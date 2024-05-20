# FROM jsbroks/coco-annotator:python-env
FROM python:latest

WORKDIR /

# Install python package dependices
COPY ./backend/ /backend/
RUN mv /backend/start.py /start.py
#COPY ./.git /backend/.git
# RUN python set_path.py
RUN apt update && apt install -y libgl1-mesa-glx
RUN pip install -r /backend/requirements.txt

ENV FLASK_ENV=development
ENV DEBUG=true

EXPOSE 5000
#CMD gunicorn -c /workspace/webserver/gunicorn_config.py webserver:app --no-sendfile
CMD python /start.py
