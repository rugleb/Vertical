FROM python:3.8-buster as build

COPY . .

RUN unzip oracle/instantclient-*.zip

RUN pip install -U --no-cache-dir pip poetry setuptools wheel && \
    poetry build -f wheel && \
    poetry export -f requirements.txt -o requirements.txt --without-hashes && \
    pip wheel -w dist -r requirements.txt


FROM python:3.8-slim-buster as runtime

WORKDIR /usr/src/app

ENV PYTHONOPTIMIZE true
ENV DEBIAN_FRONTEND noninteractive

ENV ORACLE_HOME /opt/oracle/instantclient
ENV LD_LIBRARY_PATH $ORACLE_HOME:$LD_LIBRARY_PATH

COPY --from=build dist dist
COPY --from=build instantclient_19_6 $ORACLE_HOME
COPY --from=build migrations migrations
COPY --from=build alembic.ini main.py gunicorn.config.py ./

RUN apt-get -y update && \
    apt-get -y install libaio1 && \
    apt-get -y upgrade && \
    apt-get -y clean

RUN pip install -U --no-cache-dir pip dist/*.whl && \
    rm -rf dist

CMD ["gunicorn", "main:app", "-c", "gunicorn.config.py"]
