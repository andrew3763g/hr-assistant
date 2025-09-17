# Development Environment

The project now uses a single virtual environment located at `.venv/`.

1. Ensure Python 3.11.9 is available on your PATH (`C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe`).
2. Create or refresh the environment if needed:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. VS Code picks up the interpreter automatically via `.vscode/settings.json`, but you can select `.venv/` manually from the command palette if needed.
4. Remove any stale `.venv*` folders before recreating the environment to avoid mismatched dependencies.

Run application tasks (FastAPI server, Alembic migrations, tests) from an activated shell that uses `.venv`.
