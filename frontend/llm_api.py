#!/usr/bin/env python
from langchain_gigachat.chat_models import GigaChat
import speech_recognition as sr
import configparser
from gtts import gTTS
import os
from flask import Flask, request, jsonify

# Чтение настроек из конфига
config = configparser.ConfigParser()
config.read('config.ini')
API_KEY = config.get('gigachat', 'authkey')

# Создание экземпляра GigaChat
giga = GigaChat(credentials=API_KEY, verify_ssl_certs=False)


def ask_model(msg, prompt="Переведи следующее сообщение с русского на английский"):
    """Отсылаем запрос в модель GigaChat"""
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": msg}
    ]
    result = giga.invoke(messages)
    return result.content


def text_to_speech(text, out_filename='output.mp3'):
    """Преобразуем текст в звук и сохраняем файл."""
    tts = gTTS(text=text, lang='ru')
    tts.save(out_filename)


def file_to_text(filename='in.wav'):
    """Распознаём речь из аудиофайла."""
    r = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio_data = r.record(source)
    try:
        recognized_text = r.recognize_google(audio_data, language='ru-RU')
    except Exception as e:
        print("Ошибка:", str(e))
        return ''
    return recognized_text


if __name__ == '__main__':

    app = Flask(__name__)


    @app.route('/convert_audio_to_text', methods=['POST'])
    def convert_audio_to_text():
        """Обрабатываем аудиофайл и возвращаем распознанный текст."""
        if 'audio' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400

        audio_file = request.files['audio']
        filename = 'temp_in.wav'
        audio_file.save(filename)

        recognized_text = file_to_text(filename)
        os.remove(filename)  # Удаляем временный файл

        return jsonify({'recognized_text': recognized_text})


    @app.route('/text_to_speech', methods=['POST'])
    def generate_text_to_speech():
        """Генерируем звуковое сообщение по переданному тексту."""

        text = request.json.get('text', '')

        print(text)
        output_filename = 'output.mp3'
        text_to_speech(text, output_filename)

        return jsonify({'message': f'Файл сохранён как {output_filename}'})


    @app.route('/ask_model', methods=['POST'])
    def process_request():
        """Обращаемся к модели GigaChat с заданием и получаем ответ."""
        data = request.json
        message = data.get('message', '')
        response = ask_model(message)
        return jsonify({'response': response})


    app.run(debug=True)