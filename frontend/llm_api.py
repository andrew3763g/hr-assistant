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


def check_resume_vacancy_match(resume, vacancy):
    '''проверка соответствия резюме вакансии'''
    # from parse_documents import convert_file_to_text
    resume = open(resume).read()
    vacancy = open(vacancy).read()
    promt = f'''
    Описание вакансии следующее: {vacancy}

    Описание резюме: {resume}
    '''
    txt2 = ask_model(
        'Напиши список требований вакансии и напротив каждого пункта через тире "да" если резюме соответствует, и "нет" если резюме не соответствует вакансии. Дополнительно напиши количество соответствующих пунктов и не соответствующих.',
        promt)
    return txt2

def extract_vacancy_requirements(vacancy):
    vacancy = open(vacancy).read()
    promt = f'''
    Описание вакансии следующее: {vacancy}
    '''
    txt2 = ask_model(
        'Напиши список требований вакансии, кратко, без расшифровки, в виде пронумерованного списка.',
        promt)
    return txt2.replace('*','')

import re
if __name__ == '__main__':
    resume = 'resume/Алексей Владимирович Черкасов - специалист ИТ.txt'
    vacancy = 'vacancy/vak3.txt'
    vacancy2 = 'vacancy/vak1.txt'
    print(extract_vacancy_requirements(vacancy))
    re.split()
    print('=======================================')
    print(extract_vacancy_requirements(vacancy2))

    exit()

    txt2 = check_resume_vacancy_match(resume, vacancy)
    print(' -> ', txt2)
    print('=======================================')
    txt2 = check_resume_vacancy_match(resume, vacancy2)
    print(' -> ', txt2)

import telethon

# call via telethon
def call_telethon(phone_number):
    if phone_number:
        client = telethon.TelegramClient('session_name', api_id, api_hash)
        client.connect()
        if not client.is_user_authorized():
            client.send_code_request(phone_number)
            client.sign_in(phone_number, input('Enter the code: '))
        # make a call
        if client.is_user_authorized():
            client.send_message('me', 'Hello!')
            client.call(phone_number)
            client.disconnect()

