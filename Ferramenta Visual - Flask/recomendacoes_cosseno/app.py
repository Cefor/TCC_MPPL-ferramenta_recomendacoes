import spacy
nlp = spacy.load('pt_core_news_lg')
from flask import Flask, render_template, request,redirect, url_for, send_file
import pandas as pd
import numpy as np
import string
import json
from rank_bm25 import BM25Okapi
from flask_bootstrap import Bootstrap5
from flask import Flask
from flask import jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk 
nltk.download('stopwords')
from nltk.corpus import stopwords
app = Flask(__name__)
bootstrap = Bootstrap5(app)
import csv
from datetime import datetime  # Importe o módulo datetime

# Ler os DataFrames uma vez e armazenar como variáveis globais
df_senadores = pd.read_csv('df_senadores.csv')
df_sugestoes = pd.read_csv('df_sugestoes_bm25_geral.csv')
df_interesses = pd.read_csv('interesse.csv')
df_detalhes_materias = pd.read_csv('df_detalhes_materias.csv')
df_autorias = pd.read_csv('df_autorias.csv')

df_detalhes_materias["combinacao"] = df_detalhes_materias["combinacao"].astype(str)
corpus_parla = df_detalhes_materias["combinacao"]
corpus_parla = [doc.translate(str.maketrans('', '', string.punctuation)).replace('\n',' ').lower() for doc in corpus_parla]
tokenized_corpus_parla = [doc.split(" ") for doc in corpus_parla]
bm25_parla = BM25Okapi(tokenized_corpus_parla)

#Similaridade de coseno
lista_stop_words = stopwords.words('portuguese') + ['lei','altera','modifica']
cv = TfidfVectorizer(stop_words=lista_stop_words, use_idf=True)
count_matrix = cv.fit_transform(df_detalhes_materias["combinacao"])
cosine_sim_normal = cosine_similarity(count_matrix)

def get_lista_similares_tramitando_base_2(DataFrameCosine,DataFrameMaterias,CodigoMateria,DataFrameMateriasAlvo):
    
    indice = get_index_materia(DataFrameMaterias,CodigoMateria)    
    similares = list(enumerate(DataFrameCosine[indice]))    
    similares = sorted(similares, key=lambda x:x[1], reverse=True)        
    df_similares = pd.DataFrame(similares, columns=['Indice', 'ValorSimilaridade'])    
    df_similares = df_similares.set_index('Indice')    
    DataFrameMaterias_filtrado = DataFrameMaterias.loc[df_similares.index]    
    DataFrameMaterias_filtrado['ValorSimilaridade'] = df_similares['ValorSimilaridade']
    # DataFrameMaterias_filtrado agora contém as linhas filtradas com a coluna de similaridade

    #Filtra para conter apenas os valores contidos em DataFrameMateriasAlvo
    condicao = DataFrameMaterias_filtrado['CodigoMateria'].isin(DataFrameMateriasAlvo['CodigoMateria'])
    DataFrameMaterias_filtrado = DataFrameMaterias_filtrado[condicao]

    #Filtra para conter apenas as matérias que começam com P
    DataFrameMaterias_filtrado = DataFrameMaterias_filtrado[DataFrameMaterias_filtrado['Identificacao'].str.startswith('P')]

    
    materias = pd.DataFrame()
    achou = 0;    
    for indice, row in DataFrameMaterias_filtrado.iterrows():
        codigo_materia_pesquisada = row["CodigoMateria"]            
        #esta_tramitando = is_materia_tramitando(codigo_materia_pesquisada)
        esta_tramitando = row["Tramitando"]
        #print('Está:'+esta_tramitando)
        if (esta_tramitando == "Sim"):             
            #materias = materias.append(row)            
            #print(pd.DataFrame(row).T)
            materias = pd.concat([materias,pd.DataFrame(row).T])
            achou = achou + 1    

        if achou >= 5:            
            break  
    
    materias = materias[materias['CodigoMateria'] != CodigoMateria]
    return materias

