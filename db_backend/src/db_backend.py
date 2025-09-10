#!/usr/bin/env python
# coding: utf-8

# In[84]:


#!/big/venv/cuda/bin/python
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, trim_messages
from langgraph.prebuilt import create_react_agent
import uuid
import os
import configparser
from time import sleep
from glob import glob
import re
import psycopg2


# # Модель

# In[87]:


# читаем конфиг
config = configparser.ConfigParser()
config.read('config.ini')
API_KEY=config.get('gigachat', 'authkey')

# модель
model = GigaChat(
    credentials=API_KEY,
    verify_ssl_certs=False,
)



# ## Читаем вакансию и генерируем списки вопросов

# In[3]:


def get_connection():
    conn = psycopg2.connect(
        dbname="hrdb",
        user="hruser",
        password="hrpassword",
        host="postgres",
        port="5432"
    )
    return conn


# In[4]:


def generate_skills_question_list(vacancy):
    promt=f'''
    вакансия: {vacancy}
    '''
    bq=f'''Сформулиуй краткий список требований кандидату согласно вакансии
    
    Список вопросов не должен включать пояснения и дополнительную информацию. 
    '''
    res = model.invoke([SystemMessage(promt), HumanMessage(bq)])
    questions = res.content.replace('- ','').split('\n')
    return questions





# ### читаем данные из БД

# In[14]:


def query_db(query):
    con = get_connection()
    cur = con.cursor()
    cur.execute(query)
    res= cur.fetchall()
    con.close()
    return res

    
def exec_db(*query):
    con = get_connection()
    cur = con.cursor()
    cur.execute(*query)
    con.commit()
    con.close()


# In[88]:


def parse_requirements():
    res = query_db('''
    select * from vacancies v 
    where v.requirements is null 
    ''')
    
    
    for v in res:
        vacancy = v[1]
        skill_question_list = generate_skills_question_list(vacancy)
        exec_db('update vacancies set requirements=%s where vacancy_file=%s',(skill_question_list,v[0]))


# In[92]:


# insert new score lines
def insert_new_scores():
    exec_db('''
    with t1 as (
    select r2.id rid, v2.id vid from resume r2 ,vacancies v2 
    ),
    t2 as (
    select rid,vid from  resume_vacancies_correspondence rvc
    full join t1 on t1.rid=rvc.resume_id and t1.vid = rvc.vacancy_id
    where rvc.resume_id is null
    )
    insert into resume_vacancies_correspondence (resume_id,  vacancy_id)
    select * from t2
    ''')


# In[90]:


def extract_fio():
    # извлечение фио из вакансий 
    res = query_db('''
    select r.id, r.resume_text  from resume r
    where r.fio is null
    ''')
    for row in res:
        resume = row[1]
        promt=f'''
        резюме: {resume}
        '''
        bq=f'''напиши Фамилию Имя Отчество кандидата согласно резюме. коротко без пояснений
        '''
        res = model.invoke([SystemMessage(promt), HumanMessage(bq)])
        fio = res.content.replace('.','')
        exec_db('update resume set fio=%s where id=%s',(fio,row[0]))


# In[89]:


# первичная оценка
def calc_first_score():
    res = query_db('''
    select rvc.vacancy_id, v.requirements,rvc.resume_id, r.resume_text  from resume_vacancies_correspondence rvc
    join vacancies v on v.id = rvc.vacancy_id
    join resume r on r.id = rvc.resume_id 
    where rvc.score is NULL
    ''')
    for row in res:
        vacancy = '\n'.join(row[1])
        print(row)
        resume = row[3]
        promt=f'''
        резюме: {resume}
        требования: {vacancy}
        '''
        bq=f'''напиши список требований вакансии. Каждый элемент списка должен занимать одну строку. В конце строки надо указать соответствует или нет вакансия этому требованию. 
        '''
        res = model.invoke([SystemMessage(promt), HumanMessage(bq)])
        
        # расчет score
        full = len(res.content.split('\n'))
        ok = len(re.findall('Соответствует', res.content))
        half = len(re.findall('Частично соответствует', res.content))
        s=ok+half*0.5
        exec_db('update resume_vacancies_correspondence set score=%s where resume_id=%s and vacancy_id=%s',(s/full,row[2],row[0]))



# In[98]:


#initiate interviews
def init_new_interviews():
    res = query_db('''
    select v.id, r.id,r.fio from resume_vacancies_correspondence rvc
    join vacancies v on v.id = rvc.vacancy_id
    join resume r on r.id = rvc.resume_id 
    left join interviews i on i.vacancy = v.id and i.resume =r.id
    where rvc.score > (select mp.min_percent/100.0  from min_percent mp)
    and i.uuid is null 
    ''')
    for row in res:
        vacancy = row[0]
        resume = row[1]
        _uuid = str(uuid.uuid4())
        print(row[2],'->',_uuid)
        exec_db('''insert into interviews (uuid,message,vacancy,resume,state)
                values(%s,'',%s,%s,'init')''',(_uuid,vacancy,resume))



# In[99]:


def pooling():
    parse_requirements()
    extract_fio()
    insert_new_scores()
    calc_first_score()
    init_new_interviews()


# In[100]:


from time import sleep

while True:
    pooling()
    sleep(10)


# In[ ]:




