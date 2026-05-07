from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
from time import perf_counter
from typing import Literal
from uuid import uuid4

import psycopg
from fastapi import HTTPException
from psycopg import sql
from psycopg.rows import dict_row
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError
from pydantic import BaseModel, Field

from app.config import settings
from app.datasets import get_dataset
from app.loaders import MONGO_COLLECTION_NAME, POSTGRES_TABLE_NAME


POSTGRES_WORK_TABLE_NAME = "benchmark_work_records"
MONGO_WORK_COLLECTION_NAME = "benchmark_work_records"
MONGO_RESULT_COLLECTION_NAME = "benchmark_results"

BenchmarkOperation = Literal["WRITE", "READ", "UPDATE", "DELETE"]


class BenchmarkRunRequest(BaseModel):
    dataset_id: str
    operation: BenchmarkOperation
    record_count: int = Field(ge=1)
    repetitions: int = Field(ge=1, le=20)


class BenchmarkMetrics(BaseModel):
    total_time_ms: float
    average_latency_ms: float
    throughput_ops_sec: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    operation_count: int


class BenchmarkDatabaseResult(BaseModel):
    ok: bool
    target_name: str
    run_times_ms: list[float]
    affected_counts: list[int]
    metrics: BenchmarkMetrics
    message: str


class BenchmarkRunResult(BaseModel):
    benchmark_id: str
    created_at: str
    dataset_id: str
    dataset_name: str
    operation: BenchmarkOperation
    record_count: int
    repetitions: int
    postgresql: BenchmarkDatabaseResult
    mongodb: BenchmarkDatabaseResult


def run_benchmark(request: BenchmarkRunRequest) -> BenchmarkRunResult:
    dataset = get_dataset(request.dataset_id)

    postgresql = run_postgres_benchmark(request)
    mongodb = run_mongodb_benchmark(request)

    result = BenchmarkRunResult(
        benchmark_id=f"bench_{uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        dataset_id=dataset.metadata.dataset_id,
        dataset_name=dataset.metadata.dataset_name,
        operation=request.operation,
        record_count=request.record_count,
        repetitions=request.repetitions,
        postgresql=postgresql,
        mongodb=mongodb,
    )

    store_benchmark_result(result)
    return result


def list_benchmark_results() -> list[BenchmarkRunResult]:
    client: MongoClient | None = None

    try:
        client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=10000)
        database = client.get_default_database(default="benchmark")
        collection = database[MONGO_RESULT_COLLECTION_NAME]
        documents = collection.find({}, {"_id": 0}).sort("created_at", -1)
        return [BenchmarkRunResult(**document) for document in documents]
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail=f"Benchmark results could not be loaded: {exc}") from exc
    finally:
        if client is not None:
            client.close()


def get_benchmark_result(benchmark_id: str) -> BenchmarkRunResult:
    client: MongoClient | None = None

    try:
        client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=10000)
        database = client.get_default_database(default="benchmark")
        collection = database[MONGO_RESULT_COLLECTION_NAME]
        document = collection.find_one({"benchmark_id": benchmark_id}, {"_id": 0})
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail=f"Benchmark result could not be loaded: {exc}") from exc
    finally:
        if client is not None:
            client.close()

    if document is None:
        raise HTTPException(status_code=404, detail=f"Benchmark result '{benchmark_id}' was not found.")

    return BenchmarkRunResult(**document)


def store_benchmark_result(result: BenchmarkRunResult) -> None:
    client: MongoClient | None = None

    try:
        client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=10000)
        database = client.get_default_database(default="benchmark")
        collection = database[MONGO_RESULT_COLLECTION_NAME]
        collection.replace_one(
            {"benchmark_id": result.benchmark_id},
            result.model_dump(mode="json"),
            upsert=True,
        )
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail=f"Benchmark result could not be stored: {exc}") from exc
    finally:
        if client is not None:
            client.close()


