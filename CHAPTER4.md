# Chapter 4 Implementation Notes

This document contains factual implementation details based on the current project codebase. It is not written as final thesis prose.

Checked files:

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/datasets.py`
- `backend/app/loaders.py`
- `backend/app/benchmarks.py`
- `frontend/src/app/page.tsx`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/globals.css`
- `backend/requirements.txt`
- `frontend/package.json`
- `docker-compose.yml`

## 1. Backend Implementation

### Backend framework

- The backend uses **FastAPI**.
- The ASGI server dependency is **Uvicorn**.
- Data validation and response schemas use **Pydantic** models.
- PostgreSQL access uses **psycopg 3**.
- MongoDB access uses **PyMongo**.
- File upload support uses `python-multipart`.

### Main backend files and roles

| File | Role |
|---|---|
| `backend/app/main.py` | Defines the FastAPI application, CORS middleware, and API endpoints. |
| `backend/app/config.py` | Reads application settings from environment variables. |
| `backend/app/database.py` | Implements PostgreSQL and MongoDB health checks. |
| `backend/app/datasets.py` | Handles dataset upload parsing, sample dataset discovery, validation, and in-memory dataset storage. |
| `backend/app/loaders.py` | Loads validated datasets into PostgreSQL and MongoDB. |
| `backend/app/benchmarks.py` | Implements benchmark request models, benchmark execution, metric calculation, result storage, and previous result retrieval. |
| `backend/app/__init__.py` | Package marker file. |

### Implemented API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Basic backend health endpoint. |
| `GET` | `/` | Root endpoint returning service metadata and useful endpoint paths. |
| `GET` | `/api/health` | API-prefixed basic health endpoint. |
| `GET` | `/api/health/databases` | Checks PostgreSQL and MongoDB connectivity. |
| `POST` | `/api/datasets/upload` | Uploads and validates a CSV or JSON dataset. |
| `GET` | `/api/datasets/samples` | Lists available built-in sample datasets. |
| `POST` | `/api/datasets/sample` | Loads a selected built-in sample dataset into backend memory. |
| `POST` | `/api/datasets/load` | Loads the selected dataset into PostgreSQL and MongoDB. |
| `POST` | `/api/benchmarks/run` | Runs a benchmark operation on PostgreSQL and MongoDB. |
| `GET` | `/api/benchmarks` | Returns previous benchmark results. |
| `GET` | `/api/benchmarks/{benchmark_id}` | Returns one stored benchmark result by ID. |

### Dataset upload endpoint logic

Endpoint: `POST /api/datasets/upload`

- Receives an uploaded file using FastAPI `UploadFile`.
- Reads the uploaded file content.
- Rejects empty files.
- Decodes file content as UTF-8 with BOM support through `utf-8-sig`.
- Supports only `.csv` and `.json` extensions.
- Routes CSV files to `parse_csv_dataset`.
- Routes JSON files to `parse_json_dataset`.
- Stores validated dataset records in backend process memory.
- Returns generated dataset metadata to the frontend.

### Sample dataset endpoint logic

Implemented sample dataset endpoints:

- `GET /api/datasets/samples`
- `POST /api/datasets/sample`

Sample dataset list behavior:

- Scans the directory configured by `SAMPLE_DATASET_DIR`.
- Accepts `.csv` and `.json` files.
- Reads each sample file to extract fields and record count.
- Generates a `sample_id` from file stem and file type.
- Sorts options by record count, file type, and dataset name.
- Uses `lru_cache(maxsize=1)` for sample dataset scanning.

Sample dataset selection behavior:

- If no request body is provided, the default sample ID is `sample_orders_1k_csv`.
- If a `sample_id` is provided, the backend checks whether it exists.
- The selected sample file is read and validated using the same CSV or JSON parsing logic as uploaded files.
- The selected sample dataset is stored in backend memory.
- The returned metadata has `source` set to `sample`.

### Dataset validation logic for CSV

Implemented in `parse_csv_dataset`.

CSV validation rules:

