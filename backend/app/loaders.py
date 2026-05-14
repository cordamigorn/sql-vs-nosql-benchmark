from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import psycopg
from fastapi import HTTPException
from psycopg import sql
from psycopg.rows import dict_row
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pydantic import BaseModel

from app.config import settings
from app.datasets import Dataset, Record


POSTGRES_TABLE_NAME = "benchmark_dataset_records"
MONGO_COLLECTION_NAME = "benchmark_dataset_records"


class DatasetLoadRequest(BaseModel):
    dataset_id: str


class DatabaseLoadResult(BaseModel):
    ok: bool
    record_count: int
    target_name: str
    message: str


class DatasetLoadResult(BaseModel):
    dataset_id: str
    dataset_name: str
    expected_record_count: int
    postgresql: DatabaseLoadResult
    mongodb: DatabaseLoadResult
    counts_match: bool


@dataclass(frozen=True)
class PreparedDataset:
    fields: list[str]
    column_map: dict[str, str]
    records: list[Record]


def load_dataset_to_databases(dataset: Dataset) -> DatasetLoadResult:
    prepared = prepare_dataset(dataset)

    postgres_result = load_postgres(prepared)
    mongodb_result = load_mongodb(prepared)
    counts_match = (
        postgres_result.ok
        and mongodb_result.ok
        and postgres_result.record_count == dataset.metadata.record_count
        and mongodb_result.record_count == dataset.metadata.record_count
        and postgres_result.record_count == mongodb_result.record_count
    )

    return DatasetLoadResult(
        dataset_id=dataset.metadata.dataset_id,
        dataset_name=dataset.metadata.dataset_name,
        expected_record_count=dataset.metadata.record_count,
        postgresql=postgres_result,
        mongodb=mongodb_result,
        counts_match=counts_match,
    )


def prepare_dataset(dataset: Dataset) -> PreparedDataset:
    if not dataset.records:
        raise HTTPException(status_code=400, detail="Dataset does not contain any records to load.")

    column_map = build_column_map(dataset.metadata.fields)
    normalized_records: list[Record] = []

    for index, record in enumerate(dataset.records, start=1):
        normalized_records.append(
            {
                "record_index": index,
                **{field: record.get(field) for field in dataset.metadata.fields},
            }
        )

    return PreparedDataset(
        fields=dataset.metadata.fields,
        column_map=column_map,
        records=normalized_records,
    )


def build_column_map(fields: list[str]) -> dict[str, str]:
    column_map: dict[str, str] = {}
    used: set[str] = {"record_index"}

    for field in fields:
        base = re.sub(r"[^a-zA-Z0-9_]+", "_", field.strip().lower()).strip("_")
        if not base:
            base = "field"
        if base[0].isdigit():
            base = f"field_{base}"

        column = base
        suffix = 2
        while column in used:
            column = f"{base}_{suffix}"
            suffix += 1

        used.add(column)
        column_map[field] = column

    return column_map


def load_postgres(prepared: PreparedDataset) -> DatabaseLoadResult:
    columns = list(prepared.column_map.values())

    try:
        with psycopg.connect(settings.database_url, connect_timeout=10) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                recreate_postgres_table(cursor, columns)
                insert_postgres_records(cursor, prepared)
                cursor.execute(
                    sql.SQL("SELECT COUNT(*) AS count FROM {}").format(
                        sql.Identifier(POSTGRES_TABLE_NAME)
                    )
                )
                count = int(cursor.fetchone()["count"])

            connection.commit()

        return DatabaseLoadResult(
            ok=True,
            record_count=count,
            target_name=POSTGRES_TABLE_NAME,
            message="Dataset loaded into PostgreSQL.",
        )
    except psycopg.Error as exc:
        raise HTTPException(status_code=500, detail=f"PostgreSQL data loading failed: {exc}") from exc


def recreate_postgres_table(cursor: psycopg.Cursor[Any], columns: list[str]) -> None:
    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(POSTGRES_TABLE_NAME)))

    column_definitions = [
        sql.SQL("{} TEXT").format(sql.Identifier(column)) for column in columns
    ]
    create_query = sql.SQL(
        "CREATE TABLE {} (record_index BIGINT PRIMARY KEY, {})"
    ).format(
        sql.Identifier(POSTGRES_TABLE_NAME),
        sql.SQL(", ").join(column_definitions),
    )
    cursor.execute(create_query)


def insert_postgres_records(cursor: psycopg.Cursor[Any], prepared: PreparedDataset) -> None:
    columns = list(prepared.column_map.values())
    insert_columns = ["record_index", *columns]
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in insert_columns)
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(POSTGRES_TABLE_NAME),
        sql.SQL(", ").join(sql.Identifier(column) for column in insert_columns),
        placeholders,
    )

    values: list[tuple[Any, ...]] = []
    for record in prepared.records:
        source_record = {field: record[field] for field in prepared.fields}
        values.append(
            (
                record["record_index"],
                *(None if source_record[field] is None else str(source_record[field]) for field in prepared.fields),
            )
        )

    cursor.executemany(query, values)


def load_mongodb(prepared: PreparedDataset) -> DatabaseLoadResult:
    client: MongoClient | None = None

    try:
        client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=10000)
        database = client.get_default_database(default="benchmark")
        collection = database[MONGO_COLLECTION_NAME]
        collection.drop()

        if prepared.records:
            collection.insert_many(
                [
                    {
                        "_id": record["record_index"],
                        "record_index": record["record_index"],
                        **{field: record[field] for field in prepared.fields},
                    }
                    for record in prepared.records
                ],
                ordered=False,
            )

        count = collection.count_documents({})
        return DatabaseLoadResult(
            ok=True,
            record_count=count,
            target_name=MONGO_COLLECTION_NAME,
            message="Dataset loaded into MongoDB.",
        )
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail=f"MongoDB data loading failed: {exc}") from exc
    finally:
        if client is not None:
            client.close()
