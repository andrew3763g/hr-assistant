import psycopg2


def get_connection():
    conn = psycopg2.connect(
        dbname="hrdb",
        user="hruser",
        password="hrpassword",
        host="localhost",
        port="5432"
    )
    return conn

def load_vacancy_to_db(filename, text):
    conn = get_connection()

    cursor = conn.cursor()

    # Вставка данных в таблицу vacancies
    query = """
        INSERT INTO vacancies (vacancy_file, vacancy_text)
        VALUES (%s, %s)
    """
    cursor.execute(query, (filename, text))

    # Сохранение изменений
    conn.commit()

    # Закрытие соединения
    cursor.close()
    conn.close()


def load_resume_to_db(filename, text):
    conn = get_connection()

    cursor = conn.cursor()

    # Вставка данных в таблицу vacancies
    query = """
        INSERT INTO resume (resume_file, resume_text) 
        VALUES (%s, %s)
    """
    cursor.execute(query, (filename, text))

    # Сохранение изменений
    conn.commit()

    # Закрытие соединения
    cursor.close()
    conn.close()

def add_uuid_message_to_db(uuid, message=''):
    # Подключение к БД (замените параметры на свои)
    conn = get_connection()
    cursor = conn.cursor()

    # SQL-запрос для вставки данных
    query = """
        INSERT INTO interviews (uuid, message,state)
        VALUES (%s, %s, 'to_process')
    """

    # Выполнение запроса
    cursor.execute(query, (uuid, message))

    # Сохранение изменений
    conn.commit()
    print("Сообщение успешно добавлено в БД.")

    cursor.close()
    conn.close()


def get_messages_by_uuid_and_state(uuid):
    conn = get_connection()
    cursor = conn.cursor()

    # SQL-запрос для получения сообщений
    query = """
        SELECT uuid, message 
        FROM interviews
        WHERE uuid = %s AND state = 'new'
    """

    cursor.execute(query, (uuid,))
    rows = cursor.fetchall()

    # Формирование результата
    messages = []
    for row in rows:
        messages.append({
            'uuid': row[0],
            'message': row[1]
        })

    cursor.close()
    conn.close()

    return messages