def get_sugestoes_parla_coseno(id):
    df_interesses_parla = obter_dataframe_interesses_condicionado(id)
    df_top_similares_cosseno = pd.DataFrame()    
    for codigo_materia in df_interesses_parla.CodigoMateria:        
        df_materia_pesquisada = df_detalhes_materias[df_detalhes_materias['CodigoMateria'] == codigo_materia]        
        similares_pesquisadas = get_lista_similares_tramitando_base_2(cosine_sim_normal, df_detalhes_materias, codigo_materia, df_detalhes_materias)        
        similares_pesquisadas = similares_pesquisadas[similares_pesquisadas['CodigoMateria'] != codigo_materia]        
        df_top_similares_cosseno = pd.concat([df_top_similares_cosseno, similares_pesquisadas])        
    #Elimina as duplicatas    
    df_top_similares_cosseno = df_top_similares_cosseno.drop_duplicates(subset='CodigoMateria')

    return df_top_similares_cosseno

# Realizar merge entre df_interesses e df_detalhes_materias
df_interesses = pd.merge(df_interesses, df_detalhes_materias, on='CodigoMateria')
df_interesses = pd.merge(df_interesses, df_senadores, on='CodigoParlamentar')

#Lê os votos
def get_votos(id):
    meus_votos = list()
    with open('votos.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        votos = list(reader)
    
    for i, row in enumerate(votos):
        if row['codigo_parlamentar'] == str(id):
            # Remova o voto se existir
            meus_votos.append(row)
            

    lista = [voto['codigo_materia'] for voto in meus_votos]    
    lista = list(map(int, lista))
    df_retorno = df_detalhes_materias[df_detalhes_materias['CodigoMateria'].isin(lista)]
    df_retorno = df_retorno.replace({np.nan: None})    
    # Verificar se o resultado é uma Series (uma linha) e converter para DataFrame se necessário
    if isinstance(df_retorno, pd.Series):
        df_retorno = pd.DataFrame([df_retorno])

    return df_retorno

def obter_dataframe_senadores():
    return df_senadores

def obter_dataframe_sugestoes():
    return df_sugestoes

def obter_dataframe_detalhe_materia():
    return df_detalhes_materias

def obter_dataframe_interesses(id):
    # Filtrar os 10 principais interesses para o parlamentar específico
    interesses_para_senador = df_interesses[df_interesses['CodigoParlamentar'] == id].sort_values(by='interesse', ascending=False).head(10)
    return interesses_para_senador

def obter_dataframe_interesses_condicionado(id):
    # Filtrar os 10 principais interesses para o parlamentar específico
        
    condicao = ((df_interesses['Identificacao'].str.startswith('P')) &
                (df_interesses['Tramitando'] == 'Sim') &                
                (~df_interesses['ClasseHierarquica'].str.contains('Orçamento Anual',na=False)) & 
                (~df_interesses['Natureza'].str.contains('Concessão',na=False)))
    df_interesses_condicionado = df_interesses[condicao]
    interesses_para_senador = df_interesses_condicionado[df_interesses_condicionado['CodigoParlamentar'] == id].sort_values(by='interesse', ascending=False).head(10)
    return interesses_para_senador

def obter_similares_sugeridas_prioritarias(codigo_materia, codigo_parlamentar):
    # Lógica para obter matérias similares sugeridas
    # Substitua a lógica abaixo pela implementação real
    
    bm25 = bm25_parla
    query = df_detalhes_materias[df_detalhes_materias['CodigoMateria'] == codigo_materia]['combinacao'].to_string(index=False)
    
    query = query.translate(str.maketrans('', '', string.punctuation)).replace('\n',' ').lower()
    tokenized_query = query.split(" ")
    bm25_scores = bm25.get_scores(tokenized_query)
    descending_indices = (-bm25_scores).argsort()
    dataframe_filtrado = df_detalhes_materias.filter(items=descending_indices, axis=0)
    dataframe_filtrado = dataframe_filtrado[dataframe_filtrado['Identificacao'].str.startswith('P') and dataframe_filtrado['prioridade'] == 'Sim']
    
    
    #Define a base que será usada para alvo    
    df_detalhes_materias_teste = pd.DataFrame(df_detalhes_materias)

    #Remove as autorias da base de teste    
    df_autorias_parla = df_autorias[df_autorias['CodigoParlamentar'] == codigo_parlamentar]    
    codigos_autorias_parla = df_autorias_parla['CodigoMateria'].unique()
    df_detalhes_materias_teste = df_detalhes_materias_teste[~df_detalhes_materias_teste['CodigoMateria'].isin(codigos_autorias_parla)]
    
    
    #Aplica as condições na base de teste
    condicao = ((df_detalhes_materias_teste['Identificacao'].str.startswith('P')) &
                (df_detalhes_materias_teste['Tramitando'] == 'Sim') &
                (df_detalhes_materias_teste['CodigoMateria'] != codigo_materia) &
                (~df_detalhes_materias_teste['ClasseHierarquica'].str.contains('Honorífico|Orçamento Anual',na=False)) & 
                (~df_detalhes_materias_teste['Natureza'].str.contains('Concessão',na=False)))
    df_detalhes_materias_teste = df_detalhes_materias_teste[condicao]
    
    achou = 0
    total_escapa = 0
    df_retorno = pd.DataFrame()

    for index, row in dataframe_filtrado.iterrows():
        if df_detalhes_materias_teste['CodigoMateria'].isin([row['CodigoMateria']]).any():
            achou += 1
            df_retorno = pd.concat([df_retorno, pd.DataFrame(row).T])

        total_escapa += 1

        if achou >= 5:
            break
        if total_escapa > 500:
            print('escapei achando', achou)
            break
    
    # Verificar se o resultado é uma Series (uma linha) e converter para DataFrame se necessário
    if isinstance(df_retorno, pd.Series):
        df_retorno = pd.DataFrame([df_retorno])

    return df_retorno

def get_index_materia(DataFrameMaterias,CodigoMateria):
    
    return DataFrameMaterias[DataFrameMaterias.CodigoMateria == int(CodigoMateria)].index.values[0]

def obter_similares_sugeridas_coseno(codigo_materia, codigo_parlamentar):
    DataFrameCosine = cosine_sim_normal
    DataFrameMaterias = df_detalhes_materias
    CodigoMateria = codigo_materia
    DataFrameMateriasAlvo = df_detalhes_materias
    
    indice = get_index_materia(DataFrameMaterias,CodigoMateria)    
    similares = list(enumerate(DataFrameCosine[indice]))    
    similares = sorted(similares, key=lambda x:x[1], reverse=True)        
    df_similares = pd.DataFrame(similares, columns=['Indice', 'ValorSimilaridade'])    
    df_similares = df_similares.set_index('Indice')    
    DataFrameMaterias_filtrado = DataFrameMaterias.loc[df_similares.index]    
    DataFrameMaterias_filtrado['ValorSimilaridade'] = df_similares['ValorSimilaridade']
    DataFrameMaterias_filtrado['ValorSimilaridade'] = pd.to_numeric(DataFrameMaterias_filtrado['ValorSimilaridade'], errors='coerce') * 100
    DataFrameMaterias_filtrado['ValorSimilaridade'] = DataFrameMaterias_filtrado['ValorSimilaridade'].round(2)
        

    # DataFrameMaterias_filtrado agora contém as linhas filtradas com a coluna de similaridade
    #Filtra para conter apenas os valores contidos em DataFrameMateriasAlvo
    condicao = DataFrameMaterias_filtrado['CodigoMateria'].isin(DataFrameMateriasAlvo['CodigoMateria'])
    DataFrameMaterias_filtrado = DataFrameMaterias_filtrado[condicao]

    #Filtra para conter apenas as matérias que começam com P e estão tramitando
    condicao = ((DataFrameMaterias_filtrado['Identificacao'].str.startswith('P')) &
                (DataFrameMaterias_filtrado['Tramitando'] == 'Sim') &
                (DataFrameMaterias_filtrado['CodigoMateria'] != codigo_materia) &
                (~DataFrameMaterias_filtrado['ClasseHierarquica'].str.contains('Orçamento Anual',na=False)) & 
                (~DataFrameMaterias_filtrado['Natureza'].str.contains('Concessão',na=False)))
    DataFrameMaterias_filtrado = DataFrameMaterias_filtrado[condicao]    
    DataFrameMaterias_filtrado = DataFrameMaterias_filtrado.replace({np.nan: None})
    
    return DataFrameMaterias_filtrado.head(6)
    

def obter_similares_sugeridas(codigo_materia, codigo_parlamentar):
    # Lógica para obter matérias similares sugeridas
    # Substitua a lógica abaixo pela implementação real
    
    bm25 = bm25_parla
    query = df_detalhes_materias[df_detalhes_materias['CodigoMateria'] == codigo_materia]['combinacao'].to_string(index=False)
    
    query = query.translate(str.maketrans('', '', string.punctuation)).replace('\n',' ').lower()
    tokenized_query = query.split(" ")
    bm25_scores = bm25.get_scores(tokenized_query)
    descending_indices = (-bm25_scores).argsort()
    dataframe_filtrado = df_detalhes_materias.filter(items=descending_indices, axis=0)
    dataframe_filtrado = dataframe_filtrado[(dataframe_filtrado['Identificacao'].str.startswith('P')) ]
    dataframe_filtrado = dataframe_filtrado.replace({np.nan: None})
    
    #Define a base que será usada para alvo    
    df_detalhes_materias_teste = pd.DataFrame(df_detalhes_materias)

    #Remove as autorias da base de teste    
    df_autorias_parla = df_autorias[df_autorias['CodigoParlamentar'] == codigo_parlamentar]    
    codigos_autorias_parla = df_autorias_parla['CodigoMateria'].unique()
    df_detalhes_materias_teste = df_detalhes_materias_teste[~df_detalhes_materias_teste['CodigoMateria'].isin(codigos_autorias_parla)]
    
    
    #Aplica as condições na base de teste
    condicao = ((df_detalhes_materias_teste['Identificacao'].str.startswith('P')) &
                (df_detalhes_materias_teste['Tramitando'] == 'Sim') &
                (df_detalhes_materias_teste['CodigoMateria'] != codigo_materia) &
                (~df_detalhes_materias_teste['ClasseHierarquica'].str.contains('Orçamento Anual',na=False)) & 
                (~df_detalhes_materias_teste['Natureza'].str.contains('Concessão',na=False)))
    df_detalhes_materias_teste = df_detalhes_materias_teste[condicao]
    
    achou = 0
    total_escapa = 0
    df_retorno = pd.DataFrame()

    for index, row in dataframe_filtrado.iterrows():
        if df_detalhes_materias_teste['CodigoMateria'].isin([row['CodigoMateria']]).any():
            achou += 1
            df_retorno = pd.concat([df_retorno, pd.DataFrame(row).T])

        total_escapa += 1

        if achou >= 5:
            break
        if total_escapa > 500:
            print('escapei achando', achou)
            break
    
    # Verificar se o resultado é uma Series (uma linha) e converter para DataFrame se necessário
    if isinstance(df_retorno, pd.Series):
        df_retorno = pd.DataFrame([df_retorno])

    return df_retorno

def obter_similares_pesquisa(codigo_parlamentar, query):    
    bm25 = bm25_parla
        
    query = query.translate(str.maketrans('', '', string.punctuation)).replace('\n',' ').lower()
    tokenized_query = query.split(" ")
    bm25_scores = bm25.get_scores(tokenized_query)

    limite_similaridade = 0.5

    # Filtra os documentos com escores BM25 acima do limite
    documentos_selecionados = [i for i, score in enumerate(bm25_scores) if score > limite_similaridade]


    descending_indices = (-bm25_scores).argsort()
    print("Indices: ",descending_indices)
    dataframe_filtrado = df_detalhes_materias.filter(items=documentos_selecionados, axis=0)
    dataframe_filtrado = dataframe_filtrado[dataframe_filtrado['Identificacao'].str.startswith('P')]
    
    #Define a base que será usada para alvo    
    df_detalhes_materias_teste = pd.DataFrame(df_detalhes_materias)
        
    #Aplica as condições na base de teste
    condicao = ((df_detalhes_materias_teste['Identificacao'].str.startswith('P')) &
                (df_detalhes_materias_teste['Tramitando'] == 'Sim') &                
                (~df_detalhes_materias_teste['ClasseHierarquica'].str.contains('Orçamento Anual',na=False)) & 
                (~df_detalhes_materias_teste['Natureza'].str.contains('Concessão',na=False)))
    df_detalhes_materias_teste = df_detalhes_materias_teste[condicao]
    
    achou = 0
    total_escapa = 0
    df_retorno = pd.DataFrame()

    for index, row in dataframe_filtrado.iterrows():
        if df_detalhes_materias_teste['CodigoMateria'].isin([row['CodigoMateria']]).any():
            achou += 1
            df_retorno = pd.concat([df_retorno, pd.DataFrame(row).T])

        total_escapa += 1

        if achou >= 12:
            break
        if total_escapa > 500:
            print('escapei achando', achou)
            break
    
    # Verificar se o resultado é uma Series (uma linha) e converter para DataFrame se necessário
    if isinstance(df_retorno, pd.Series):
        df_retorno = pd.DataFrame([df_retorno])
    
    if df_retorno.empty:
        return df_retorno
    else:
        df_retorno = df_retorno.head(12)[['Identificacao','Ementa','CodigoMateria','justificativa_prioridade']]    
        df_retorno = df_retorno.replace({np.nan: None})
    return df_retorno

# Função para salvar a avaliação em um arquivo CSV
def salvar_avaliacao_csv(id,pergunta1, pergunta2, pergunta3, pergunta4):
    with open('avaliacoes.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([id,pergunta1, pergunta2, pergunta3, pergunta4])    

@app.route('/')
def pagina_inicial():
    senadores = obter_dataframe_senadores().to_dict(orient='records')
    return render_template('pagina_inicial.html', senadores=senadores)

@app.route('/senador/<int:id>')
def pagina_detalhes(id):
    senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id].to_dict(orient='records')[0]    
    #sugestoes_para_senador = obter_dataframe_sugestoes()[(obter_dataframe_sugestoes()['CodigoParlamentar'] == id)].head(12).to_dict(orient='records')
    
    df_retorno = get_sugestoes_parla_coseno(id)
    df_retorno = df_retorno.replace({np.nan: None})
    df_retorno = df_retorno.head(12).to_dict(orient='records')
    ##sugestoes_para_senador = obter_dataframe_sugestoes()[(obter_dataframe_sugestoes()['CodigoParlamentar'] == id) & (obter_dataframe_sugestoes()['prioridade'] == 'Não')].head(12).to_dict(orient='records')
    #sugestoes_prioritarias = obter_dataframe_sugestoes()[(obter_dataframe_sugestoes()['CodigoParlamentar'] == id) & (obter_dataframe_sugestoes()['prioridade'] == 'Sim')].head(12).to_dict(orient='records')
    
    return render_template('pagina_detalhes.html', senador=senador, sugestoes=df_retorno)

@app.route('/senador/<int:id>/interesses')
def pagina_interesses(id):
    interesses_para_senador = obter_dataframe_interesses(id).to_dict(orient='records')
    senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id].to_dict(orient='records')[0]
    return render_template('pagina_interesses.html',senador=senador, interesses=interesses_para_senador,similares_sugeridas=obter_similares_sugeridas_coseno)

