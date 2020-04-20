FROM python:3.8-buster as build

COPY . .

RUN pip install -U --no-cache-dir pip poetry setuptools wheel && \
    poetry build -f wheel && \
    poetry export -f requirements.txt -o requirements.txt --without-hashes && \
    pip wheel -w dist -r requirements.txt


FROM python:3.8-slim-buster

WORKDIR /usr/src/app

COPY --from=build dist dist
COPY --from=build migrations migrations
COPY --from=build alembic.ini main.py gunicorn.config.py ./

RUN pip install --no-cache-dir dist/*.whl && \
    rm -rf dist

CMD ["gunicorn", "main:app", "-c", "gunicorn.config.py"]