- File must contain a header row.
- Header fields are stripped of surrounding whitespace.
- Header must define at least one field.
- Empty field names are rejected.
- Duplicate field names are rejected.
- Empty data rows are skipped.
- Each non-empty row must have the same number of columns as the header.
- Dataset must include at least one data row.
- Cell values are stripped of surrounding whitespace.
- Parsed records are stored as dictionaries keyed by header field name.

### Dataset validation logic for JSON

Implemented in `parse_json_dataset`.

JSON validation rules:

- File must contain valid JSON.
- Top-level JSON value must be an array.
- Array must not be empty.
- First array item must be an object.
- Field names are taken from the first object.
- Field list must define at least one field.
- Empty field names are rejected.
- Duplicate field names are rejected.
- Every item must be an object.
- Every item must use exactly the same field set as the first object.
- Nested objects and arrays are rejected.
- Parsed records are stored as dictionaries keyed by JSON field name.

### Dataset metadata fields generated

Dataset metadata model: `DatasetMetadata`

Generated fields:

- `dataset_id`
- `dataset_name`
- `record_count`
- `fields`
- `source`
- `file_type`

Current dataset storage:

- Datasets are stored in an in-memory dictionary named `_datasets`.
- The key is `dataset_id`.
- This storage is process-local and not persistent across backend restarts.

### PostgreSQL connection logic

Configuration:

- PostgreSQL connection string is read from `DATABASE_URL`.
- Default local value: `postgresql://benchmark:benchmark@localhost:5432/benchmark`.
- Docker Compose value: `postgresql://benchmark:benchmark@postgres:5432/benchmark`.

Health check:

- Implemented in `check_postgres`.
- Opens a connection with `connect_timeout=5`.
- Executes `SELECT 1`.
- Returns a `ConnectionStatus` object with `service`, `ok`, and `message`.

Operational usage:

- Dataset loading and benchmark execution open PostgreSQL connections through `psycopg.connect`.
- SQL identifiers are built using `psycopg.sql.Identifier`.
- Query results that need dictionary access use `dict_row`.

### MongoDB connection logic

Configuration:

- MongoDB URL is read from `MONGO_URL`.
- Default local value: `mongodb://localhost:27017/benchmark`.
- Docker Compose value: `mongodb://mongodb:27017/benchmark`.

Health check:

- Implemented in `check_mongodb`.
- Creates a `MongoClient`.
- Executes `client.admin.command("ping")`.
- Returns a `ConnectionStatus` object with `service`, `ok`, and `message`.
- Closes the client in a `finally` block.

Operational usage:

- Dataset loading, benchmark execution, result storage, and previous result retrieval use `MongoClient`.
- The default database name is resolved with `get_default_database(default="benchmark")`.

### Data loading logic into PostgreSQL and MongoDB

Implemented in `backend/app/loaders.py`.

Common preparation:

- `prepare_dataset` rejects empty datasets.
- Adds a sequential `record_index` field starting from `1`.
- Builds a PostgreSQL-safe column map from dataset field names.
- Preserves the original dataset field list.

PostgreSQL loading:

- Target table: `benchmark_dataset_records`.
- Existing table is dropped.
- New table is created with:
  - `record_index BIGINT PRIMARY KEY`
  - one `TEXT` column per dataset field
  - `record_data JSONB NOT NULL`
- Records are inserted with `executemany`.
- Original record content is also stored in `record_data` as JSONB.
- A count query verifies the inserted row count.

MongoDB loading:

- Target collection: `benchmark_dataset_records`.
- Existing collection is dropped.
- Records are inserted with:
  - `_id` equal to `record_index`
  - `record_index`
  - original dataset fields
- A count query verifies inserted document count.

Load result:

- The backend returns one PostgreSQL load result and one MongoDB load result.
- It also returns `counts_match`.
- `counts_match` is true only when both loads succeed and both databases contain the expected dataset record count.

### Error handling approach

Backend error handling uses FastAPI `HTTPException`.

Examples:

- Invalid upload file: `400`.
- Unsupported file type: `400`.
- Invalid CSV or JSON structure: `400`.
- Missing dataset ID: `404`.
- Missing sample dataset: `404`.
- PostgreSQL dataset table missing before benchmark: `400`.
- Requested benchmark `record_count` larger than loaded database count: `400`.
- PostgreSQL loading or benchmark database errors: `500`.
- MongoDB loading, benchmark, result storage, or result retrieval errors: `500`.

