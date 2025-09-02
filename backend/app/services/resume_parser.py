# backend/app/services/resume_parser.py
"""
Парсер резюме из PDF, DOCX, TXT файлов
Извлекает: имя, контакты, навыки, опыт работы, образование
"""
import re
from typing import Dict, List, Optional
import PyPDF2
import docx
import io


class ResumeParser:
    def __init__(self):
        # Ключевые слова для поиска секций
        self.section_keywords = {
            'experience': ['опыт работы', 'experience', 'работа', 'employment', 'карьера'],
            'education': ['образование', 'education', 'обучение', 'учеба'],
            'skills': ['навыки', 'skills', 'компетенции', 'технологии', 'стек'],
            'contacts': ['контакты', 'contacts', 'телефон', 'email', 'почта'],
            'summary': ['о себе', 'summary', 'обо мне', 'профиль', 'about']
        }

        # Технические навыки для поиска
        self.tech_skills = [
            # Languages
            'Python', 'JavaScript', 'TypeScript', 'Java', 'C#', 'C++', 'Go', 'Rust', 'PHP', 'Ruby', 'Swift', 'Kotlin',
            # Frontend
            'React', 'Angular', 'Vue', 'HTML', 'CSS', 'SASS', 'Redux', 'Next.js', 'Webpack',
            # Backend
            'Node.js', 'Express', 'FastAPI', 'Django', 'Flask', 'Spring', '.NET', 'Rails',
            # Databases
            'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server', 'Elasticsearch',
            # DevOps
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'CI/CD', 'Jenkins', 'GitLab', 'Terraform',
            # Other
            'Git', 'REST', 'GraphQL', 'Microservices', 'Linux', 'Agile', 'Scrum'
        ]

    def parse(self, file_content: bytes, file_type: str) -> Dict:
        """Главный метод парсинга"""
        text = self._extract_text(file_content, file_type)

        if not text:
            return {"error": "Не удалось извлечь текст из файла"}

        result = {
            "full_text": text,
            "name": self._extract_name(text),
            "email": self._extract_email(text),
            "phone": self._extract_phone(text),
            "skills": self._extract_skills(text),
            "experience_years": self._extract_experience_years(text),
            "education": self._extract_education(text),
            "experience": self._extract_experience_section(text),
            "summary": self._extract_summary(text),
            "languages": self._extract_languages(text)
        }

        return result

    def _extract_text(self, content: bytes, file_type: str) -> str:
        """Извлечение текста из файла"""
        try:
            if file_type == 'pdf':
                return self._extract_pdf_text(content)
            elif file_type == 'docx':
                return self._extract_docx_text(content)
            elif file_type == 'txt':
                return content.decode('utf-8', errors='ignore')
            else:
                return ""
        except Exception as e:
            print(f"Error extracting text: {e}")
            return ""

    def _extract_pdf_text(self, content: bytes) -> str:
        """Извлечение текста из PDF"""
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    def _extract_docx_text(self, content: bytes) -> str:
        """Извлечение текста из DOCX"""
        try:
            doc_file = io.BytesIO(content)
            doc = docx.Document(doc_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            return ""

    def _extract_name(self, text: str) -> str:
        """Извлечение имени (обычно в начале резюме)"""
        lines = text.split('\n')
        for line in lines[:5]:  # Ищем в первых 5 строках
            # Пропускаем пустые строки и слишком длинные
            if line and len(line) < 50 and not any(char in line for char in ['@', 'http', 'www']):
                # Проверяем, похоже ли на имя (2-3 слова, начинаются с заглавной)
                words = line.strip().split()
                if 2 <= len(words) <= 4:
                    if all(word[0].isupper() or word in ['де', 'van', 'von'] for word in words if word):
                        return line.strip()
        return "Не указано"

    def _extract_email(self, text: str) -> str:
        """Извлечение email"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else ""

    def _extract_phone(self, text: str) -> str:
        """Извлечение телефона"""
        # Паттерны для разных форматов телефонов
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

    def _extract_skills(self, text: str) -> List[str]:
        """Извлечение технических навыков"""
        found_skills = []
        text_lower = text.lower()

        for skill in self.tech_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)

        # Дополнительный поиск в секции навыков
        skills_section = self._find_section(text, 'skills')
        if skills_section:
            # Ищем навыки через запятую или точку с запятой
            additional_skills = re.split(r'[,;•·]', skills_section)
            for skill in additional_skills:
                skill = skill.strip()
                if skill and len(skill) < 30:  # Отсекаем слишком длинные строки
                    if skill not in found_skills:
                        found_skills.append(skill)

        return found_skills[:20]  # Ограничиваем количество

    def _extract_experience_years(self, text: str) -> Optional[float]:
        """Извлечение количества лет опыта"""
        # Ищем паттерны вида "5 лет опыта", "опыт 3 года"
        patterns = [
            r'(\d+)\s*(?:лет|года?|years?)\s*(?:опыта?|experience)',
            r'(?:опыт|experience)\s*(\d+)\s*(?:лет|года?|years?)',
            r'(?:стаж|seniority)\s*(\d+)\s*(?:лет|года?|years?)'
        ]

        for pattern in patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                return float(matches.group(1))

        # Альтернатива - подсчет годов из опыта работы
        years = re.findall(r'20\d{2}', text)
        if len(years) >= 2:
            try:
                min_year = min(int(y) for y in years)
                max_year = max(int(y) for y in years)
                return float(max_year - min_year)
            except:
                pass

        return None

    def _extract_education(self, text: str) -> List[str]:
        """Извлечение информации об образовании"""
        education = []
        education_section = self._find_section(text, 'education')

        if education_section:
            lines = education_section.split('\n')
            for line in lines[:5]:  # Берем первые 5 строк из секции
                if line.strip() and len(line) > 10:
                    education.append(line.strip())

        # Дополнительный поиск университетов
        uni_keywords = ['университет', 'university', 'институт', 'institute', 'мгу', 'мфти', 'бауманка']
        for keyword in uni_keywords:
            if keyword in text.lower():
                # Находим строку с университетом
                for line in text.split('\n'):
                    if keyword in line.lower():
                        education.append(line.strip())
                        break

        return education[:3]  # Максимум 3 записи

    def _extract_experience_section(self, text: str) -> List[str]:
        """Извлечение секции опыта работы"""
        experience = []
        exp_section = self._find_section(text, 'experience')

        if exp_section:
            # Разбиваем на компании/позиции
            lines = exp_section.split('\n')
            current_job = ""

            for line in lines:
                if line.strip():
                    # Если строка содержит годы, вероятно это новая работа
                    if re.search(r'20\d{2}', line):
                        if current_job:
                            experience.append(current_job)
                        current_job = line.strip()
                    else:
                        current_job += " " + line.strip()

            if current_job:
                experience.append(current_job)

        return experience[:5]  # Максимум 5 мест работы

    def _extract_summary(self, text: str) -> str:
        """Извлечение раздела 'О себе'"""
        summary_section = self._find_section(text, 'summary')
        if summary_section:
            # Берем первые 500 символов
            return summary_section[:500]

        # Если нет явной секции, берем начало документа после имени
        lines = text.split('\n')
        summary_lines = []
        start_reading = False

        for line in lines[:20]:  # Первые 20 строк
            if not start_reading and line.strip() and not '@' in line:
                start_reading = True
                continue
            if start_reading and line.strip():
                summary_lines.append(line.strip())
                if len(' '.join(summary_lines)) > 300:
                    break

        return ' '.join(summary_lines)[:500]

    def _extract_languages(self, text: str) -> List[str]:
        """Извлечение языков"""
        languages = []
        language_keywords = {
            'английский': ['английский', 'english', 'англ'],
            'русский': ['русский', 'russian'],
            'немецкий': ['немецкий', 'german', 'deutsch'],
            'французский': ['французский', 'french'],
            'испанский': ['испанский', 'spanish'],
            'китайский': ['китайский', 'chinese'],
        }

        text_lower = text.lower()
        for lang, keywords in language_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Пытаемся найти уровень
                    level_match = re.search(f'{keyword}.*?(a1|a2|b1|b2|c1|c2|native|fluent|intermediate|basic)',
                                            text_lower)
                    if level_match:
                        languages.append(f"{lang} ({level_match.group(1)})")
                    else:
                        languages.append(lang)
                    break

        return languages

    def _find_section(self, text: str, section_type: str) -> str:
        """Поиск секции в тексте"""
        keywords = self.section_keywords.get(section_type, [])
        text_lower = text.lower()

        for keyword in keywords:
            # Ищем позицию ключевого слова
            pos = text_lower.find(keyword)
            if pos != -1:
                # Берем текст от этого места до следующей секции или конца
                section_text = text[pos:]

                # Ищем конец секции (начало следующей)
                min_next_pos = len(section_text)
                for other_type, other_keywords in self.section_keywords.items():
                    if other_type != section_type:
                        for other_keyword in other_keywords:
                            next_pos = section_text.lower().find(other_keyword)
                            if next_pos > 100 and next_pos < min_next_pos:  # Минимум 100 символов на секцию
                                min_next_pos = next_pos

                return section_text[:min_next_pos]

        return ""