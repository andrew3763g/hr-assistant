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


@app.route('/get_vacancies', methods=['GET'])
def get_vacancies():
    # Получаем все вакансии из БД
    vacancies = db_utils.get_all_vacancies()

    if not vacancies:
        return jsonify({'error': 'No vacancies found'}), 404

    # Формируем список с полями filename
    vacancy_list = [{'vacancy_file': v[0]} for v in vacancies]
    print(vacancy_list)
    return jsonify(vacancy_list)


@app.route('/get_resumes', methods=['GET'])
def get_resumes():
    # Получаем все резюме из БД
    resumes = db_utils.get_all_resumes()

    if not resumes:
        return jsonify({'error': 'No resumes found'}), 404

    # Формируем список с полями filename
    resume_list = [{'resume_file': r[0]} for r in resumes]
    print(resume_list)
    return jsonify(resume_list)

from db_utils import get_connection
@app.route('/get_min_percent', methods=['GET'])
def get_min_percent():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT min_percent FROM min_percent LIMIT 1;")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result[0] is not None:
            return jsonify({"success": True, "min_percent": result[0]})
        else:
            return jsonify({"success": False, "error": "No data found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/set_min_percent', methods=['POST'])
def set_min_percent():
    data = request.get_json()
    percent = data.get('min_percent')

    if not isinstance(percent, int) or percent < 0 or percent > 100:
        return jsonify({"success": False, "error": "Invalid percentage value"})

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Если запись не существует — создаём новую
        cursor.execute("""
            INSERT INTO min_percent (min_percent)
            VALUES (%s)
            ON CONFLICT (id) DO UPDATE SET min_percent = %s;
        """, (percent, percent))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/')
def home():
    return render_template('index2.html')

@app.route('/admin')
def admin():
    return render_template('index2.html')


def convert_webm_to_wav(input_path, output_path):
    audio = AudioSegment.from_file(input_path, format="webm")
    audio.export(output_path, format="wav")

@app.route('/process-sound/<uuid>', methods=['POST'])
def process_sound(uuid):
    # Читаем поступивший файл
    raw_data = request.get_data()

    # Создаем временный файл для хранения входящей аудиодорожки
    temp_input_file2 = 'input_audio.webm'
    temp_input_file = 'input_audio.webm'
    temp_output_file = 'output_audio.wav'
    with open(temp_input_file2, 'wb') as input_file:
        input_file.write(raw_data)
        audio = AudioSegment.from_file(temp_input_file2)
        audio.export(temp_input_file, format="wav")

    #convert_webm_to_wav(temp_input_file2, temp_input_file)

    in_text = llm_api.file_to_text(temp_input_file)
    print('in_text',in_text)
    print('uuid',uuid)
    db_utils.add_uuid_message_to_db(uuid, in_text)

    # Удаляем временные файлы
    #os.remove(temp_input_file)
    #os.remove(temp_output_file)

    # Формируем JSON-ответ
    return jsonify({
        'status': 200,

    }), 200






def load_all_resumes_to_db():
    '''загрузка всех резюме каталога resume в базу'''
    for filename in os.listdir('resume'):
        if filename.endswith('.txt'):
            resume_path = os.path.join('resume', filename)
            resume_text = open(resume_path).read()
            db_utils.load_resume_to_db(filename, resume_text)


def load_all_vacancies_to_db():
    for filename in os.listdir('vacancy'):
        if filename.endswith('.txt'):
            vacancy_path = os.path.join('vacancy', filename)
            vacancy_text = open(vacancy_path).read()
            db_utils.load_vacancy_to_db(filename, vacancy_text)

    
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
        os.system(f'rm -f resume_raw/*')
        os.system(f'rm -f resume/*')

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
        os.system(f'rm -f vacancy_raw/*')
        os.system(f'rm -f vacancy/*')


        return jsonify({'message': f'Вакансия загружена: {filename}'}), 200
    else:
        return jsonify({'error': 'Invalid file type'}), 400


@app.route('/get_question/<uuid>', methods=['POST'])
def get_question(uuid):
    data = request.get_json()
    state = data.get('state')

    if not state:
        return jsonify({'error': 'Missing "state" parameter'}), 400
    print('Get question',uuid)
    # Здесь вызвать LLM, сформировать ответ и преобразовать его в аудио
    for out_text in  db_utils.get_messages_by_uuid_and_state(uuid):
        print('out_text',out_text)
        db_utils.mark_message_as_processed(out_text['uuid'], out_text['message'])
        llm_api.text_to_speech(out_text['message'])  # Предположим, функция возвращает путь к файлу
        audio_path = 'output.mp3'

        with open(audio_path, 'rb') as f:
            encoded_audio = base64.b64encode(f.read()).decode('utf-8')

        return jsonify({
            'wav': encoded_audio,
            'state': 'new',
            'question': out_text['message']
        })
    return jsonify({
        'wav': '',
        'state': 'wait',
        'question': ''
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
        out_text = llm_api.ask_model('Поздоровайся, перед тобой администратор системы. Кратко предложи загрузить файлы вакансий и резюме', '')  # Пример вызова модели
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
    print('Interview:', uuid)
    if not uuid:
        return jsonify({'error': 'Missing "uuid" parameter'}), 400

    return render_template('index.html', uuid=uuid)

@app.route('/delete_resume/<resume_file>', methods=['DELETE'])
def delete_resume(resume_file):
    try:
        db_utils.delete_resume_by_file(id)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Ошибка удаления резюме: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/delete_vacancy/<vacancy_file>', methods=['DELETE'])
def delete_vacancy(vacancy_file):
    try:
        db_utils.delete_vacancy_by_file(id)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Ошибка удаления вакансии: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)