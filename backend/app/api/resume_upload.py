# backend/app/api/resume_upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
import random
import json
import re
import io

router = APIRouter()

# Временное хранилище в памяти
_parsed_resumes = {}


# Простой парсер резюме без внешних зависимостей
class SimpleResumeParser:
    def parse(self, content: bytes, file_type: str) -> dict:
        """Упрощенный парсер резюме"""
        try:
            # Извлекаем текст
            if file_type == 'txt':
                text = content.decode('utf-8', errors='ignore')
            elif file_type == 'pdf':
                # Простая обработка PDF
                try:
                    import PyPDF2
                    pdf_file = io.BytesIO(content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                except:
                    text = "PDF parsing failed - using mock data"
            elif file_type == 'docx':
                # Простая обработка DOCX
                try:
                    import docx
                    doc_file = io.BytesIO(content)
                    doc = docx.Document(doc_file)
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                except:
                    text = "DOCX parsing failed - using mock data"
            else:
                text = str(content)

            # Извлекаем данные
            result = {
                "full_text": text[:1000],  # Первые 1000 символов
                "name": self._extract_name(text),
                "email": self._extract_email(text),
                "phone": self._extract_phone(text),
                "skills": self._extract_skills(text),
                "experience_years": self._extract_experience_years(text),
                "education": self._extract_education(text),
                "summary": text[:300] if text else "No summary available"
            }

            return result

        except Exception as e:
            print(f"Parse error: {e}")
            # Возвращаем mock данные при ошибке
            return {
                "full_text": "Unable to parse file",
                "name": "Test Candidate",
                "email": "test@example.com",
                "phone": "+7 900 123-45-67",
                "skills": ["Python", "JavaScript", "SQL"],
                "experience_years": 3,
                "education": ["Bachelor's in Computer Science"],
                "summary": "Experienced developer"
            }

    def _extract_name(self, text: str) -> str:
        """Извлечение имени"""
        lines = text.split('\n')
        for line in lines[:5]:
            if line and len(line) < 50 and '@' not in line and 'http' not in line:
                words = line.strip().split()
                if 2 <= len(words) <= 4:
                    return line.strip()
        return "Unknown Name"

    def _extract_email(self, text: str) -> str:
        """Извлечение email"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else "no-email@example.com"

    def _extract_phone(self, text: str) -> str:
        """Извлечение телефона"""
        phone_patterns = [
            r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{10,11}'
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                return phones[0]
        return ""

    def _extract_skills(self, text: str) -> list:
        """Извлечение навыков"""
        tech_skills = [
            'Python', 'JavaScript', 'TypeScript', 'Java', 'C#', 'C++', 'Go', 'Rust', 'PHP', 'Ruby',
            'React', 'Angular', 'Vue', 'HTML', 'CSS', 'Node.js', 'Express', 'FastAPI', 'Django', 'Flask',
            'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes', 'AWS', 'Git'
        ]

        found_skills = []
        text_lower = text.lower()
        for skill in tech_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)

        return found_skills[:10] if found_skills else ["General Skills"]

    def _extract_experience_years(self, text: str) -> float:
        """Извлечение опыта в годах"""
        patterns = [
            r'(\d+)\s*(?:лет|года?|years?)\s*(?:опыта?|experience)',
            r'(?:опыт|experience)\s*(\d+)\s*(?:лет|года?|years?)'
        ]

        for pattern in patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                return float(matches.group(1))
        return 2.0  # Default

    def _extract_education(self, text: str) -> list:
        """Извлечение образования"""
        education_keywords = ['университет', 'university', 'институт', 'institute', 'college', 'bachelor', 'master']
        education = []

        lines = text.split('\n')
        for line in lines:
            for keyword in education_keywords:
                if keyword in line.lower() and len(line) < 100:
                    education.append(line.strip())
                    break

        return education[:2] if education else ["Higher Education"]


# Создаем экземпляр парсера
parser = SimpleResumeParser()


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Загрузка и парсинг резюме"""

    # Определяем тип файла
    file_type = 'txt'  # default
    if file.filename.endswith('.pdf'):
        file_type = 'pdf'
    elif file.filename.endswith('.docx'):
        file_type = 'docx'
    elif file.filename.endswith('.txt'):
        file_type = 'txt'

    # Читаем содержимое
    content = await file.read()

    # Парсим резюме
    try:
        parsed_data = parser.parse(content, file_type)

        # Сохраняем в памяти
        resume_id = random.randint(1000, 9999)
        _parsed_resumes[resume_id] = parsed_data

        # Готовим ответ
        response = {
            "resume_id": resume_id,
            "filename": file.filename,
            "name": parsed_data.get("name", ""),
            "email": parsed_data.get("email", ""),
            "phone": parsed_data.get("phone", ""),
            "skills": parsed_data.get("skills", []),
            "experience_years": parsed_data.get("experience_years"),
            "education": parsed_data.get("education", []),
            "summary": parsed_data.get("summary", "")[:200]
        }

        return response

    except Exception as e:
        print(f"Upload error: {e}")
        # Возвращаем mock данные при ошибке
        return {
            "resume_id": random.randint(1000, 9999),
            "filename": file.filename,
            "name": "Test Candidate",
            "email": "test@example.com",
            "phone": "+7 900 123-45-67",
            "skills": ["Python", "JavaScript", "React"],
            "experience_years": 3,
            "education": ["Bachelor's Degree"],
            "summary": "Experienced developer with strong skills"
        }


@router.get("/parsed/{resume_id}")
async def get_parsed_resume(resume_id: int):
    """Получение распарсенного резюме по ID"""
    if resume_id not in _parsed_resumes:
        # Возвращаем mock данные если не найдено
        return {
            "resume_id": resume_id,
            "name": "Mock Candidate",
            "email": "mock@example.com",
            "skills": ["Python", "JavaScript"],
            "experience_years": 2,
            "education": ["University"],
            "summary": "Mock resume data"
        }

    return _parsed_resumes[resume_id]


@router.post("/generate-questions/{resume_id}")
async def generate_interview_questions(resume_id: int):
    """Генерация вопросов на основе резюме"""

    # Получаем данные резюме
    if resume_id in _parsed_resumes:
        resume_data = _parsed_resumes[resume_id]
    else:
        resume_data = {
            "skills": ["Python", "JavaScript"],
            "experience_years": 2,
            "name": "Candidate"
        }

    skills = resume_data.get("skills", [])
    experience_years = resume_data.get("experience_years", 0)

    # Определяем уровень
    if experience_years < 2:
        level = "Junior"
    elif experience_years < 5:
        level = "Middle"
    else:
        level = "Senior"

    # Генерируем вопросы
    questions = [
        "Расскажите о себе и вашем опыте работы",
        f"Какой опыт работы с {skills[0]} у вас есть?" if skills else "Расскажите о технологиях, с которыми работали",
        "Опишите самый сложный проект"
    ]

    # Добавляем специфичные вопросы
    if "React" in skills:
        questions.append("Объясните разницу между props и state в React")
    if "Python" in skills:
        questions.append("Что такое декораторы в Python?")
    if "Docker" in skills:
        questions.append("Для чего используется Docker?")

    # Вопросы по уровню
    if level == "Senior":
        questions.extend([
            "Как вы проводите код-ревью?",
            "Опишите вашу роль в проектировании архитектуры"
        ])
    elif level == "Middle":
        questions.extend([
            "Как подходите к изучению новых технологий?",
            "Расскажите о работе в команде"
        ])
    else:
        questions.extend([
            "Что вас мотивирует в программировании?",
            "Какие ресурсы используете для обучения?"
        ])

    return {
        "resume_id": resume_id,
        "candidate_name": resume_data.get("name", "Unknown"),
        "level": level,
        "experience_years": experience_years,
        "skills": skills,
        "questions": questions[:7]  # Максимум 7 вопросов
    }