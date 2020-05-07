import uvicorn
from environs import Env

import vertical

env = Env()

config = {
    "auth_service": {
        "pool": {
            "dsn": env.str("AUTH_DB_URL"),
            "min_size": env.int("AUTH_DB_MIN_SIZE", 0),
            "max_size": env.int("AUTH_DB_MAX_SIZE", 5),
            "max_queries": env.int("AUTH_DB_MAX_QUERIES", 1000),
            "timeout": env.float("AUTH_DB_TIMEOUT", 10),
            "command_timeout": env.float("AUTH_DB_COMMAND_TIMEOUT", 5),
        },
        "logger": {
            "name": "audit",
        },
    },
    "hunter_service": {
        "bind": {
            "name_or_url": env.str("HUNTER_DB_URL"),
            "echo": env.bool("HUNTER_DB_ECHO", False),
            "echo_pool": env.bool("HUNTER_DB_ECHO_POOL", False),
            "encoding": env.str("HUNTER_DB_ENCODING", "utf-8"),
            "max_overflow": env.int("HUNTER_DB_MAX_OVERFLOW", 5),
            "pool_pre_ping": env.bool("HUNTER_DB_POOL_PRE_PING", False),
            "pool_size": env.int("HUNTER_DB_POOL_SIZE", 5),
            "pool_recycle": env.int("HUNTER_DB_POOL_RECYCLE", 3600),
            "pool_timeout": env.int("HUNTER_DB_POOL_TIMEOUT", 10),
        },
        "days": env.int("HUNTER_DELTA_DAYS", 180),
        "schema": env.str("HUNTER_DB_SCHEMA", "yavert"),
        "table": env.str("HUNTER_DB_TABLE", "hundata"),
        "timeout": env.float("HUNTER_QUERY_TIMEOUT", 10),
        "logger": {
            "name": "hunter",
        },
    },
}

app = vertical.create_app(config)

if __name__ == "__main__":
    host = env.str("HOST", "127.0.0.1")
    port = env.str("PORT", 8080)

    uvicorn.run(app, host=host, port=port)
