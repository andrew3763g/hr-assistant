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
        INSERT INTO vacancies (vacancy_filename, vacancy_text)
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
        INSERT INTO resumes (resume_filename, resume_text) 
        VALUES (%s, %s)
    """
    cursor.execute(query, (filename, text))

    # Сохранение изменений
    conn.commit()

    # Закрытие соединения
    cursor.close()
    conn.close()
