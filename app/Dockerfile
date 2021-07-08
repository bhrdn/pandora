FROM python:3.8-slim-buster

LABEL maintainer="Habib Bahruddin <habibbahruddin@student.telkomuniversity.ac.id>"

COPY . /app
ENV FLASK_APP /app/run.py

WORKDIR /app
RUN pip install -r requirements.txt

USER nobody
CMD [ "python", "-m", "flask", "run", "--host=0.0.0.0" ]