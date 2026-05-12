# Current Benchmark Implementation Factual Summary

This document summarizes the current implementation state of the SQL vs NoSQL benchmarking platform based on the active project codebase.

Checked files:

- `backend/app/benchmarks.py`
- `backend/app/loaders.py`
- `backend/app/datasets.py`
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `frontend/src/app/page.tsx`
- `docker-compose.yml`

## 1. Current Benchmark Request Parameters

When the user runs a benchmark, the frontend sends a request to:

`POST /api/benchmarks/run`

The request body contains:

| Parameter | Status | Description |
|---|---|---|
| `dataset_id` | Used | Identifies the selected dataset metadata in backend memory. |
| `operation` | Used | Benchmark operation type. |
| `record_count` | Used | Number of records used in the benchmark. |
| `repetitions` | Used | Number of repeated benchmark runs. |

Supported `operation` values:

- `WRITE`
- `READ`
- `UPDATE`
- `DELETE`

Current frontend behavior:

- `dataset_id` is sent from the selected dataset.
- `operation` is selected by the user.
- `record_count` is not manually configured by the user.
- `record_count` is sent as the full selected dataset record count.
- `repetitions` is configured by the user.
- Frontend default `repetitions` value is `3`.
- Frontend input limits `repetitions` to minimum `1` and maximum `20`.

Current backend validation:

- `dataset_id`: required string.
- `operation`: required literal value, limited to `WRITE`, `READ`, `UPDATE`, `DELETE`.
- `record_count`: required integer, minimum `1`.
- `repetitions`: required integer, minimum `1`, maximum `20`.

Removed or absent parameters:

- `index_enabled` is removed.
- `selected_field` is removed.
- No active references to `selected_field` or `selectedField` were found in the current codebase.
- No active references to `index_enabled` or `indexEnabled` were found in the current frontend/backend source.

## 2. Current Benchmark Workflow

Current workflow when the user clicks **Run Benchmark**:

1. The frontend checks whether a dataset is selected.
2. The frontend checks whether the dataset was loaded into both databases and whether record counts match.
3. The frontend sends `dataset_id`, `operation`, `record_count`, and `repetitions` to the backend.
4. The backend validates the request with the `BenchmarkRunRequest` model.
5. The backend retrieves the dataset using `get_dataset(dataset_id)`.
6. The backend prepares normalized dataset records with sequential `record_index` values.
7. The backend validates `record_count` against the prepared dataset and against the loaded database source data.
8. The backend runs the PostgreSQL benchmark first.
9. The backend runs the MongoDB benchmark second.
10. Metrics are calculated for PostgreSQL and MongoDB using the same metric calculation function.
11. A combined benchmark result is created.
12. The result is stored in MongoDB in the `benchmark_results` collection.
13. The result is returned to the frontend.
14. The frontend displays the latest result and reloads previous benchmark results.

Temporary benchmark data preparation:

- PostgreSQL uses a temporary work table named `benchmark_work_records`.
- MongoDB uses a temporary work collection named `benchmark_work_records`.
- Temporary benchmark data is cleared before each repetition.
- PostgreSQL drops and recreates the work table before each repetition.
- MongoDB drops the work collection before each repetition.

Database preparation:

- Source dataset table in PostgreSQL: `benchmark_dataset_records`.
- Source dataset collection in MongoDB: `benchmark_dataset_records`.
- PostgreSQL benchmark work table is created from the source table schema.
- MongoDB benchmark work collection is created by inserting copied documents from the source collection.
- PostgreSQL work data includes a simple `benchmark_updated` boolean column for UPDATE benchmarks.
- MongoDB work data includes a `benchmark_updated` field for UPDATE benchmarks.

Same dataset and record count:

- Both databases are benchmarked using the loaded source dataset.
- Both databases receive the same `record_count`.
- The frontend currently sends the full selected dataset record count.
- The backend validates that the requested `record_count` does not exceed the loaded record count in each database.

Repetitions:

- Repetitions are implemented.
- For each repetition, temporary benchmark data is prepared again.
- One timed operation is executed per repetition.
- Each repetition produces one run time and one affected count.

Execution order:

1. PostgreSQL benchmark runs completely for all repetitions.
2. MongoDB benchmark runs completely for all repetitions.

Error handling:

- Missing dataset metadata returns `404`.
- Missing PostgreSQL source table returns `400`.
- Empty loaded data returns `400`.
- Requested `record_count` larger than loaded count returns `400`.
- PostgreSQL benchmark failures return `500`.
- MongoDB benchmark failures return `500`.
- Result storage failures return `500`.
- The frontend displays backend error messages in an error alert.

## 3. CRUD Operation Logic

