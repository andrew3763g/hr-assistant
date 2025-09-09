import psycopg2

# Параметры подключения к PostgreSQL
DB_NAME = "hrdb"
DB_USER = "hruser"
DB_PASSWORD = "hrpassword"
DB_HOST = "localhost"
DB_PORT = "5432"

def init_states_table():
    conn = None
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # SQL-запрос на создание таблицы, если она не существует
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS states (
            id SERIAL PRIMARY KEY,
            state VARCHAR(255) NOT NULL,
            next_state VARCHAR(255) NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        );
        """

        # Выполнение запроса
        cursor.execute(create_table_sql)
        conn.commit()
        print("Таблица 'states' успешно создана или уже существует.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Ошибка при работе с базой данных: {error}")
    finally:
        if conn is not None:
            cursor.close()
            conn.close()
            print("Соединение закрыто.")


def add_state(state, next_state, question, answer):
    conn = None
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        # SQL-запрос на добавление новой записи в таблицу
        insert_sql = """
            INSERT INTO states (state, next_state, question, answer)
            VALUES (%s, %s, %s, %s);
            """
        if conn is not None:
            if cursor.execute(insert_sql, (state, next_state, question, answer)):
                conn.commit()
                print("Запись успешно добавлена в таблицу 'states'.")
            else:
                print("Ошибка при добавлении записи в таблицу 'states'.")
                if conn is not None:
                    conn.rollback()

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Ошибка при работе с базой данных: {error}")
    finally:
        if conn is not None:
            cursor.close()

def get_state_info(state):
    '''подключение к базе данных и получение информации о состоянии из таблицы по имени состояния
    возвращаем следующее состояние, вопрос и ответ'''
    conn = None
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        if conn is not None:
            if cursor.execute("SELECT next_state, question, answer FROM states WHERE state = %s", (state,)):
                result = cursor.fetchall()
            conn.close()
    except (Exception, psycopg2.DatabaseError) as error:
        if conn is not None:
            conn.close()
            print(f"Ошибка при работе с базой данных: {error}")


def fill_states_table():
    add_state('start', 'plan_interview','Здравствуйте, что Вас интересует?', 'Я хотел бы запланировать интервью или я кандидат на должность')


if __name__ == '__main__':
    init_states_table()