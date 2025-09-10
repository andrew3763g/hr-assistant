FROM python:3.11-slim



RUN python3 -m pip install --upgrade pip
WORKDIR /src
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src .
CMD python3 db_backend.py


