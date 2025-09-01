from flask import Flask, render_template, request, send_from_directory
import os
from werkzeug.utils import secure_filename
from pydub import AudioSegment
import base64
import llm_api

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    return render_template('index2.html')

from flask import jsonify

def convert_webm_to_wav(input_path, output_path):
    audio = AudioSegment.from_file(input_path, format="webm")
    audio.export(output_path, format="wav")


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




@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']

    if file.filename == '':
        return 'No selected file'

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Здесь можно обработать полученный файл дополнительно (например, преобразовать его в другой формат).
        return f'File uploaded successfully to {filepath}'
    else:
        return 'Invalid file type'


if __name__ == '__main__':
    app.run(debug=True)