@app.route('/senador/<int:id>/detalhes_materias/<int:codigo_materia>')
def pagina_detalhes_materias(id, codigo_materia):
    interesse_para_senador = obter_dataframe_interesses(id)[obter_dataframe_interesses(id)['CodigoMateria'] == codigo_materia]
    
    if not interesse_para_senador.empty:
        interesse_para_senador = interesse_para_senador.to_dict(orient='records')[0]
    else:
        interesse_para_senador = None
    
    senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id].to_dict(orient='records')[0]
    detalhe_materia = obter_dataframe_detalhe_materia()[obter_dataframe_detalhe_materia()['CodigoMateria'] == codigo_materia].to_dict(orient='records')[0]
    return render_template('pagina_detalhes_materias.html',senador=senador, materia=detalhe_materia,similares_sugeridas=obter_similares_sugeridas_coseno,interesse=interesse_para_senador )

@app.route('/senador/<int:id>/pesquisar/', methods=['GET'])
def pesquisar_similares(id):    
    query = request.args.get('query', '')
    df_retorno = obter_similares_pesquisa(id,query)    
    df_retorno = df_retorno.replace({np.nan: None})
    df_retorno = df_retorno.to_dict(orient='records')    
    senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id].to_dict(orient='records')[0]
    return render_template('pagina_resultado_pesquisa.html', resultados_pesquisa=df_retorno, senador=senador)

