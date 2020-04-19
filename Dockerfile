FROM python:3.8-buster as builder

COPY . .

RUN pip install -U --no-cache-dir pip poetry setuptools wheel && \
    poetry export -f requirements.txt -o requirements.txt --without-hashes && \
    pip wheel -w dist -r requirements.txt


FROM python:3.8-slim-buster

WORKDIR /usr/src/app

COPY --from=builder dist dist
COPY . .

RUN pip install --no-cache-dir dist/*.whl && \
    rm -rf dist

CMD ["gunicorn", "main:app", "-c", "gunicorn.config.py"]
