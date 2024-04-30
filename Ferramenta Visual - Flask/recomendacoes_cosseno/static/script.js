document.addEventListener('DOMContentLoaded', function () {
    var thumbsUpButtons = document.querySelectorAll('.thumbs-up');
    var thumbsDownButtons = document.querySelectorAll('.thumbs-down');

    thumbsUpButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            alternarVoto(button, 'gostei');
        });

        var codigoParlamentar = button.dataset.codigoParlamentar;
        var codigoMateria = button.dataset.codigoMateria;
        var url = '/get_voto_mat/' + codigoParlamentar + '/' + codigoMateria;

        // Faz uma solicitação AJAX para obter o voto
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.acao === 'gostei') {
                    button.classList.add('votado');
                }
            })
            .catch(error => console.error('Erro ao obter voto:', error));
    });

    thumbsDownButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            alternarVoto(button, 'nao_gostei');
        });

        var codigoParlamentar = button.dataset.codigoParlamentar;
        var codigoMateria = button.dataset.codigoMateria;
        var url = '/get_voto_mat/' + codigoParlamentar + '/' + codigoMateria;

        // Faz uma solicitação AJAX para obter o voto
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.acao === 'nao_gostei') {
                    button.classList.add('votado');
                }
            })
            .catch(error => console.error('Erro ao obter voto:', error));
    });
});


function alternarVoto(button, acao) {
    var codigoParlamentar = button.dataset.codigoParlamentar;
    var codigoMateria = button.dataset.codigoMateria;

    // Adicione aqui a lógica para verificar o estado atual e enviar os dados para o servidor (Flask)
    // Exemplo: Se o usuário já votou "Gostei", ao clicar novamente, remove o voto.

    // Exemplo simples:
    if (button.classList.contains('votado')) {
        // Se já votou, remove o voto
        button.classList.remove('votado');
        enviarVoto(codigoParlamentar, codigoMateria, 'remover', acao);
    } else {
        // Se ainda não votou, adiciona o voto
        button.classList.add('votado');
        enviarVoto(codigoParlamentar, codigoMateria, 'adicionar', acao);
    }
}

function enviarVoto(codigoParlamentar, codigoMateria, acaoAtual, acaoNova) {
    // Adicione aqui a lógica para enviar os dados para o servidor (Flask)
    fetch('/salvar_voto', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            codigo_parlamentar: codigoParlamentar,
            codigo_materia: codigoMateria,
            acao_atual: acaoAtual,
            acao: acaoNova,
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Voto salvo com sucesso!');
        } else {
            console.error('Erro ao salvar o voto.');
        }
    })
    .catch(error => console.error('Erro na solicitação AJAX:', error));
}

function get_voto_mat(codigoParlamentar, codigoMateria) {    
    var votoMat = preferencias.find(function (voto) {
        return voto.codigo_parlamentar === codigoParlamentar && voto.codigo_materia === codigoMateria;
    });

    return votoMat ? votoMat.acao : '';
}



function limparNaN(obj) {
    for (var prop in obj) {
        if (obj.hasOwnProperty(prop) && typeof obj[prop] === 'number' && isNaN(obj[prop])) {
            obj[prop] = null; // ou substitua por outro valor padrão
        }
    }
}

function pesquisar(senadorCodigo) {
    console.log("Entrei no pesquisar");
    var query = document.getElementById('search-input').value;
    var url = `/senador/${senadorCodigo}/pesquisar/${encodeURIComponent(query)}`;

    // Realiza a solicitação AJAX para o Flask
    // Realiza a solicitação AJAX para o Flask
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            console.log("Response:"+response)
            return response.json();
        })
        .then(data => exibirResultados(data, senadorCodigo))
        .catch(error => console.error('Erro na solicitação AJAX:', error));
    
    event.preventDefault(); 
}



function exibirResultados(resultados, senadorCodigo) {
    

    var resultadosContainer = document.getElementById('resultados-container');
    resultadosContainer.innerHTML = ''; // Limpa qualquer conteúdo existente

    if (resultados.length === 0) {
        resultadosContainer.innerHTML = '<p>Nenhum resultado encontrado.</p>';
    } else {
        resultadosContainer.innerHTML = '<h3>Resultados da Pesquisa:</h3>';

        

        
        // Crie elementos HTML para cada resultado
        resultados.resultados.forEach(function (resultado) {
            

            var card = document.createElement('div');
            card.className = 'card my-3';

            var cardBody = document.createElement('div');
            cardBody.className = 'card-body';

            // Verificar se as propriedades existem antes de acessá-las
            if (resultado['Identificacao'] !== null && resultado['Identificacao'] !== undefined) {
                var titulo = document.createElement('h5');
                titulo.className = 'card-title text-primary';
                titulo.textContent = resultado['Identificacao'];
                cardBody.appendChild(titulo);
            }

            if (resultado['Ementa'] !== null && resultado['Ementa'] !== undefined) {
                var ementa = document.createElement('p');
                ementa.className = 'card-text';
                ementa.textContent = resultado['Ementa'];
                cardBody.appendChild(ementa);
            }

            card.appendChild(cardBody);            
            resultadosContainer.appendChild(card);

            
            
        });
        // Redirecionar para a página de resultados (substitua 'resultados_pesquisa' com o caminho real)
        window.location.href = '/senador/'+senadorCodigo+'/resultados_pesquisa/';
        
    }
}

function alo(){
    console.log("CHAMEI")
}