@app.route('/senador/<int:id>/avaliacao')
def pagina_avaliacao(id):
    senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id].to_dict(orient='records')[0]
    return render_template('avaliacao.html',senador=senador, sucesso=request.args.get('sucesso'))

@app.route('/senador/<int:id>/preferencias')
def pagina_preferencias(id):
    senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id].to_dict(orient='records')[0]
    votos = get_votos(id).to_dict(orient='records')
    return render_template('pagina_preferencias.html',senador=senador, preferencias=votos)

@app.route('/senador/<int:id>/outros')
def pagina_outros(id):
    senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id].to_dict(orient='records')[0]
    interesses_partido = obter_interesses_senadores_partido(id).to_dict(orient='records')
    interesses_estado = obter_interesses_senadores_estado(id).to_dict(orient='records')
    principais_interesses = obter_principais_interesses_senadores().to_dict(orient='records')
    return render_template('pagina_outros.html',senador=senador, interesses_partido=interesses_partido, interesses_estado = interesses_estado, principais_interesses = principais_interesses)

@app.route('/senador/<int:id>/salvar_avaliacao', methods=['POST'])
def salvar_avaliacao(id):
    try:
        senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id].to_dict(orient='records')[0]
        # Obtenha os dados da avaliação do formulário
        pergunta1 = int(request.form['pergunta1'])
        pergunta2 = int(request.form['pergunta2'])
        pergunta3 = int(request.form['pergunta3'])        
        pergunta4 = request.form['pergunta4']

        # Salve a avaliação em um arquivo CSV
        salvar_avaliacao_csv(id, pergunta1, pergunta2, pergunta3, pergunta4)

        # Redirecione de volta para a página de avaliação com uma mensagem de sucesso
        return redirect(url_for('pagina_avaliacao',id=id, sucesso='Obrigado! Avaliação enviada com sucesso!'))
    except Exception as e:
        # Em caso de erro, redirecione com uma mensagem de falha
        return redirect(url_for('pagina_avaliacao', id=id, sucesso='Erro ao enviar a avaliação. Tente novamente.'))




