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

def get_all_vacancies():
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT vacancy_file FROM vacancies"
    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def get_all_resumes():
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT resume_file FROM resume"
    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def delete_resume_by_file(resume_file):
    conn = get_connection()
    cursor = conn.cursor()

    query = "DELETE FROM resume WHERE resume_file = %s"
    cursor.execute(query, (resume_file,))
    conn.commit()

    cursor.close()
    conn.close()


def delete_vacancy_by_file(vacancy_file):
    conn = get_connection()
    cursor = conn.cursor()

    query = "DELETE FROM vacancies WHERE vacancy_file = %s"
    cursor.execute(query, (vacancy_file,))
    conn.commit()

    cursor.close()
    conn.close()


def init_tables():
    con = psycopg2.connect(database='hrdb', user='hruser', password='hrpassword', host='localhost')
    cur = con.cursor()

    cur.execute('''
    create table if not exists interviews
    (
    uuid varchar(100) not null,
    message text not null,
    date timestamp default now(),
    vacancy varchar(100) not null,
    resume varchar(100) not null,
    state varchar(100) default 'created'
    )    ''')

    cur.execute('''
    create table if not exists vacancies (
    vacancy_file varchar(100) not null unique,
    vacancy_text text not null,
    requirements varchar(300)[]
    ); ''')

    cur.execute('''
    create table if not exists resume (
    resume_file varchar(100) not null unique,
    resume_text text not null,
    fio varchar(100),
    skills varchar(100)[]
    );

    ''')

    con.commit()
    con.close()


init_tables()