### WRITE

PostgreSQL:

- Drops and recreates the work table.
- Adds the `benchmark_updated` boolean column outside timing.
- Uses the first `record_count` normalized records prepared by the backend application.
- Inserts records into `benchmark_work_records` with psycopg `executemany`.
- Timed operation is the application-driven insert and commit.

MongoDB:

- Drops the work collection.
- Uses the same first `record_count` normalized logical records prepared by the backend application.
- Creates documents with `_id` equal to `record_index`.
- Inserts documents into `benchmark_work_records` with `insert_many`.
- Timed operation is the application-driven insert.

Notes:

- WRITE is application-driven for both databases.
- Temporary work storage cleanup and record preparation happen before timing.
- No selected field is used.
- The operations are broadly equivalent as bulk insert operations.

### READ

PostgreSQL:

- Copies the first `record_count` rows into the work table before timing.
- Adds the `benchmark_updated` boolean column outside timing.
- Retrieves rows from the work table with `SELECT *`.
- Filter condition: `record_index <= record_count`.
- The returned rows are materialized with `fetchall`.

MongoDB:

- Copies the first `record_count` documents into the work collection before timing.
- Sets `benchmark_updated` to `false` in the copied work documents outside timing.
- Retrieves documents with `find`.
- Filter condition: `_id <= record_count`.
- The returned documents are materialized with `list(...)`.

Notes:

- PostgreSQL uses `record_index` as the filter.
- MongoDB uses `_id` as the filter because `_id` equals `record_index` in loaded and work documents.
- No selected field is used.
- The implementation measures materialized retrieval, not only count queries.

### UPDATE

PostgreSQL:

- Copies the first `record_count` rows into the work table before timing.
- Adds the `benchmark_updated` boolean column outside timing.
- Updates rows where `record_index <= record_count`.
- Sets the simple `benchmark_updated` column to `TRUE`.

MongoDB:

- Copies the first `record_count` documents into the work collection before timing.
- Sets `benchmark_updated` to `false` in the copied work documents outside timing.
- Updates documents where `_id <= record_count`.
- Sets the `benchmark_updated` field to `true`.

Notes:

- PostgreSQL uses `record_index` as the filter.
- MongoDB uses `_id` as the filter.
- No selected field is used.
- The operations are semantically closer than the previous JSONB update design because both update a simple benchmark flag.

### DELETE

PostgreSQL:

- Copies the first `record_count` rows into the work table before timing.
- Deletes rows where `record_index <= record_count`.

MongoDB:

- Copies the first `record_count` documents into the work collection before timing.
- Deletes documents where `_id <= record_count`.

Notes:

- PostgreSQL uses `record_index` as the filter.
- MongoDB uses `_id` as the filter because `_id` equals `record_index`.
- No selected field is used.
- The operations are equivalent as delete operations over the prepared work dataset.

## 4. Same-Condition and Fairness Rules

Implemented same-condition rules:

- The same uploaded or sample dataset is loaded into both PostgreSQL and MongoDB.
- The same `record_count` is used for both databases.
- The same `repetitions` value is used for both databases.
- The same `operation` value is used for both databases.
- The same metric calculation function is used for both databases.
- Both databases run in the same Docker Compose environment.
- Both databases use source storage named `benchmark_dataset_records`.
- Both databases use temporary benchmark storage named `benchmark_work_records`.
- Temporary benchmark storage is reset before each repetition.
- WRITE uses the same first `record_count` application-prepared logical records for both databases.
- READ materializes matching rows/documents for both databases instead of using count-only reads.
- UPDATE modifies a simple benchmark update flag in both databases.

Docker Compose environment:

- Backend service: FastAPI application.
- Frontend service: Next.js application.
- PostgreSQL service: `postgres:16-alpine`.
- MongoDB service: `mongo:7`.
- PostgreSQL data is stored in the `postgres_data` Docker volume.
- MongoDB data is stored in the `mongodb_data` Docker volume.

Limitations that may affect fairness:

- PostgreSQL benchmarks run before MongoDB benchmarks.
- Benchmark repetitions are not interleaved between databases.
- No explicit cache clearing is implemented.
- No warm-up phase is implemented.
- No Docker CPU or memory limits are configured.
- PostgreSQL has `record_index` as a primary key.
- MongoDB uses `_id` equal to `record_index`; `_id` is indexed by MongoDB.
- PostgreSQL and MongoDB store records in different physical structures.
- PostgreSQL and MongoDB drivers have different client-side batching behavior.
- Execution order is still PostgreSQL first and MongoDB second.
- The backend checks loaded record counts but does not verify that the currently loaded database contents still correspond to the requested `dataset_id`.