Frontend-facing error format:

- FastAPI returns errors with a `detail` field.
- The frontend reads `detail` when available and displays it as an alert.

### Response format style returned to the frontend

- Backend responses are JSON.
- Response schemas are defined with Pydantic models.
- Field names use snake_case.
- Main response types include:
  - `DatasetMetadata`
  - `SampleDatasetOption`
  - `DatasetLoadResult`
  - `BenchmarkRunResult`
  - database health status objects

## 2. Frontend Implementation

### Frontend framework and libraries

- The frontend uses **Next.js**.
- The UI is implemented with **React**.
- The code is written in **TypeScript**.
- Styling is implemented with CSS in `frontend/src/app/globals.css`.
- No external charting library is used.
- Charts are implemented with custom HTML/CSS and SVG.

Frontend package versions from `package.json`:

- `next`: `^16.2.4`
- `react`: `19.2.4`
- `react-dom`: `19.2.4`
- `typescript`: `5.9.3`

### Main frontend files and roles

| File | Role |
|---|---|
| `frontend/src/app/page.tsx` | Main dashboard UI and client-side API interaction logic. |
| `frontend/src/app/layout.tsx` | Root application layout and metadata. |
| `frontend/src/app/globals.css` | Global styling for dashboard, forms, result cards, tables, and charts. |
| `frontend/package.json` | Frontend dependencies and scripts. |
| `frontend/next.config.ts` | Next.js configuration. |

### Main dashboard sections

Implemented dashboard sections:

- Header with platform title and system status.
- Database lanes for MongoDB and PostgreSQL status.
- Dataset setup panel.
- Benchmark configuration panel.
- Results panel.
- Previous results section.

### Dataset upload UI behavior

- The user can choose a `.csv` or `.json` file.
- Accepted file input types include `.csv`, `.json`, `text/csv`, and `application/json`.
- Upload sends a `FormData` request to `POST /api/datasets/upload`.
- On success:
  - dataset metadata is stored in React state.
  - previous load result is cleared.
  - current benchmark result is cleared.
  - success message is displayed.
- On failure:
  - dataset state is cleared.
  - error message is displayed.

### Sample dataset selection behavior

- The frontend loads sample options from `GET /api/datasets/samples`.
- The default selected sample ID in the UI is `sample_orders_1k_csv`.
- The sample selector displays dataset name and record count.
- Clicking **Use Sample Dataset** sends `sample_id` to `POST /api/datasets/sample`.
- On success:
  - selected dataset metadata is stored.
  - selected file state is cleared.
  - previous load result is cleared.
  - current benchmark result is cleared.

### Benchmark operation selector behavior

- Operation is selected from a `<select>` control.
- Supported UI options:
  - `WRITE`
  - `READ`
  - `UPDATE`
  - `DELETE`
- Default frontend operation is `WRITE`.

### Repetitions input behavior

- Repetitions are entered with a numeric input.
- Default frontend value is `3`.
- Frontend input attributes:
  - minimum `1`
  - maximum `20`
- Backend also validates repetitions with minimum `1` and maximum `20`.

### Record count display and determination

- `record_count` is displayed as read-only text under **Records used**.
- The user does not manually enter `record_count` in the current UI.
- The frontend sends `record_count: dataset.record_count`.
- This means the current UI benchmarks the full selected dataset.

### Run Benchmark button behavior

- The benchmark form calls `handleRunBenchmark`.
- The frontend blocks benchmark execution if:
  - no dataset is selected, or
  - the dataset has not been loaded into both databases with matching counts.
- The button is disabled when:
  - a benchmark is already running, or
  - `loadResult.counts_match` is not true.
- The request is sent to `POST /api/benchmarks/run`.
- Request body contains:
  - `dataset_id`
  - `operation`
  - `record_count`
  - `repetitions`
- On success:
  - latest benchmark result is displayed.
  - previous benchmark results are reloaded.
  - success message is displayed.
- On failure:
  - backend error detail is displayed when available.

