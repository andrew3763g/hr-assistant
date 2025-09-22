import sys
import types


# --- Pydantic stub ---
if "pydantic" not in sys.modules:
    pydantic_stub = types.ModuleType("pydantic")

    class BaseModel:  # pragma: no cover - minimal stub
        def __init__(self, *args, **kwargs):
            pass

    pydantic_stub.BaseModel = BaseModel
    sys.modules["pydantic"] = pydantic_stub


# --- FastAPI stub ---
if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str | dict | None = None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        def get(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    def identity(*args, **kwargs):
        return None

    status_module = types.SimpleNamespace(
        HTTP_200_OK=200,
        HTTP_400_BAD_REQUEST=400,
        HTTP_401_UNAUTHORIZED=401,
        HTTP_404_NOT_FOUND=404,
        HTTP_503_SERVICE_UNAVAILABLE=503,
    )

    fastapi_stub.APIRouter = APIRouter
    fastapi_stub.Body = identity
    fastapi_stub.Depends = identity
    fastapi_stub.File = identity
    fastapi_stub.Form = identity
    fastapi_stub.HTTPException = HTTPException
    fastapi_stub.UploadFile = object
    fastapi_stub.status = status_module

    sys.modules["fastapi"] = fastapi_stub
    sys.modules["fastapi.status"] = status_module


# --- SQLAlchemy stub (typing only) ---
if "sqlalchemy" not in sys.modules:
    sqlalchemy_stub = types.ModuleType("sqlalchemy")
    sqlalchemy_orm_stub = types.ModuleType("sqlalchemy.orm")
    sqlalchemy_pool_stub = types.ModuleType("sqlalchemy.pool")

    class Session:  # pragma: no cover - placeholder for typing only
        pass

    class Pool:  # pragma: no cover - placeholder for event registration
        pass

    sqlalchemy_orm_stub.Session = Session
    sqlalchemy_pool_stub.Pool = Pool
    sys.modules["sqlalchemy"] = sqlalchemy_stub
    sys.modules["sqlalchemy.orm"] = sqlalchemy_orm_stub
    sys.modules["sqlalchemy.pool"] = sqlalchemy_pool_stub


# --- Backend settings stub ---
if "backend.app.config" not in sys.modules:
    config_stub = types.ModuleType("backend.app.config")
    settings = types.SimpleNamespace(
        MEDIA_UPLOAD_ROOT="./tmp_media",
        FFMPEG_BIN="ffmpeg",
        EXTRACT_WAV=1,
        CORS_ALLOW_ORIGINS=["*"],
        ADMIN_TOKEN="changeme",
        GD_BACKUPS_FOLDER_ID="",
        STORAGE_BACKEND="local",
    )
    config_stub.settings = settings
    sys.modules["backend.app.config"] = config_stub


# --- Backend database stub ---
if "backend.app.database" not in sys.modules:
    database_stub = types.ModuleType("backend.app.database")

    def get_db():  # pragma: no cover - dependency placeholder
        raise RuntimeError("Database access not available in tests")

    database_stub.get_db = get_db
    sys.modules["backend.app.database"] = database_stub


# --- Models stubs ---
if "backend.app.models" not in sys.modules:
    models_stub = types.ModuleType("backend.app.models")
    candidate_stub = types.ModuleType("backend.app.models.candidate")
    vacancy_stub = types.ModuleType("backend.app.models.vacancy")
    interview_stub = types.ModuleType("backend.app.models.interview")
    message_stub = types.ModuleType("backend.app.models.interview_message")

    class Candidate:  # pragma: no cover - placeholder
        pass

    class Vacancy:  # pragma: no cover - placeholder
        pass

    class _Status:
        def __init__(self, value: str):
            self.value = value

    class InterviewStatus:
        CREATED = _Status("created")
        IN_PROGRESS = _Status("in_progress")
        COMPLETED = _Status("completed")

    class Interview:  # pragma: no cover - placeholder
        def __init__(self, *args, **kwargs):
            pass

    class InterviewMessage:  # pragma: no cover - placeholder
        def __init__(self, *args, **kwargs):
            pass

    class MessageRole:
        INTERVIEWER = "interviewer"
        CANDIDATE = "candidate"

    candidate_stub.Candidate = Candidate
    vacancy_stub.Vacancy = Vacancy
    interview_stub.Interview = Interview
    interview_stub.InterviewStatus = InterviewStatus
    message_stub.InterviewMessage = InterviewMessage
    message_stub.MessageRole = MessageRole

    models_stub.Candidate = Candidate
    models_stub.Vacancy = Vacancy
    models_stub.Interview = Interview
    models_stub.InterviewMessage = InterviewMessage
    models_stub.MessageRole = MessageRole

    sys.modules["backend.app.models"] = models_stub
    sys.modules["backend.app.models.candidate"] = candidate_stub
    sys.modules["backend.app.models.vacancy"] = vacancy_stub
    sys.modules["backend.app.models.interview"] = interview_stub
    sys.modules["backend.app.models.interview_message"] = message_stub


# --- Schemas stub ---
if "backend.app.schemas.interview" not in sys.modules:
    schemas_stub = types.ModuleType("backend.app.schemas.interview")

    class InterviewChatRequest:  # pragma: no cover - placeholder
        interview_id: int
        message: str

        def __init__(self, interview_id: int, message: str):
            self.interview_id = interview_id
            self.message = message

        @property
        def text(self) -> str:
            return self.message

    class InterviewChatResponse:  # pragma: no cover
        def __init__(self, interview_id: int, response: str, is_complete: bool):
            self.interview_id = interview_id
            self.response = response
            self.is_complete = is_complete

    class InterviewCreate:  # pragma: no cover
        def __init__(self, candidate_id: int, vacancy_id: int, questions=None, expires_in_days: int = 7):
            self.candidate_id = candidate_id
            self.vacancy_id = vacancy_id
            self.questions = questions
            self.expires_in_days = expires_in_days

    class InterviewQuestionSchema:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            pass

    class InterviewResponse:  # pragma: no cover
        pass

    schemas_stub.InterviewChatRequest = InterviewChatRequest
    schemas_stub.InterviewChatResponse = InterviewChatResponse
    schemas_stub.InterviewCreate = InterviewCreate
    schemas_stub.InterviewQuestionSchema = InterviewQuestionSchema
    schemas_stub.InterviewResponse = InterviewResponse

    sys.modules["backend.app.schemas.interview"] = schemas_stub


# --- Services stubs ---
if "backend.app.services.ai_service" not in sys.modules:
    ai_service_stub = types.ModuleType("backend.app.services.ai_service")

    class AIInterviewer:  # pragma: no cover
        def conduct_interview_turn(self, *args, **kwargs):
            return {}

    ai_service_stub.AIInterviewer = AIInterviewer
    sys.modules["backend.app.services.ai_service"] = ai_service_stub

if "backend.app.services.gdrive_service" not in sys.modules:
    gdrive_stub = types.ModuleType("backend.app.services.gdrive_service")

    class DummyStorage:  # pragma: no cover
        def upload(self, *args, **kwargs):
            return "dummy"

        def download(self, *args, **kwargs):
            return b""

    def get_storage():  # pragma: no cover
        return DummyStorage()

    gdrive_stub.get_storage = get_storage
    sys.modules["backend.app.services.gdrive_service"] = gdrive_stub

if "backend.app.services.media_joiner" not in sys.modules:
    media_stub = types.ModuleType("backend.app.services.media_joiner")

    def ensure_ffmpeg(*args, **kwargs):  # pragma: no cover
        return True

    def extract_wav(*args, **kwargs):  # pragma: no cover
        return None

    def join_webm_chunks(*args, **kwargs):  # pragma: no cover
        return None

    media_stub.ensure_ffmpeg = ensure_ffmpeg
    media_stub.extract_wav = extract_wav
    media_stub.join_webm_chunks = join_webm_chunks
    sys.modules["backend.app.services.media_joiner"] = media_stub


from backend.app.api import interviews


def test_generate_questions_default_texts():
    questions = interviews._generate_questions(None)
    assert len(questions) == 6

    expected_fragments = [
        "расскажите, пожалуйста, кратко о себе",
        "Опишите последний значимый проект",
        "Какие языки программирования, фреймворки",
        "Как вы организуете взаимодействие с командой",
        "Что для вас сейчас наиболее важно",
        "Какие вопросы у вас есть к нам",
    ]

    for question, fragment in zip(questions, expected_fragments):
        assert fragment in question["text"]
        assert question["type"] == "open"
        assert question["required"] is True


def test_conduct_turn_follow_up_variants():
    short_message = "Работал над сервисом"
    result_short = interviews._conduct_turn((), short_message, None)
    assert result_short["response"].startswith("Спасибо за ответ.")
    assert "Могли бы вы уточнить" in result_short["response"]

    long_message = "Проект включал разработку API, интеграцию с внешними сервисами и настройку CI/CD." * 2
    result_long = interviews._conduct_turn((), long_message, None)
    assert result_long["response"].startswith("Спасибо за ответ.")
    assert "Перейдём к следующему вопросу" in result_long["response"]


def test_evaluate_interview_fallback_texts():
    history = ({"role": "user", "content": "Ответ"},)
    evaluation = interviews._evaluate_interview(history, None)

    assert evaluation["recommendation"] == "Рекомендую пригласить на следующий этап технического интервью."
    assert "чёткая структура ответов" in evaluation["strengths"]
    assert "недостаточно примеров нагрузочного тестирования" in evaluation["weaknesses"]
    assert "Кандидат уверенно описывает" in evaluation["hr_comment"]
