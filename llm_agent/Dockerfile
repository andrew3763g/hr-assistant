FROM python:3.11-slim


RUN mkdir -p /src
RUN chmod -R ugo+rwx /src
RUN python3 -m pip install --upgrade pip
ADD requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt
WORKDIR /tmp
COPY src .
CMD python3 llm_agent.py