@app.route('/salvar_voto', methods=['POST'])
def salvar_voto():
    codigo_parlamentar = request.form.get('codigo_parlamentar')
    codigo_materia = request.form.get('codigo_materia')
    acao = request.form.get('acao')

    # Adicione uma coluna de identificação única (pode ser um timestamp)
    identificador_unico = datetime.now().strftime('%Y%m%d%H%M%S%f')

    with open('votos.csv', 'r+') as csvfile:
        reader = csv.DictReader(csvfile)
        votos = list(reader)

        # Verifique se já existe um voto com a mesma combinação
        for i, row in enumerate(votos):
            if row['codigo_parlamentar'] == codigo_parlamentar and row['codigo_materia'] == codigo_materia:
                # Remova o voto se existir
                votos.pop(i)
                break
        else:
            # Adicione um novo voto se não existir
            votos.append({'codigo_parlamentar': codigo_parlamentar, 'codigo_materia': codigo_materia, 'acao': acao, 'identificador_unico': identificador_unico})

        # Volte ao início do arquivo e escreva os votos atualizados
        csvfile.seek(0)
        csvfile.truncate()
        fieldnames = ['codigo_parlamentar', 'codigo_materia', 'acao', 'identificador_unico']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(votos)

    return jsonify({'status': 'success'})