### Loading states implemented

Implemented loading states:

- Backend/database health check loading state.
- Dataset upload/sample selection processing state.
- Dataset loading-to-databases state.
- Benchmark running state.
- Previous results loading state.

### Error states implemented

Implemented error states:

- Backend health check error.
- Sample dataset list loading error.
- Dataset upload error.
- Sample dataset selection error.
- Dataset loading error.
- Benchmark execution error.
- Previous results loading error.

### Result cards implemented

Implemented result panels:

- MongoDB result card, labeled as NoSQL.
- PostgreSQL result card, labeled as SQL.

Each result card displays:

- status badge
- total time
- average latency
- throughput
- minimum time
- maximum time
- standard deviation
- operation count
- benchmark target name
- per-repetition run times

### Comparison table implemented

The comparison table is implemented in `MetricComparison`.

Displayed metrics:

- total execution time
- average latency
- throughput
- minimum time
- maximum time
- standard deviation

The table includes:

- metric name
- MongoDB value
- PostgreSQL value
- faster database based on metric direction

### Charts implemented and types

Implemented in `BenchmarkCharts`.

Charts:

- Total execution time bar chart.
- Throughput bar chart.
- Repeated runs line chart.

Chart implementation details:

- Bar charts use HTML/CSS.
- The repeated runs chart uses inline SVG.
- No external charting package is used.

### Previous results table behavior

Implemented in `PreviousResults`.

Behavior:

- Previous results are loaded from `GET /api/benchmarks`.
- The section shows a loading badge while results are loading.
- If there are no results, the UI displays a no-results message.
- If results exist, the table displays the first 10 results from the loaded list.

Displayed previous result fields:

- benchmark ID
- dataset name
- operation
- MongoDB total time
- PostgreSQL total time
- throughput leader

## 3. Benchmarking Engine

### Main benchmark module

The benchmark engine is implemented in:

- `backend/app/benchmarks.py`

### Benchmark request model fields

Request model: `BenchmarkRunRequest`

Fields:

- `dataset_id`
- `operation`
- `record_count`
- `repetitions`

Validation:

- `operation` must be one of `WRITE`, `READ`, `UPDATE`, `DELETE`.
- `record_count` must be at least `1`.
- `repetitions` must be between `1` and `20`.

### Supported operations

Currently supported benchmark operations:

- `WRITE`
- `READ`
- `UPDATE`
- `DELETE`

### Removed parameters

- `selected_field` is removed from the current frontend, backend request model, UI, and benchmark logic.
- `index_enabled` is removed from the current frontend, backend request model, UI, and benchmark logic.
- No active source references to `selected_field`, `selectedField`, `index_enabled`, or `indexEnabled` were found in the current frontend/backend code.

### Temporary work table and collection behavior

Temporary benchmark storage:

- PostgreSQL work table: `benchmark_work_records`
- MongoDB work collection: `benchmark_work_records`

Behavior:

- The work table or collection is cleared before each repetition.
- PostgreSQL drops and recreates the work table.
- MongoDB drops the work collection.
- For non-WRITE operations, the first `record_count` source records are copied into the work storage before timing.
- For WRITE operations, the backend prepares the same first `record_count` logical records in the application and inserts them through each database driver.
- PostgreSQL work tables include a simple `benchmark_updated` boolean column for UPDATE benchmarks.
- MongoDB work documents include a `benchmark_updated` field for UPDATE benchmarks.

### PostgreSQL benchmark flow

Implemented in `run_postgres_benchmark`.

Flow:

1. Connects to PostgreSQL.
2. Counts source rows in `benchmark_dataset_records`.
3. Validates that the requested `record_count` is available.
4. Repeats the benchmark for `request.repetitions`.
5. For `WRITE`:
   - drops and recreates an empty work table.
   - adds the `benchmark_updated` boolean column outside timing.
   - commits setup.
   - uses the first `record_count` normalized records prepared by the backend application.
   - times psycopg `executemany` insertion and commit into the work table.
