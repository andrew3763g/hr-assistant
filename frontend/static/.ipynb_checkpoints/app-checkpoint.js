const startBtn = document.getElementById('start-btn');
const recordingStatus = document.getElementById('recording-status');
const audioPlayer = document.querySelector('audio');
let mediaRecorder;
let chunks = [];

// Функция запуска записи
async function startRecording() {
    if (startBtn.value == 'Запустить запись ответа') {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
    
            // Добавляем обработчик события dataavailable для сбора фрагментов записи
            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) {
                    chunks.push(event.data);
                }
            };
    
            // Обработчик завершения записи
            mediaRecorder.onstop = () => {
                const blob = new Blob(chunks, { type: 'audio/wav' });
                const audioURL = URL.createObjectURL(blob);
                //audioPlayer.src = audioURL;
                //audioPlayer.controls = true;
                chunks = []; // Очищаем массив записей
    
    
                fetch('/process-sound', {
                    method: 'POST',
                    body: blob,
                    headers: {'Content-Type': 'application/octet-stream'}
                })
                .then(res => res.json()) // Теперь ожидаем JSON
                .then(jsonResponse => {
                    if (jsonResponse.status === 200) {
                        // Декодируем base64-значение в BLOB
                        const byteCharacters = atob(jsonResponse.data);
                        const byteNumbers = new Array(byteCharacters.length);
                        for (let i = 0; i < byteCharacters.length; i++) {
                            byteNumbers[i] = byteCharacters.charCodeAt(i);
                        }
                        const byteArray = new Uint8Array(byteNumbers);
                        const processedBlob = new Blob([byteArray], {type: 'audio/wav'});
    
                        // Устанавливаем источник и начинаем воспроизведение
                        const processedAudioURL = URL.createObjectURL(processedBlob);
                        audioPlayer.src = processedAudioURL;
                        audioPlayer.play(); // Автоматически запускаем воспроизведение
                        audioPlayer.visible = false;
                    } else {
                        alert(`Ошибка: статус ${jsonResponse.status}`);
                    }
                })
                .catch(err => alert(`Ошибка: ${err}`));
    
            };
    
            mediaRecorder.start();
            recordingStatus.textContent = 'Идет запись...';
            recordingStatus.style.display = 'block';
            startBtn.value = 'Закончить ответ';
        } catch (err) {
            console.error(err);
        }
    }
    else
    {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            recordingStatus.style.display = 'none';
            startBtn.value = 'Запустить запись ответа';
        }
    }
}

// Функция остановки записи
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        recordingStatus.style.display = 'none';
        startBtn.value = 'Запустить запись ответа';
    }
}

// Назначаем обработчики кнопкам
startBtn.addEventListener('click', startRecording);
startBtn.addEventListener('click', stopRecording);

document.getElementById('resume-upload').addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('resume-upload', file);

        fetch('/upload/resume', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ошибка при загрузке резюме');
        });
        event.target.value = '';
    }
});

document.getElementById('vacancy-upload').addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('vacancy-upload', file);

        fetch('/upload/vacancy', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ошибка при загрузке вакансии');
        });
        event.target.value = '';
    }
});