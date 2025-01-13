const arduinoContainer = document.querySelector('.arduino-dropdown-container');
const arduinoMenu = document.querySelector('.arduino-dropdown-menu');
const arduinoToggle = document.querySelector('.arduino-dropdown-toggle');


const displayFallbackMessage = () => {
    arduinoMenu.innerHTML = '';
    const noItemsMessage = document.createElement('li');
    noItemsMessage.textContent = 'Nessun Arduino selezionabile al momento';
    noItemsMessage.classList.add('no-arduino-message');
    arduinoMenu.appendChild(noItemsMessage);
};


const populateMenu = (data) => {
    arduinoMenu.innerHTML = '';

    if (data.length === 0) {
        displayFallbackMessage();
    } else {
        data.forEach(item => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = 'javascript:void(0);';
            a.textContent = item;
            li.appendChild(a);
            arduinoMenu.appendChild(li);

            a.addEventListener('click', async (event) => {
                event.preventDefault();

                currentArduinoName = item.replace(/ /g, '-');

                await initializeDatePickers();

                drawArduinoChart();

                arduinoContainer.classList.remove('active');
            });
        });
    }
};


document.addEventListener('DOMContentLoaded', async () => {
    await fetch('/api/arduino-names')
    .then(response => {
        if (!response.ok) throw new Error();
        return response.json();
    })
    .then(data => {
        let dataToPopulateMenuWith = [];
        data.forEach(item => { dataToPopulateMenuWith.push(item.replace(/-/g, ' ')); });
        populateMenu(dataToPopulateMenuWith);
    })
    .catch(error => {
        displayFallbackMessage();
    });

    arduinoToggle.addEventListener('click', () => {
        arduinoContainer.classList.toggle('active');
    });

    document.addEventListener('click', (event) => {
        if (!arduinoContainer.contains(event.target)) arduinoContainer.classList.remove('active');
    });
});