6. For `READ`:
   - drops and recreates the work table.
   - copies first `record_count` source rows into the work table.
   - adds the `benchmark_updated` boolean column outside timing.
   - commits setup.
   - times `SELECT *` with `record_index <= record_count`.
   - materializes returned rows with `fetchall`.
7. For `UPDATE`:
   - prepares the work table with copied source rows.
   - times update of the simple `benchmark_updated` column where `record_index <= record_count`.
8. For `DELETE`:
   - prepares the work table with copied source rows.
   - times deletion where `record_index <= record_count`.
9. Stores each repetition time in `run_times_ms`.
10. Stores each affected/read count in `affected_counts`.
11. Calculates metrics.
12. Returns a `BenchmarkDatabaseResult`.

### MongoDB benchmark flow

Implemented in `run_mongodb_benchmark`.

Flow:

1. Connects to MongoDB.
2. Uses source collection `benchmark_dataset_records`.
3. Uses work collection `benchmark_work_records`.
4. Counts source documents.
5. Validates that the requested `record_count` is available.
6. Repeats the benchmark for `request.repetitions`.
7. For `WRITE`:
   - uses the same first `record_count` normalized records prepared by the backend application.
   - creates MongoDB documents with `_id` equal to `record_index`.
   - drops the work collection.
   - times `insert_many` into the work collection.
8. For `READ`:
   - drops and repopulates the work collection with first `record_count` source documents.
   - sets `benchmark_updated` to `false` in copied work documents outside timing.
   - times `find` with `_id <= record_count`.
   - materializes returned documents with `list(...)`.
9. For `UPDATE`:
   - prepares the work collection with copied source documents.
   - times `update_many` setting `benchmark_updated` to `true` where `_id <= record_count`.
10. For `DELETE`:
   - prepares the work collection with copied source documents.
   - times `delete_many` where `_id <= record_count`.
11. Stores each repetition time in `run_times_ms`.
12. Stores each affected/read count in `affected_counts`.
13. Calculates metrics.
14. Returns a `BenchmarkDatabaseResult`.

### Repetition handling

- Repetitions are implemented with a loop in each database benchmark function.
- Each repetition prepares temporary work storage before running the timed operation.
- Each repetition produces:
  - one elapsed time
  - one affected/read count
- Metrics are calculated after all repetitions complete for each database.

### Timing measurement logic

- Timing uses Python `time.perf_counter`.
- `elapsed_ms` converts elapsed seconds to milliseconds.
- Timed sections include only the database operation under test.
- Temporary setup work is performed before the timer starts.
- WRITE timing measures the application-driven insert into empty work storage.
- READ timing measures materialized retrieval of matching rows/documents.
- UPDATE timing measures update operations against a simple benchmark update flag.
- DELETE timing measures delete operations.

### Error handling in benchmark execution

Benchmark-specific error handling:

- Missing PostgreSQL source table returns `400`.
- Empty loaded data returns `400`.
- Requested record count larger than loaded database count returns `400`.
- Unsupported benchmark operation returns `400`.
- PostgreSQL driver errors return `500`.
- MongoDB driver errors return `500`.
- Result storage errors return `500`.

### Fairness rules implemented in code

Implemented fairness controls:

- Same `operation` value is sent to both database benchmark functions.
- Same `record_count` is sent to both database benchmark functions.
- Same `repetitions` value is sent to both database benchmark functions.
- Both databases read from a loaded source dataset named `benchmark_dataset_records`.
- Both databases use temporary benchmark storage named `benchmark_work_records`.
- Temporary benchmark storage is reset before each repetition.
- WRITE uses the same first `record_count` application-prepared logical records for both databases.
- READ materializes matching rows/documents for both databases instead of using count-only reads.
- UPDATE modifies a simple benchmark update flag in both databases.
- Metrics for both databases are calculated using the same `calculate_metrics` function.
- Both services run in the same Docker Compose environment.

Limitations:

- PostgreSQL runs first, then MongoDB.
- Repetitions are not interleaved between databases.
- No warm-up run is implemented.
- No explicit cache clearing is implemented.
- No CPU or memory monitoring is implemented.
- No concurrent workload execution is implemented.
- No explicit Docker CPU or memory limits are configured.

## 4. Data Collection and Storage