def obter_voto_mat(codigo_parlamentar, codigo_materia):
    try:
        votos = obter_todos_os_votos()  # Substitua com sua lógica real para obter todos os votos
        for voto in votos:
            if voto['codigo_parlamentar'] == str(codigo_parlamentar) and voto['codigo_materia'] == str(codigo_materia):
                return voto['acao']

        return None  # Se não houver voto encontrado
    except Exception as e:
        print("ERRROU")
        
    

def obter_todos_os_votos():
    try:
        with open('votos.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            return [voto for voto in reader]
    except Exception as e:
        print("ERRROU")

@app.route('/get_voto_mat/<int:codigo_parlamentar>/<int:codigo_materia>')
def get_voto_mat(codigo_parlamentar, codigo_materia):
    voto = obter_voto_mat(codigo_parlamentar, codigo_materia)  # Substitua com sua lógica real
    return jsonify({'acao': voto})

def obter_senadores_partido(id):
    senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id]
    partido = senador['SiglaPartidoParlamentar'].values[0]
    df_senadores_partido = obter_dataframe_senadores()[obter_dataframe_senadores()['SiglaPartidoParlamentar'] == partido]
    # Remova o senador específico do DataFrame df_senadores_partido
    df_senadores_partido = df_senadores_partido[df_senadores_partido['CodigoParlamentar'] != id]

    return df_senadores_partido