def calculate_metrics(
    run_times_ms: list[float],
    affected_counts: list[int],
) -> BenchmarkMetrics:
    total_time_ms = sum(run_times_ms)
    operation_count = sum(affected_counts)
    average_latency_ms = total_time_ms / operation_count if operation_count > 0 else 0
    throughput_ops_sec = operation_count / (total_time_ms / 1000) if total_time_ms > 0 else 0

    if run_times_ms:
        min_time_ms = min(run_times_ms)
        max_time_ms = max(run_times_ms)
        mean_time_ms = total_time_ms / len(run_times_ms)
        std_dev_ms = sqrt(
            sum((run_time_ms - mean_time_ms) ** 2 for run_time_ms in run_times_ms)
            / len(run_times_ms)
        )
    else:
        min_time_ms = 0
        max_time_ms = 0
        std_dev_ms = 0

    return BenchmarkMetrics(
        total_time_ms=round(total_time_ms, 4),
        average_latency_ms=round(average_latency_ms, 6),
        throughput_ops_sec=round(throughput_ops_sec, 4),
        min_time_ms=round(min_time_ms, 4),
        max_time_ms=round(max_time_ms, 4),
        std_dev_ms=round(std_dev_ms, 4),
        operation_count=operation_count,
    )


def run_postgres_benchmark(request: BenchmarkRunRequest) -> BenchmarkDatabaseResult:
    run_times_ms: list[float] = []
    affected_counts: list[int] = []

    try:
        with psycopg.connect(settings.database_url, connect_timeout=10) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                source_count = get_postgres_source_count(cursor)
                validate_record_count(request.record_count, source_count, "PostgreSQL")

                for _ in range(request.repetitions):
                    if request.operation == "WRITE":
                        setup_postgres_work_table(cursor, copy_records=False, record_count=request.record_count)
                        connection.commit()
                        elapsed_ms, affected = time_postgres_write(cursor, connection, request.record_count)
                    else:
                        setup_postgres_work_table(cursor, copy_records=True, record_count=request.record_count)
                        connection.commit()
                        elapsed_ms, affected = time_postgres_operation(
                            cursor,
                            connection,
                            request.operation,
                            request.record_count,
                        )

                    run_times_ms.append(elapsed_ms)
                    affected_counts.append(affected)

        return BenchmarkDatabaseResult(
            ok=True,
            target_name=POSTGRES_WORK_TABLE_NAME,
            run_times_ms=run_times_ms,
            affected_counts=affected_counts,
            metrics=calculate_metrics(run_times_ms, affected_counts),
            message="PostgreSQL benchmark completed.",
        )
    except psycopg.errors.UndefinedTable as exc:
        raise HTTPException(
            status_code=400,
            detail="PostgreSQL dataset table was not found. Load a dataset before running benchmarks.",
        ) from exc
    except psycopg.Error as exc:
        raise HTTPException(status_code=500, detail=f"PostgreSQL benchmark failed: {exc}") from exc


def get_postgres_source_count(cursor: psycopg.Cursor) -> int:
    cursor.execute(
        sql.SQL("SELECT COUNT(*) AS count FROM {}").format(sql.Identifier(POSTGRES_TABLE_NAME))
    )
    return int(cursor.fetchone()["count"])


def setup_postgres_work_table(
    cursor: psycopg.Cursor,
    *,
    copy_records: bool,
    record_count: int,
) -> None:
    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(POSTGRES_WORK_TABLE_NAME)))
    cursor.execute(
        sql.SQL("CREATE TABLE {} (LIKE {} INCLUDING ALL)").format(
            sql.Identifier(POSTGRES_WORK_TABLE_NAME),
            sql.Identifier(POSTGRES_TABLE_NAME),
        )
    )

    if copy_records:
        cursor.execute(
            sql.SQL("INSERT INTO {} SELECT * FROM {} ORDER BY record_index LIMIT %s").format(
                sql.Identifier(POSTGRES_WORK_TABLE_NAME),
                sql.Identifier(POSTGRES_TABLE_NAME),
            ),
            (record_count,),
        )


def time_postgres_write(
    cursor: psycopg.Cursor,
    connection: psycopg.Connection,
    record_count: int,
) -> tuple[float, int]:
    started = perf_counter()
    cursor.execute(
        sql.SQL("INSERT INTO {} SELECT * FROM {} ORDER BY record_index LIMIT %s").format(
            sql.Identifier(POSTGRES_WORK_TABLE_NAME),
            sql.Identifier(POSTGRES_TABLE_NAME),
        ),
        (record_count,),
    )
    affected = cursor.rowcount
    connection.commit()
    return elapsed_ms(started), affected


