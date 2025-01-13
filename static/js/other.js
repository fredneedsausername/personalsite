
var currentArduinoName;

function getDayAfter(inputDate) {
    const parsedDate = new Date(`${inputDate}T00:00:00Z`);
  
    parsedDate.setUTCDate(parsedDate.getUTCDate() + 1);
  
    return parsedDate.toISOString().split('T')[0];
}


function getItalianISOTimeNow() {
    const now = new Date();
  
    const options = { timeZone: 'Europe/Rome', hour12: false };
    const dateParts = new Intl.DateTimeFormat('en-CA', {
      ...options,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).formatToParts(now);
  
    const dateTime = dateParts.reduce((acc, part) => {
      if (part.type === 'year') acc.year = part.value;
      if (part.type === 'month') acc.month = part.value;
      if (part.type === 'day') acc.day = part.value;
      if (part.type === 'hour') acc.hour = part.value;
      if (part.type === 'minute') acc.minute = part.value;
      if (part.type === 'second') acc.second = part.value;
      return acc;
    }, {});
  
    const date = `${dateTime.year}-${dateTime.month}-${dateTime.day}`;
    const time = `${dateTime.hour}:${dateTime.minute}:${dateTime.second}`;
  
    const offset = new Intl.DateTimeFormat('en-US', { timeZoneName: 'shortOffset', timeZone: 'Europe/Rome' })
      .formatToParts(now)
      .find((part) => part.type === 'timeZoneName').value;
  
    return `${date}T${time}${offset}`;
}


function getItalianISOTimeYesterday() {
    const now = new Date();
  
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  
    const options = { timeZone: 'Europe/Rome', hour12: false };
    const dateParts = new Intl.DateTimeFormat('en-CA', {
      ...options,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).formatToParts(yesterday);
  
    // Extract date and time parts
    const dateTime = dateParts.reduce((acc, part) => {
      if (part.type === 'year') acc.year = part.value;
      if (part.type === 'month') acc.month = part.value;
      if (part.type === 'day') acc.day = part.value;
      if (part.type === 'hour') acc.hour = part.value;
      if (part.type === 'minute') acc.minute = part.value;
      if (part.type === 'second') acc.second = part.value;
      return acc;
    }, {});
  
    // Construct ISO string manually
    const date = `${dateTime.year}-${dateTime.month}-${dateTime.day}`;
    const time = `${dateTime.hour}:${dateTime.minute}:${dateTime.second}`;
  
    // Calculate Italian timezone offset
    const offset = new Intl.DateTimeFormat('en-US', { timeZoneName: 'shortOffset', timeZone: 'Europe/Rome' })
      .formatToParts(yesterday)
      .find((part) => part.type === 'timeZoneName').value;
  
    return `${date}T${time}${offset}`;
}


async function handleAruinoDatePickerFormSubmission(event) {
    event.preventDefault();

    const form = event.target;
    const formId = form.querySelector('[name="form_id"]').value;
    const [startDate, endDate] = readDatesFromArduinoChartCalendar();

    if (new Date(startDate) > new Date(endDate)) {
        alert('La data di inizio deve venire prima della data di fine');
        return;
    }
    if (new Date(endDate) - new Date(startDate) > 7 * 24 * 60 * 60 * 1000) {
        alert("L'intervallo massimo selezionabile è di 7 giorni");
        return;
    }

    const submitButton = form.querySelector('.arduino-graph-date-picker-submit-button');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = 'Caricando...';
    submitButton.disabled = true;

    drawArduinoChart();
        
    submitButton.innerHTML = originalText;
    submitButton.disabled = false;
}


async function fetchMeasurementsFromServer(startDate, endDate) {
    const response = await fetch('/api/arduino-measurements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            arduino_name: currentArduinoName,
            start_date: startDate,
            end_date: endDate,
        }),
    });

    if (!response.ok) throw new Error("Errore nel caricamento dei dati");

    return response.json();
}


function readDatesFromArduinoChartCalendar() {
    const startDate = document.getElementById('arduino-graph-start-date').value;
    const endDate = document.getElementById('arduino-graph-end-date').value;
    return [startDate, endDate];
}


var arduinoChart;
var arduinoChartIsPageLoad = true;
async function drawArduinoChart() {
    const [start_date, end_date] = readDatesFromArduinoChartCalendar();

    const data = await fetchMeasurementsFromServer(start_date, end_date)
    .catch( error => { if(!arduinoChartIsPageLoad) alert(error.message); });

    let labels;
    let tempData;
    let humidityData;

    let drawChart;

    if(data) {
        labels = data.dates;
        tempData = data.temperatures;
        humidityData = data.humidity;

        drawChart = true;
    } 
    if (!data) {
        if(arduinoChartIsPageLoad) {
            labels = [];
            tempData = [];
            humidityData = [];
            drawChart = true;
        }
        else drawChart = false;
    }
    
    if (drawChart) {
        const ctx = document.getElementById('ArduinoChart').getContext('2d');

        if (arduinoChart) arduinoChart.destroy();

        const chartData = {
            labels: labels,
            datasets: [
                {
                    label: 'Temperatura (°C)',
                    data: tempData,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.5)',
                    yAxisID: 'y',
                },
                {
                    label: 'Umidità Relativa (%)',
                    data: humidityData,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    yAxisID: 'y1',
                },
            ],
        };
    
        const config = {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { position: 'left', title: { display: true, text: 'Temperatura (°C)' } },
                    y1: { position: 'right', title: { display: true, text: 'Umidità Relativa (%)' }, grid: { drawOnChartArea: false } },
                },
            },
        };
    
        arduinoChart = new Chart(ctx, config);
    }

    arduinoChartIsPageLoad = false;
}


async function initializeDatePickers() {

    const startDateInput = document.getElementById('arduino-graph-start-date');
    const endDateInput = document.getElementById('arduino-graph-end-date');
    
    await fetch('/api/earliest-latest-arduino-measurements-dates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arduino_name: currentArduinoName }),
    })
    .then(response => {
        if (!response.ok) throw new Error();
        return response.json();
    })
    .then(data => {

        startDateInput.min = data.earliest_measurement_date;
        startDateInput.max = data.latest_measurement_date;

        endDateInput.min = getDayAfter(data.earliest_measurement_date)
        endDateInput.max = getDayAfter(data.latest_measurement_date);

    })
    .catch(error => {

        startDateInput.min = getItalianISOTimeYesterday().split('T')[0];
        startDateInput.max = startDateInput.min;

        endDateInput.min = getItalianISOTimeNow().split('T')[0];
        endDateInput.max = endDateInput.min;

    });

    startDateInput.value = startDateInput.max
    endDateInput.value = endDateInput.max

}

document.addEventListener('DOMContentLoaded', async () => {
    await fetch('/api/arduino-names')
    .then(response => response.json())
    .then(data => { if (data) currentArduinoName = data[0]; });

    await initializeDatePickers();

    await drawArduinoChart();
});