def obter_senadores_estado(id):
    senador = obter_dataframe_senadores()[obter_dataframe_senadores()['CodigoParlamentar'] == id]
    estado = senador['UfParlamentar'].values[0]
    df_senadores_estado = obter_dataframe_senadores()[obter_dataframe_senadores()['UfParlamentar'] == estado]
    # Remova o senador específico do DataFrame df_senadores_partido
    df_senadores_estado = df_senadores_estado[df_senadores_estado['CodigoParlamentar'] != id]

    return df_senadores_estado

def obter_interesses_senadores_partido(id):
    df_senadores_partido = obter_senadores_partido(id)
    df_retorno = pd.DataFrame()
    for index, row in df_senadores_partido.iterrows():
        codigo_parlamentar = row['CodigoParlamentar']
        df_interesses_senador = obter_dataframe_interesses_condicionado(codigo_parlamentar)
        df_interesses_senador = df_interesses_senador.head(3)
        df_retorno = pd.concat([df_retorno, df_interesses_senador])
    
    df_retorno = df_retorno.replace({np.nan: None}) 
    return df_retorno

def obter_principais_interesses_senadores():
    df_filtrado = df_interesses[df_interesses['interesse'] > 5]
    condicao = ((df_interesses['Identificacao'].str.startswith('P')) &
                (df_interesses['Tramitando'] == 'Sim') &                
                (~df_interesses['ClasseHierarquica'].str.contains('Orçamento Anual',na=False)) & 
                (~df_interesses['Natureza'].str.contains('Concessão',na=False)))
    df_filtrado = df_interesses[condicao]
    df_agrupado = df_filtrado.groupby('CodigoMateria')['CodigoParlamentar'].nunique().reset_index(name='ContagemParlamentares')
    df_ordenado = df_agrupado.sort_values(by='ContagemParlamentares', ascending=False)
    df_ordenado = df_ordenado.head(8)
    df_retorno = pd.DataFrame()
    for index,row in df_ordenado.iterrows():
        codigo_materia = row['CodigoMateria']
        detalhe_materia = obter_dataframe_detalhe_materia()[obter_dataframe_detalhe_materia()['CodigoMateria'] == codigo_materia]
        detalhe_materia['ContagemParlamentares'] = row['ContagemParlamentares']
        df_retorno = pd.concat([df_retorno,detalhe_materia])


    df_retorno = df_retorno.replace({np.nan: None}) 
    return df_retorno


def obter_interesses_senadores_estado(id):
    df_senadores_estado = obter_senadores_estado(id)
    df_retorno = pd.DataFrame()
    for index, row in df_senadores_estado.iterrows():
        codigo_parlamentar = row['CodigoParlamentar']
        df_interesses_senador = obter_dataframe_interesses_condicionado(codigo_parlamentar)
        df_interesses_senador = df_interesses_senador.head(3)
        df_retorno = pd.concat([df_retorno, df_interesses_senador])
    
    
    
    df_retorno = df_retorno.replace({np.nan: None}) 
    return df_retorno

@app.route('/download_votos')
def download_votos():
    votos_file_path = 'votos.csv'
    return send_file(votos_file_path, as_attachment=True)

@app.route('/download_avaliacao')
def download_avaliacoes():
    votos_file_path = 'avaliacoes.csv'
    return send_file(votos_file_path, as_attachment=True)

if __name__ == '__main__':

    app.run(debug=True)
