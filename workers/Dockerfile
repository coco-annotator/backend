# FROM jsbroks/coco-annotator:python-env
FROM python:latest

WORKDIR /workspace/

# Install python package dependices
COPY ./backend/ /workspace/

RUN pip install -r requirements.txt

EXPOSE 5555
CMD celery -A workers worker -l info
