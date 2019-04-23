FROM python:3.6-alpine

RUN adduser -D justfiles

WORKDIR /home/justfiles

RUN apk add --no-cache curl python3 pkgconfig python3-dev openssl-dev libffi-dev musl-dev make gcc

COPY requirements.txt requirements.txt
RUN python -m venv s3_upload_env
RUN s3_upload_env/bin/pip install -r requirements.txt
RUN s3_upload_env/bin/pip install gunicorn pymysql

COPY app app
COPY migrations migrations
COPY run.py config.py boot.sh ./
RUN chmod a+x boot.sh

ENV FLASK_APP run.py

RUN chown -R justfiles:justfiles ./
USER justfiles

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