### Metrics calculated

Metric model: `BenchmarkMetrics`

Calculated metrics:

- `total_time_ms`
- `average_latency_ms`
- `throughput_ops_sec`
- `min_time_ms`
- `max_time_ms`
- `std_dev_ms`
- `operation_count`

Not implemented:

- p95 latency
- success rate as a percentage metric
- CPU usage
- memory/RAM usage

### Metric calculation function

Metrics are calculated by:

- `calculate_metrics` in `backend/app/benchmarks.py`

Calculation behavior:

- `total_time_ms`: sum of repetition times.
- `operation_count`: sum of affected/read counts.
- `average_latency_ms`: total time divided by operation count.
- `throughput_ops_sec`: operation count divided by total time in seconds.
- `min_time_ms`: minimum repetition time.
- `max_time_ms`: maximum repetition time.
- `std_dev_ms`: population standard deviation across repetition times.

### Result object structure

Top-level result model: `BenchmarkRunResult`

Fields:

- `benchmark_id`
- `created_at`
- `dataset_id`
- `dataset_name`
- `operation`
- `record_count`
- `repetitions`
- `postgresql`
- `mongodb`

Per-database model: `BenchmarkDatabaseResult`

Fields:

- `ok`
- `target_name`
- `run_times_ms`
- `affected_counts`
- `metrics`
- `message`

Per-database metrics model: `BenchmarkMetrics`

Fields:

- `total_time_ms`
- `average_latency_ms`
- `throughput_ops_sec`
- `min_time_ms`
- `max_time_ms`
- `std_dev_ms`
- `operation_count`

### MongoDB `benchmark_results` collection behavior

Result storage collection:

- `benchmark_results`

Storage behavior:

- Benchmark results are stored in MongoDB.
- `store_benchmark_result` uses `replace_one`.
- The replacement filter is `benchmark_id`.
- `upsert=True` is enabled.
- Stored documents exclude MongoDB internal `_id` when read back by the API.

### Fields stored in each benchmark result

Stored benchmark result fields:

- `benchmark_id`
- `created_at`
- `dataset_id`
- `dataset_name`
- `operation`
- `record_count`
- `repetitions`
- `postgresql`
- `mongodb`

Stored under each database result:

- `ok`
- `target_name`
- `run_times_ms`
- `affected_counts`
- `metrics`
- `message`

Stored under metrics:

- `total_time_ms`
- `average_latency_ms`
- `throughput_ops_sec`
- `min_time_ms`
- `max_time_ms`
- `std_dev_ms`
- `operation_count`

### Previous results API behavior

Implemented endpoints:

- `GET /api/benchmarks`
- `GET /api/benchmarks/{benchmark_id}`

List behavior:

- Reads from MongoDB `benchmark_results`.
- Excludes internal `_id`.
- Sorts by `created_at` descending.
- Returns a list of `BenchmarkRunResult` objects.

Detail behavior:

- Looks up one document by `benchmark_id`.
- Excludes internal `_id`.
- Returns `404` if no matching result is found.

### How frontend uses stored results

- The frontend calls `loadBenchmarkResults` when the dashboard first loads.
- The same function is called again after a successful benchmark run.
- Returned results are stored in React state as `previousResults`.
- The previous results table renders from this state.

### Fields shown in previous results table

The frontend previous results table displays:

- benchmark ID
- dataset name
- operation
- MongoDB total time
- PostgreSQL total time
- throughput leader

## 5. Figures or Tables Recommended for Chapter 4

Minimal recommendations:

- Include one frontend screenshot of the full dashboard after a completed benchmark. This can show dataset setup, benchmark configuration, result cards, comparison table, charts, and previous results in one implementation figure.
- Include one benchmark execution flow diagram only if Chapter 3 does not already cover the implementation-level sequence. Keep it focused on frontend request, backend benchmark execution, database operations, result storage, and frontend display.
- Include one compact result object table listing `BenchmarkRunResult`, `BenchmarkDatabaseResult`, and `BenchmarkMetrics` fields.

Avoid adding too many additional diagrams in Chapter 4 if Chapter 3 already contains architecture and design diagrams.
