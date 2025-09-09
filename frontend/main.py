from flask import Flask, render_template, request, send_from_directory, jsonify
import os
from werkzeug.utils import secure_filename
from pydub import AudioSegment
import base64
import llm_api
import db_utils

ALLOWED_EXTENSIONS = {'wav', 'mp3'}
ALLOWED_EXTENSIONS_DOCS = {'doc', 'pdf', 'docx','txt', 'rtf'}

app = Flask(__name__)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_DOCS


@app.route('/')
def home():
    return render_template('index2.html')

@app.route('/admin')
def admin():
    return render_template('index2.html')


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




def load_all_resumes_to_db():
    '''загрузка всех резюме каталога resume в базу'''
    for filename in os.listdir('resume'):
        if filename.endswith('.txt'):
            resume_path = os.path.join('resume', filename)
            resume_text = open(resume_path).read()
            db_utils.load_resume_to_db(filename, resume_text)
            '''удалить файл резюме'''
            os.remove(resume_path)

    ''' очистка каталога resume и resume_raw'''
    for filename in os.listdir('resume_raw'):
        resume_path = os.path.join('resume_raw', filename)
        os.remove(resume_path)

    for filename in os.listdir('resume'):
        resume_path = os.path.join('resume', filename)
        os.remove(resume_path)

def load_all_vacancies_to_db():
    for filename in os.listdir('vacancy'):
        if filename.endswith('.txt'):
            vacancy_path = os.path.join('vacancy', filename)
            vacancy_text = open(vacancy_path).read()
            db_utils.load_vacancy_to_db(filename, vacancy_text)
            '''удалить файл резюме'''
            os.remove(vacancy_path)

    
@app.route('/upload/resume', methods=['POST'])
def resume_upload():
    if 'resume-upload' not in request.files:
        print('No file part')
        return jsonify({'error': 'No file part'}), 400

    file = request.files['resume-upload']
    print('file',file.filename)
    if file.filename == '':
        print('No selected file')
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join('resume_raw', filename)
        file.save(filepath)
        # convert to text
        os.system(f'java -jar tika-app-3.2.2.jar -t -i resume_raw -o resume')
        print(f'Resume {filename} uploaded.')
        load_all_resumes_to_db()
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
        filename = file.filename
        filepath = os.path.join('vacancy_raw', filename)
        file.save(filepath)
        os.system(f'java -jar tika-app-3.2.2.jar -t -i vacancy_raw -o vacancy')
        print(f'Вакансия {filename} загружена. ')
        load_all_vacancies_to_db()


        return jsonify({'message': f'Вакансия загружена: {filename}'}), 200
    else:
        return jsonify({'error': 'Invalid file type'}), 400


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
        'wav': encoded_audio,
        'state': 'new',
        'question': out_text
    })

@app.route('/get_greeting', methods=['POST'])
def get_greeting():
    data = request.get_json()
    state = data.get('state')
    print('state',state)

    if not state:
        return jsonify({'error': 'Missing "state" parameter'}), 400

    if state == 'new':
        # Здесь можно вызвать LLM, сформировать ответ и преобразовать его в аудио
        out_text = llm_api.ask_model('Поздоровайся, перед тобой администратор системы. Предложи загрузить файлы вакансий и резюме', '')  # Пример вызова модели
        llm_api.text_to_speech(out_text)  # Предположим, функция возвращает путь к файлу
        audio_path = 'output.mp3'

        with open(audio_path, 'rb') as f:
            encoded_audio = base64.b64encode(f.read()).decode('utf-8')

        return jsonify({
            'wav': encoded_audio,
            'state': 'new',
            'question': out_text
        })
    else:
        return jsonify({
            'wav': '',
            'state': 'wait',
            'question': ''
        })

@app.route('/interview/<uuid>', methods=['GET'])
def get_user_conv(uuid):
    if not uuid:
        return jsonify({'error': 'Missing "uuid" parameter'}), 400


    db_utils.add_uuid_message_to_db(uuid,'') # начало диалога

    return jsonify({
        'wav': '',
        'state': 'wait',
        'question': ''
    })

if __name__ == '__main__':
    app.run(debug=True)