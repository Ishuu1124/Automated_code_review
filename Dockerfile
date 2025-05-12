FROM python:3.11.12-slim-bookworm

COPY . .

RUN pip install -r requirements.txt

ENTRYPOINT [ "./start_celery.sh" ]