def time_postgres_operation(
    cursor: psycopg.Cursor,
    connection: psycopg.Connection,
    operation: BenchmarkOperation,
    record_count: int,
) -> tuple[float, int]:
    if operation == "READ":
        started = perf_counter()
        cursor.execute(
            sql.SQL("SELECT COUNT(*) AS count FROM {} WHERE record_index <= %s").format(
                sql.Identifier(POSTGRES_WORK_TABLE_NAME)
            ),
            (record_count,),
        )
        affected = int(cursor.fetchone()["count"])
        return elapsed_ms(started), affected

    if operation == "UPDATE":
        started = perf_counter()
        cursor.execute(
            sql.SQL("UPDATE {} SET record_data = record_data || %s::jsonb WHERE record_index <= %s").format(
                sql.Identifier(POSTGRES_WORK_TABLE_NAME)
            ),
            ('{"benchmark_updated": true}', record_count),
        )
        affected = cursor.rowcount
        connection.commit()
        return elapsed_ms(started), affected

    if operation == "DELETE":
        started = perf_counter()
        cursor.execute(
            sql.SQL("DELETE FROM {} WHERE record_index <= %s").format(
                sql.Identifier(POSTGRES_WORK_TABLE_NAME)
            ),
            (record_count,),
        )
        affected = cursor.rowcount
        connection.commit()
        return elapsed_ms(started), affected

    raise HTTPException(status_code=400, detail=f"Unsupported benchmark operation: {operation}.")


def run_mongodb_benchmark(request: BenchmarkRunRequest) -> BenchmarkDatabaseResult:
    client: MongoClient | None = None
    run_times_ms: list[float] = []
    affected_counts: list[int] = []

    try:
        client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=10000)
        database = client.get_default_database(default="benchmark")
        source = database[MONGO_COLLECTION_NAME]
        work = database[MONGO_WORK_COLLECTION_NAME]
        source_count = source.count_documents({})
        validate_record_count(request.record_count, source_count, "MongoDB")

        for _ in range(request.repetitions):
            if request.operation == "WRITE":
                docs = list(source.find({}, sort=[("record_index", ASCENDING)], limit=request.record_count))
                work.drop()
                elapsed_ms, affected = time_mongodb_write(work, docs)
            else:
                setup_mongodb_work_collection(source, work, request.record_count)
                elapsed_ms, affected = time_mongodb_operation(
                    work,
                    request.operation,
                    request.record_count,
                )

            run_times_ms.append(elapsed_ms)
            affected_counts.append(affected)

        return BenchmarkDatabaseResult(
            ok=True,
            target_name=MONGO_WORK_COLLECTION_NAME,
            run_times_ms=run_times_ms,
            affected_counts=affected_counts,
            metrics=calculate_metrics(run_times_ms, affected_counts),
            message="MongoDB benchmark completed.",
        )
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail=f"MongoDB benchmark failed: {exc}") from exc
    finally:
        if client is not None:
            client.close()


def setup_mongodb_work_collection(source, work, record_count: int) -> None:
    work.drop()
    docs = list(source.find({}, sort=[("record_index", ASCENDING)], limit=record_count))
    if docs:
        work.insert_many(docs, ordered=False)


def time_mongodb_write(work, docs: list[dict]) -> tuple[float, int]:
    started = perf_counter()
    if docs:
        result = work.insert_many(docs, ordered=False)
        affected = len(result.inserted_ids)
    else:
        affected = 0
    return elapsed_ms(started), affected


def time_mongodb_operation(
    work,
    operation: BenchmarkOperation,
    record_count: int,
) -> tuple[float, int]:
    filter_query = {"record_index": {"$lte": record_count}}

    if operation == "READ":
        started = perf_counter()
        affected = work.count_documents(filter_query)
        return elapsed_ms(started), affected

    if operation == "UPDATE":
        started = perf_counter()
        result = work.update_many(filter_query, {"$set": {"benchmark_updated": True}})
        return elapsed_ms(started), result.modified_count

    if operation == "DELETE":
        started = perf_counter()
        result = work.delete_many(filter_query)
        return elapsed_ms(started), result.deleted_count

    raise HTTPException(status_code=400, detail=f"Unsupported benchmark operation: {operation}.")


def validate_record_count(record_count: int, available_count: int, database_name: str) -> None:
    if available_count <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"{database_name} does not contain loaded benchmark data.",
        )

    if record_count > available_count:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Record count {record_count} exceeds loaded {database_name} "
                f"record count {available_count}."
            ),
        )


def elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 4)
