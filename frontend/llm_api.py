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


from pydub import AudioSegment


def convert_webm_to_wav(input_path, output_path):
    audio = AudioSegment.from_file(input_path, format="webm")
    audio.export(output_path, format="wav")


#######################################
#          TESTS                      #
#######################################
def test_audio():
    ''' test audio input -> llm -> audio output'''
    in_file = 'input_audio.wav'
    in2_file = 'input2_audio.wav'
    out_file = 'output_audio.wav'
    convert_webm_to_wav(in_file,in2_file)
    txt = file_to_text(in2_file)
    txt2 = ask_model(txt)
    print(txt, ' -> ', txt2)
    text_to_speech(txt2,out_file)

if __name__ == '__main__':

    from parse_documents import convert_file_to_text
    resume = open('resume/Алексей Владимирович Черкасов - специалист ИТ.txt').read()
    vacancy = open('vacancy/vak1.txt')
    promt = f'''
    Описание вакансии следующее: {vacancy}
    
    Описание резюме: {resume}
    '''
    txt2 = ask_model('Напиши список требований вакансии и напротив каждого пункта через тире "да" если резюме соответствует, и "нет" если резюме не соответствует вакансии. Дополнительно напиши количество соответствующих пунктов и не соответствующих.', promt)
    print(' -> ', txt2)
