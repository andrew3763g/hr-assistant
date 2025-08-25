# backend/app/services/ai_service.py (упрощенная версия без OpenAI для тестирования)
"""
AI сервис для проведения интервью - версия с mock данными для тестирования
"""
from typing import List, Dict, Optional
import json
import random
from app.models.vacancy import Vacancy


class AIInterviewer:
    def __init__(self):
        self.model = "mock-model"
        # Заготовленные вопросы для разных позиций
        self.question_templates = {
            "default": [
                "Расскажите о себе и вашем опыте работы",
                "Почему вы хотите работать в нашей компании?",
                "Какие ваши сильные и слабые стороны?",
                "Где вы видите себя через 5 лет?",
                "Опишите сложную задачу, которую вы успешно решили"
            ],
            "technical": [
                "Какие технологии вы использовали в последнем проекте?",
                "Как вы подходите к проектированию архитектуры?",
                "Расскажите о вашем опыте с тестированием",
                "Как вы оптимизируете производительность?",
                "Какие паттерны проектирования вы применяете?"
            ]
        }

    def generate_interview_questions(self, vacancy: Vacancy, num_questions: int = 5) -> List[str]:
        """Генерация вопросов на основе вакансии"""
        # Mock implementation - возвращаем заготовленные вопросы
        questions = self.question_templates["default"][:3] + self.question_templates["technical"][:2]
        return questions[:num_questions]

    def conduct_interview_turn(self,
                               conversation_history: List[Dict],
                               candidate_message: str,
                               vacancy: Vacancy) -> Dict:
        """Проведение одного хода интервью"""
        # Mock responses
        responses = [
            "Спасибо за ваш ответ. Можете рассказать подробнее о вашем опыте работы с похожими технологиями?",
            "Интересно! А как вы решаете конфликтные ситуации в команде?",
            "Хороший подход. Какие инструменты вы используете для контроля качества кода?",
            "Понятно. Расскажите о самом сложном проекте в вашей карьере.",
            "Отлично! У меня последний вопрос: почему именно вы подходите на эту позицию?"
        ]

        # Определяем, пора ли завершать интервью
        message_count = len(conversation_history)
        is_complete = message_count >= 10  # Завершаем после 10 сообщений

        if is_complete:
            response = "Спасибо за ваши ответы! Интервью завершено. Мы свяжемся с вами в ближайшее время."
        else:
            response = responses[min(message_count // 2, len(responses) - 1)]

        return {
            "response": response,
            "is_complete": is_complete
        }

    def evaluate_interview(self, conversation_history: List[Dict], vacancy: Vacancy) -> Dict:
        """Оценка интервью и генерация отчета"""
        # Mock evaluation
        return {
            "technical_score": round(random.uniform(6, 9), 1),
            "communication_score": round(random.uniform(7, 9), 1),
            "motivation_score": round(random.uniform(6, 9), 1),
            "culture_fit_score": round(random.uniform(7, 9), 1),
            "overall_score": round(random.uniform(7, 8.5), 1),
            "strengths": [
                "Хорошие коммуникативные навыки",
                "Глубокие технические знания",
                "Опыт работы в команде"
            ],
            "weaknesses": [
                "Необходимо улучшить знания в области DevOps",
                "Мало опыта с большими проектами"
            ],
            "recommendation": "Рекомендую пригласить на техническое интервью",
            "hr_comment": "Перспективный кандидат с хорошим потенциалом развития"
        }

# -------------------