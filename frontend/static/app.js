const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const recordingStatus = document.getElementById('recording-status');
const audioPlayer = document.querySelector('audio');
let mediaRecorder;
let chunks = [];

// Функция запуска записи
async function startRecording() {
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
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } catch (err) {
        console.error(err);
    }
}

// Функция остановки записи
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        recordingStatus.style.display = 'none';
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

// Назначаем обработчики кнопкам
startBtn.addEventListener('click', startRecording);
stopBtn.addEventListener('click', stopRecording);