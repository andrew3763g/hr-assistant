import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api import interviews
from backend.app.database import SessionLocal
from backend.app.models import Candidate, Interview, InterviewMessage, Vacancy
from backend.app.models.interview import InterviewStatus


class StorageRecorder:
    def __init__(self):
        self.uploads: list[tuple[bytes, str, str]] = []

    def upload(self, data: bytes, filename: str, folder_key: str) -> str:
        self.uploads.append((data, filename, folder_key))
        return f"id-{len(self.uploads)}"

    def download(self, file_id: str) -> bytes:  # pragma: no cover - unused here
        raise NotImplementedError


def _setup_client(monkeypatch, tmp_path):
    app = FastAPI()
    app.include_router(interviews.router, prefix="/interviews")
    client = TestClient(app)

    storage = StorageRecorder()

    monkeypatch.setattr(interviews.settings, "MEDIA_UPLOAD_ROOT", str(tmp_path))
    monkeypatch.setattr(interviews.settings, "EXTRACT_WAV", 1)
    monkeypatch.setattr(interviews.settings, "FFMPEG_BIN", "ffmpeg")
    monkeypatch.setattr(interviews, "ensure_ffmpeg", lambda _: True)

    def fake_join(chunks, out_webm, ffmpeg_bin="ffmpeg"):
        data = b"".join(path.read_bytes() for path in chunks)
        out_webm.write_bytes(data)

    def fake_extract(in_webm, out_wav, ffmpeg_bin="ffmpeg"):
        out_wav.write_bytes(in_webm.read_bytes() + b"-wav")

    monkeypatch.setattr(interviews, "join_webm_chunks", fake_join)
    monkeypatch.setattr(interviews, "extract_wav", fake_extract)
    monkeypatch.setattr(interviews, "get_storage", lambda: storage)

    return client, storage


def test_chunk_upload_and_finalize(tmp_path, monkeypatch):
    client, storage = _setup_client(monkeypatch, tmp_path)

    response = client.post(
        "/interviews/upload/chunk",
        data={"session_id": "sess", "kind": "audio", "index": 0},
        files={"chunk": ("chunk0.webm", b"chunk-0", "video/webm")},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    response = client.post(
        "/interviews/upload/chunk",
        data={"session_id": "sess", "kind": "audio", "index": 1},
        files={"chunk": ("chunk1.webm", b"chunk-1", "video/webm")},
    )
    assert response.status_code == 200

    finalize = client.post(
        "/interviews/upload/finalize",
        json={"session_id": "sess"},
    )
    assert finalize.status_code == 200
    payload = finalize.json()
    assert payload["session_id"] == "sess"
    assert payload["artifacts"]["audio"]["webm"].startswith("id-")
    assert payload["artifacts"]["audio"]["wav"].startswith("id-")

    assert len(storage.uploads) == 2
    data_webm, name_webm, key_webm = storage.uploads[0]
    assert name_webm == "sess_audio.webm"
    assert key_webm == "VIDEO"
    assert data_webm == b"chunk-0chunk-1"

    data_wav, name_wav, key_wav = storage.uploads[1]
    assert name_wav == "sess_audio.wav"
    assert key_wav == "AUDIO"
    assert data_wav.endswith(b"-wav")

    session_dir = tmp_path / "sess"
    assert not session_dir.exists()


def test_finalize_missing_session(tmp_path, monkeypatch):
    client, _ = _setup_client(monkeypatch, tmp_path)

    response = client.post(
        "/interviews/upload/finalize",
        json={"session_id": "missing"},
    )
    assert response.status_code == 404


def test_interview_chat_flow_real_db(monkeypatch):
    session = SessionLocal()
    unique_email = f"chat_test_{uuid.uuid4().hex}@example.com"
    candidate = Candidate(first_name="Иван", last_name="Иванов", email=unique_email)
    vacancy = Vacancy(title="Разработчик Python", description="Тестовая вакансия")
    session.add_all([candidate, vacancy])
    session.commit()

    candidate_id = candidate.id
    vacancy_id = vacancy.id
    session.close()

    app = FastAPI()
    app.include_router(interviews.router, prefix="/interviews")
    client = TestClient(app)

    class DummyAI:
        def __init__(self):
            self.turn = 0

        def conduct_interview_turn(self, history, message, vacancy):  # noqa: ARG002
            self.turn += 1
            return {
                "response": f"Спасибо, перейдём к следующему пункту {self.turn}",
                "is_complete": self.turn >= 3,
            }

    monkeypatch.setattr(interviews, "ai_service", DummyAI())

    questions = interviews._generate_questions(vacancy)
    interview = Interview(
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        interview_url="/interviews/manual",
        questions_data=questions,
        total_questions=len(questions),
    )
    token = interview.interview_token
    if token:
        interview.interview_url = f"/interviews/{token}"
    session = SessionLocal()
    session.add(interview)
    session.commit()
    interview_id = interview.id
    session.close()

    try:
        completed = False
        for idx in range(1, 5):
            chat_resp = client.post(
                "/interviews/chat",
                json={"interview_id": interview_id, "message": f"Ответ номер {idx}"},
            )
            assert chat_resp.status_code == 200
            payload = chat_resp.json()
            if payload["is_complete"]:
                completed = True
                break

        assert completed, "Интервью должно завершиться после нескольких обменов"

        report = client.get(f"/interviews/{interview_id}/report")
        assert report.status_code == 200

        verify_session = SessionLocal()
        interview_obj = verify_session.get(Interview, interview_id)
        assert interview_obj is not None
        assert interview_obj.status == InterviewStatus.COMPLETED.value
        assert (
            verify_session.query(InterviewMessage)
            .filter_by(interview_id=interview_id)
            .count()
            >= 2
        )
        verify_session.close()
    finally:
        cleanup_session = SessionLocal()
        cleanup_session.query(InterviewMessage).filter_by(interview_id=interview_id).delete()
        cleanup_session.query(Interview).filter_by(id=interview_id).delete()
        cleanup_session.query(Candidate).filter_by(id=candidate_id).delete()
        cleanup_session.query(Vacancy).filter_by(id=vacancy_id).delete()
        cleanup_session.commit()
        cleanup_session.close()
