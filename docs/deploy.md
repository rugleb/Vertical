# Зависимости

Для успешного развертывания приложения и его запуска необходимо:
1. Предустановленный [Docker Engine 19](https://docs.docker.com/) и выше;
2. Доступ к серверу [Postgres 11](https://www.postgresql.org/docs/11/index.html) и выше.

# Сервис

Сервис состоит из двух зависимых компонент:
1. Приложение (работающее под [Docker]((https://docs.docker.com/)));
2. Миграции базы данных (работающие под СУБД [Postgres](https://www.postgresql.org)).  

## Приложение

Приложение предоставляет прикладной интерфейс (API) для верификации благонадежности  
телефонного номера физического лица (ФЛ).  

Фактически, приложение является 
([HTTP](https://developer.mozilla.org/en-US/docs/Learn/Common_questions/What_is_a_web_server))
сервером, работающим в режиме "демона", осуществляющим взаимодействие с Клиентом и 
сервисом National Hunter.  

Разработано на языке программирования 
[Python 3.8](https://www.python.org/downloads/release/python-380/) 
и поставляется в виде сборки 
[Docker образа](https://docs.docker.com/engine/reference/commandline/images/).  

Исходной код приложения содержит:
* Реализацию [бизнес требований](https://wiki.ucb.local/pages/viewpage.action?pageId=37397227);
* Миграции базы данных;
* Техническую документацию.

## Миграции

Миграции являются системой контроля версий для базы данных. 
Они позволяют автоматизированно изменять структуру БД, поддерживая её в актуальном состоянии.  

Подробнее:
* [habr.com](https://habr.com/ru/post/121265/)

Для выполнения миграций используется утилита 
[Alembic](https://alembic.sqlalchemy.org/en/latest/index.html).  

# Развёртывание

Сервис поставляется в виде 
[Docker образа](https://docs.docker.com/engine/reference/commandline/images/), 
который заранее необходимо доставить на рабочую машину.

Общий процесс развертывания приложения:
1. Установить необходимое ПО (в т.ч. образ приложения);
2. Запустить миграции базы данных авторизации (Postgres);
3. Запустить сервер приложения с помощью Docker;

Возможно два варианта запуска.

## Автоматизированное развертывание

Для этого воспользуемся средствами 
[Docker Compose](https://docs.docker.com/compose/) (для разработки) и
[Docker Swarm](https://docs.docker.com/engine/swarm/) (для продакшена).  

Опишем `docker-compose.yml` файл.  

В качестве обязательных параметров окружения выступают:
* `AUTH_DB_URL` - dsn строка подключения к СУБД Авторизации (Postgres DB);
* `HUNTER_DB_URL` - dsn строка подключения к СУБД National Hunter (Oracle DB).

Опишем 2 сервиса:
1. `vertical_api` - приложение;
2. `vertical_migrations` - миграции;

Первый сервис запустит долгоживущий 
[Docker Container](https://www.docker.com/resources/what-container) 
с HTTP сервером.  

Второй сервис проведет миграции в СУБД Авторизации.  

Пример:

```yaml
version: "3.7"

services:

  vertical_api:
    image: vertical:latest
    container_name: vertical_api
    ports:
      - 8080:8080
    environment:
      - AUTH_DB_URL=...
      - HUNTER_DB_URL=...
    networks:
      - vertical_network

  vertical_migrations:
    image: vertical:latest
    container_name: vertical_migrations
    environment:
      - AUTH_DB_URL=...
    command: ["alembic", "upgrade", "head"]
    networks:
      - vertical_network
```

В этом примере второй сервис переопределяет команду запуска контейнера на `alembic upgrade head`. 
Эта команда запускает миграции в СУБД Авторизации и тем самым обновляет структуру БД.  

После проведения миграций контейнер остановится. Больше он не нужен и его можно удалить.  

Этот пример показывает, как можно запустить миграции автоматизированно в стеке сервисов. 
Альтернативным вариантом, является запуск сервиса приложения без сервиса миграций.

## Ручное развертывание

Для этого опишем стек из одного сервиса - сервиса приложения.  

```yaml
version: "3.7"

services:

  vertical_api:
    image: vertical:latest
    container_name: vertical_api
    ports:
      - 8080:8080
    environment:
      - AUTH_DB_URL=...
      - HUNTER_DB_URL=...
    depends_on:
      - vertical_migrations
    networks:
      - vertical_network
```

После запуска стека войдем в интерактивный режим контейнера `vertical_api` командой:

```bash
docker exec -it vertical_api bash
```

Проведем миграции командой:

```bash
alembic upgrade head
```

Этот способ является ручным и его не рекомендуется использовать на продакшене.

# Проверка работоспособности

Прежде всего стоит посмотреть логи приложения и миграций.

Возвращаясь к примерам выше, это можно сделать командами:

```bash
docker logs vertical_migrations
docker logs vertical_api
```

Логи миграций должны быть примерно следующими:

```bash
INFO [alembic.migration] Context impl PostgresqlImpl.
INFO [alembic.migration] Will assume transactional DDL.
INFO [alembic.migration] Run upgrade  -> 98529cf9ab14, Create pgcrypto extension.
INFO [alembic.migration] Run upgrade 98529cf9ab14 -> 9f02be65b5d3, Create clients table.
INFO [alembic.migration] Run upgrade 9f02be65b5d3 -> 5c821b099cf2, Create contracts table.
INFO [alembic.migration] Run upgrade 5c821b099cf2 -> c68c98b6a75e, Create requests table.
INFO [alembic.migration] Run upgrade c68c98b6a75e -> 5591d429b7e3, Create responses table.
INFO [alembic.migration] Run upgrade 5591d429b7e3 -> 7b7f7733db71, Create identifications table.
INFO [alembic.migration] Run upgrade 7b7f7733db71 -> be0f06ec00b4, Create contract for admin.
```

Логи приложения должны быть примерно следующими:

```bash
...
time="2020.04.21 07:25:45" level="INFO" logger="uvicorn.error" pid="23" request_id="-" message="Started server process [23]"
time="2020.04.21 07:25:45" level="INFO" logger="uvicorn.error" pid="23" request_id="-" message="Waiting for application startup."
time="2020.04.21 07:25:45" level="INFO" logger="uvicorn.error" pid="23" request_id="-" message="Application startup complete."
...
```

Для проверки работоспособности Сервиса с помощью HTTP запросов необходимо получить `TOKEN`.  

Для этого следует выполнить SQL запрос в СУБД Авторизации (Postgres):

```sql
    SELECT
        contracts.token
    FROM contracts
        JOIN clients USING (client_id)
    WHERE
        clients.name = 'admin'
    LIMIT 1
    ;
```

На экране увидим строку длиной 64 символа.  
Запомнием полученное значение.  

Теперь, когда знаем `TOKEN` и `HOST` развернутого Сервиса сделаем 2 запроса.

## Ping

Метод запроса: `GET`.  

URL адрес: `{HOST}/api/v1/ping`.  

Пример (curl):

```shell script
curl --location --request GET '{HOST}/ping' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer {TOKEN}'
```

Ожидаемый ответ: `HTTP 200 OK` со следующим содержимым:

```json
{
    "data": {},
    "message": "pong"
}
```

## Phone Reliability

Метод запроса: `POST`.  

URL адрес: `{HOST}/api/v1/reliability/phone`.  

Пример (curl):

```shell script
curl --location --request POST '127.0.0.1:8080/reliability/phone' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer {TOKEN}' \
--header 'Content-Type: application/json' \
--data-raw '{
	"number": "70000000000"
}'
```

Ожидаемый ответ: `HTTP 200 OK` со следующим содержимым:

```json
{
    "data": {
        "period": null,
        "status": false
    },
    "message": "OK"
}
```

После проведения HTTP запросов стоит еще раз посмотреть в логи приложения и убедиться, 
что нет никаких ошибок.
