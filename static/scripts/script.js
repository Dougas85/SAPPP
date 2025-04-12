document.addEventListener('DOMContentLoaded', function () {
    const calendar = document.getElementById('calendar');
    for (let i = 1; i <= 64; i++) {
        const day = document.createElement('div');
        day.innerText = i;
        day.id = `day-${i}`;
        day.classList.add('calendar-item', 'red-item');
        calendar.appendChild(day);

        day.addEventListener("click", function () {
            showItemDetails(i);
        });
    }

     // 🎯 Aqui entra a parte que aplica o negrito com base no peso
    fetch('/get_all_items')
        .then(response => response.json())
        .then(data => {
            data.forEach(item => {
                if (item.peso === 5) {
                    const el = document.getElementById(`day-${item.numero}`);
                    if (el) {
                        el.classList.add('bold-day'); // ou el.style.fontWeight = 'bold';
                    }
                }
            });
        });


    let viewedItems = new Set();

    document.getElementById('showLinesButton').addEventListener('click', function () {
        fetch('/get_lines')
            .then(response => response.json())
            .then(data => {
                const tableBody = document.getElementById('itemsTable').querySelector('tbody');
                tableBody.innerHTML = '';

                data.forEach((line) => {
                    const newRow = tableBody.insertRow();
                    const itemCell = newRow.insertCell(0);
                    const actionCell = newRow.insertCell(1);

                    const descricao = line.descricao || "Sem informação";
                    itemCell.innerText = `Item ${line.numero}: ${descricao}`;

                    const btn = document.createElement('button');
                    btn.innerText = "Ver Detalhes";
                    btn.classList.add('open-dialog');

                    btn.addEventListener('click', function () {
                        openModal(line.numero, descricao, line.orientacao, line.referencia, line.peso);
                    });

                    actionCell.appendChild(btn);

                    const dayElement = document.getElementById(`day-${line.numero}`);
                    if (dayElement) {
                        dayElement.classList.remove('red-item');
                        dayElement.classList.add('viewed');
                        
                        viewedItems.add(line.numero);
                    }
                });

                if (viewedItems.size === 64) {
                    viewedItems.clear();
                    document.querySelectorAll('.calendar-item').forEach(day => {
                        day.classList.remove('viewed');
                        day.classList.add('red-item');
                    });
                }
            })
            .catch(error => console.error("Erro ao carregar os itens:", error));
    });

    document.getElementById('closeDialog').addEventListener('click', function () {
        document.getElementById('dialogBox').close();
        window.speechSynthesis.cancel();
        document.getElementById("speechAnimation").style.display = "none";
    });

    document.getElementById('stopSpeechButton').addEventListener('click', function () {
        window.speechSynthesis.cancel();
        document.getElementById("speechAnimation").style.display = "none";
    });

    window.addEventListener('click', function (event) {
        const modal = document.getElementById('dialogBox');
        if (event.target === modal) {
            modal.close();
            window.speechSynthesis.cancel();
            document.getElementById("speechAnimation").style.display = "none";
        }
    });

    document.getElementById('searchButton').addEventListener('click', function () {
        const searchQuery = document.getElementById('searchInput').value.toLowerCase();
        if (searchQuery.trim() === "") {
            alert("Por favor, insira uma palavra-chave para pesquisa.");
            return;
        }

        fetch(`/search_items/${searchQuery}`)
            .then(response => response.json())
            .then(data => {
                const tableBody = document.getElementById('itemsTable').querySelector('tbody');
                tableBody.innerHTML = '';

                data.forEach((line) => {
                    const newRow = tableBody.insertRow();
                    const itemCell = newRow.insertCell(0);
                    const actionCell = newRow.insertCell(1);

                    const descricao = line.descricao || "Sem informação";
                    itemCell.innerText = `Item ${line.numero}: ${descricao}`;

                    const btn = document.createElement('button');
                    btn.innerText = "Ver Detalhes";
                    btn.classList.add('open-dialog');

                    btn.addEventListener('click', function () {
                        openModal(line.numero, descricao, line.orientacao, line.referencia, line.peso);
                    });

                    actionCell.appendChild(btn);
                });
            })
            .catch(error => console.error("Erro ao buscar os itens:", error));
    });

    // Função auxiliar para abrir o modal sem iniciar a fala automaticamente
    function openModal(numero, descricao, orientacao, referencia, peso) {
        document.getElementById('modalItem').innerText = `Item ${numero}`;
        document.getElementById('modalOrientation').innerText = orientacao || "Sem orientação";
        document.getElementById('modalReference').innerText = referencia || "Sem referência";
        document.getElementById('modalDescription').innerText = descricao || "Sem informação";
        document.getElementById('modalWeight').innerText = peso || "Sem peso";

        document.getElementById('dialogBox').showModal();

        // Armazena o texto para falar no botão "Iniciar Fala"
        const textoParaFalar = `Descrição: ${descricao || "Sem informação"}. Orientação: ${orientacao || "Sem orientação"}. Referência: ${referencia || "Sem referência"}.`;
        document.getElementById('startSpeechButton').onclick = function() {
            speakText(textoParaFalar);
        };
    }

    function showItemDetails(itemNum) {
        fetch(`/get_item_details/${itemNum}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Item não encontrado!");
                } else {
                    openModal(data.numero, data.descricao, data.orientacao, data.referencia, data.peso);
                }
            })
            .catch(error => console.error("Erro ao buscar detalhes:", error));
    }

    // VOZES
    window.speechSynthesis.onvoiceschanged = function () {
        const voices = window.speechSynthesis.getVoices();
        voices.forEach(voice => {
            console.log(voice.name, voice.lang);
        });
    };

    function speakText(text) {
        const cleanedText = text.replace(/([:;.,])/g, '$1 ');

        // Pega todas as vozes disponíveis
        const voices = window.speechSynthesis.getVoices();

        // Tenta encontrar uma voz jovem e natural em português do Brasil
        const selectedVoice = voices.find(voice =>
            voice.lang === 'pt-BR' &&
            (
                voice.name.includes('Google') || // Google voz natural
                voice.name.includes('Luciana') || // Voz mais jovem/feminina em alguns sistemas
                voice.name.includes('Daniel') ||  // Alternativa mais neutra
                voice.name.includes('Microsoft')  // Voz da Microsoft (em alguns Windows)
            )
        ) || voices.find(voice => voice.lang === 'pt-BR'); // Fallback para qualquer pt-BR

        const utterance = new SpeechSynthesisUtterance(cleanedText);
        utterance.voice = selectedVoice;
        utterance.rate = 0.9;
        utterance.lang = 'pt-BR';

        // Animação de fala
        const animation = document.getElementById("speechAnimation");
        if (animation) {
            animation.style.display = "block";
        }

        utterance.onend = () => {
            if (animation) {
                animation.style.display = "none";
            }
        };

        window.speechSynthesis.speak(utterance);
    }

    // Evento para botão "Parar Fala"
    document.getElementById("stopSpeechButton").addEventListener("click", function(event) {
        event.preventDefault(); // Evita comportamento padrão
        window.speechSynthesis.cancel(); // Cancela a fala
        const animation = document.getElementById("speechAnimation");
        if (animation) animation.style.display = "none";
    });
});
