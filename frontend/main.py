from flask import Flask, render_template, request, send_from_directory, jsonify
import os
from werkzeug.utils import secure_filename
from pydub import AudioSegment
import base64
import llm_api


ALLOWED_EXTENSIONS = {'wav', 'mp3'}
ALLOWED_EXTENSIONS_DOCS = {'doc', 'pdf', 'docx'}

app = Flask(__name__)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_DOCS


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('index.html')


@app.route('/process-sound', methods=['POST'])
def process_sound():
    # Читаем поступивший файл
    raw_data = request.get_data()

    # Создаем временный файл для хранения входящей аудиодорожки
    temp_input_file2 = 'input_audio.webm'
    temp_input_file = 'input_audio.webm'
    temp_output_file = 'output_audio.wav'
    with open(temp_input_file2, 'wb') as input_file:
        input_file.write(raw_data)
    convert_webm_to_wav(temp_input_file2, temp_input_file)

    in_text = llm_api.file_to_text(temp_input_file)
    out_text=llm_api.ask_model(in_text)
    llm_api.text_to_speech(out_text,temp_output_file)
    #temp_output_file = temp_input_file

    # Преобразование в base64
    with open(temp_output_file, 'rb') as output_file:
        encoded_data = base64.b64encode(output_file.read()).decode('utf-8')

    # Удаляем временные файлы
    #os.remove(temp_input_file)
    #os.remove(temp_output_file)

    # Формируем JSON-ответ
    return jsonify({
        'status': 200,
        'data': encoded_data
    }), 200


def convert_webm_to_wav(input_path, output_path):
    audio = AudioSegment.from_file(input_path, format="webm")
    audio.export(output_path, format="wav")


@app.route('/upload/resume', methods=['POST'])
def resume_upload():
    if 'resume-upload' not in request.files:
        print('No file part')
        return jsonify({'error': 'No file part'}), 400

    file = request.files['resume-upload']

    if file.filename == '':
        print('No selected file')
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join('resume_raw', filename)
        file.save(filepath)
        print('Resume uploaded.')
        return jsonify({'message': f'Резюме загружено: {filename}'}), 200
    else:
        print('Invalid file type')
        return jsonify({'error': 'Invalid file type'}), 400


@app.route('/upload/vacancy', methods=['POST'])
def vacancy_upload():
    if 'vacancy-upload' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['vacancy-upload']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join('vacancy_raw', filename)
        file.save(filepath)
        return jsonify({'message': f'Вакансия загружена: {filename}'}), 200
    else:
        return jsonify({'error': 'Invalid file type'}), 400

@app.route('/get_state', methods=['GET'])
def get_state():
    # Здесь можно реализовать логику получения состояния
    state = "initial"  # Пример значения
    return jsonify({'state': state})

@app.route('/get_question', methods=['POST'])
def get_question():
    data = request.get_json()
    state = data.get('state')

    if not state:
        return jsonify({'error': 'Missing "state" parameter'}), 400

    # Здесь можно вызвать LLM, сформировать ответ и преобразовать его в аудио
    out_text = llm_api.ask_model('Поздоровайся, спроси является ли пользователь администратором или кандидатом на вакансию', '')  # Пример вызова модели
    llm_api.text_to_speech(out_text)  # Предположим, функция возвращает путь к файлу
    audio_path = 'output.mp3'

    with open(audio_path, 'rb') as f:
        encoded_audio = base64.b64encode(f.read()).decode('utf-8')

    return jsonify({
        'audio_data': encoded_audio,
        'message': 'Вопрос получен'
    })


if __name__ == '__main__':
    app.run(debug=True)