## 5. Evaluation Metrics Currently Implemented

The same metrics are calculated for PostgreSQL and MongoDB using `calculate_metrics`.

| Metric | Implemented | Meaning | Calculation | Basis |
|---|---:|---|---|---|
| `total_time_ms` | Yes | Total measured execution time across repetitions. | Sum of all `run_times_ms`. | Repeated runs |
| `average_latency_ms` | Yes | Average time per affected/read record. | `total_time_ms / sum(affected_counts)`. | Aggregate repeated runs |
| `throughput_ops_sec` | Yes | Operations processed per second. | `sum(affected_counts) / (total_time_ms / 1000)`. | Aggregate repeated runs |
| `min_time_ms` | Yes | Fastest repetition time. | Minimum value in `run_times_ms`. | Repeated runs |
| `max_time_ms` | Yes | Slowest repetition time. | Maximum value in `run_times_ms`. | Repeated runs |
| `std_dev_ms` | Yes | Variation between repetition times. | Population standard deviation of `run_times_ms`. | Repeated runs |
| `operation_count` | Yes | Total number of affected/read records. | Sum of `affected_counts`. | Aggregate repeated runs |
| p95 latency | No | Not implemented. | Not implemented. | Not implemented |
| success rate | No | Not implemented as a metric. | Not implemented. | Not implemented |
| CPU usage | No | Not implemented. | Not implemented. | Not implemented |
| memory/RAM usage | No | Not implemented. | Not implemented. | Not implemented |

Additional note:

- Each database result includes an `ok` boolean, but this is not calculated as a success-rate metric.

## 6. Result Output and Storage

Benchmark results are returned to the frontend and stored in MongoDB using the same structure.

Result storage:

- Storage database: MongoDB.
- Storage collection: `benchmark_results`.
- Storage behavior: `replace_one` with `upsert=True` using `benchmark_id`.

Top-level result fields:

- `benchmark_id`
- `created_at`
- `dataset_id`
- `dataset_name`
- `operation`
- `record_count`
- `repetitions`
- `postgresql`
- `mongodb`

Per-database result fields:

- `ok`
- `target_name`
- `run_times_ms`
- `affected_counts`
- `metrics`
- `message`

Per-database metric fields:

- `total_time_ms`
- `average_latency_ms`
- `throughput_ops_sec`
- `min_time_ms`
- `max_time_ms`
- `std_dev_ms`
- `operation_count`

Previous benchmark results:

- Previous results are supported.
- `GET /api/benchmarks` returns stored benchmark results.
- `GET /api/benchmarks/{benchmark_id}` returns one benchmark result.
- Results are sorted by `created_at` descending when listed.
- PostgreSQL and MongoDB results are stored side by side in each benchmark result document.

## 7. Frontend Result Display

After benchmark execution, the frontend displays:

- Benchmark operation.
- Benchmark ID.
- Record count.
- Repetition count.
- MongoDB result card.
- PostgreSQL result card.
- Per-database metric values.
- Per-repetition run times.
- Metric comparison table.
- Charts.
- Previous benchmark results table.

PostgreSQL and MongoDB result cards:

- Implemented.
- MongoDB is displayed as NoSQL.
- PostgreSQL is displayed as SQL.
- MongoDB is shown on the left.
- PostgreSQL is shown on the right.

Comparison table:

- Implemented.
- Includes:
  - total execution time
  - average latency
  - throughput
  - minimum time
  - maximum time
  - standard deviation
- Includes a "Faster" column.

Charts:

- Implemented.
- Total execution time bar chart.
- Throughput bar chart.
- Repeated runs line chart.

Previous results:

- Implemented.
- The frontend loads previous results from `GET /api/benchmarks`.
- The table displays up to 10 latest results.
- Displayed fields include benchmark ID, dataset name, operation, MongoDB total time, PostgreSQL total time, and throughput leader.

Loading and error states:

- Health loading state is implemented.
- Dataset upload/loading states are implemented.
- Benchmark running state is implemented.
- Previous results loading state is implemented.
- Dataset, benchmark, and previous result error messages are displayed.

## 8. Scope Notes

Removed:

- `selected_field`
- `index_enabled`
- Index option in the benchmark UI

Not implemented:

- p95 latency
- CPU monitoring
- RAM/memory monitoring
- Concurrent workload testing
- Cloud or distributed testing
- Export as CSV
- Export as PDF
- Authentication
- Multi-user support
- Warm-up runs
- Explicit cache clearing
- Explicit Docker resource limiting

Partially related but not full implementations:

- Success status exists as an `ok` boolean per database result.
- Success rate as a calculated percentage metric is not implemented.
- Previous result storage exists, but there is no user account separation.
