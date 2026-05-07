from dataclasses import dataclass

import psycopg
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import settings


@dataclass(frozen=True)
class ConnectionStatus:
    service: str
    ok: bool
    message: str


def check_postgres() -> ConnectionStatus:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return ConnectionStatus("postgresql", True, "PostgreSQL connection is healthy.")
    except psycopg.Error as exc:
        return ConnectionStatus("postgresql", False, f"PostgreSQL connection failed: {exc}")


def check_mongodb() -> ConnectionStatus:
    client: MongoClient | None = None

    try:
        client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return ConnectionStatus("mongodb", True, "MongoDB connection is healthy.")
    except PyMongoError as exc:
        return ConnectionStatus("mongodb", False, f"MongoDB connection failed: {exc}")
    finally:
        if client is not None:
            client.close()
