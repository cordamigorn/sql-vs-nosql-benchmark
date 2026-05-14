# Benchmark Implementation Technical Audit Report

Scope at time of writing: static inspection of the then-current codebase only. No benchmark code had been modified when this report was originally produced.

Status note: this report was generated before the benchmark fairness fixes applied after the audit. Sections that describe PostgreSQL `record_data JSONB`, fixed PostgreSQL-first execution, missing warm-up runs, missing affected-count validation, or the "Average latency" UI label refer to the pre-fix implementation state and are retained as historical audit findings.

Project context: local, single-user, Docker-based web benchmark comparing PostgreSQL and MongoDB on CSV, JSON, and sample datasets for WRITE, READ, UPDATE, and DELETE operations.

## 1. Benchmark Flow Overview

When the user runs a benchmark, the flow is:

1. Frontend component: `frontend/src/app/page.tsx`
   - `Home` stores benchmark state: `operation`, `repetitions`, `benchmarkResult`, and `previousResults` at lines 89-108.
   - The benchmark form is rendered at lines 535-572.
   - `handleRunBenchmark(event)` sends the benchmark request at lines 370-408.

2. Frontend request:

```ts
fetch(`${apiBaseUrl}/api/benchmarks/run`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    dataset_id: dataset.dataset_id,
    operation,
    record_count: dataset.record_count,
    repetitions,
  }),
});
```

Evidence: `frontend/src/app/page.tsx:385-395`.

3. Backend endpoint:
   - `POST /api/benchmarks/run`
   - Function: `run_benchmark_endpoint`
   - File: `backend/app/main.py:105-107`
   - It receives `BenchmarkRunRequest` and calls `run_benchmark(request)`.

4. Backend benchmark service:
   - Function: `run_benchmark`
   - File: `backend/app/benchmarks.py:68-89`
   - It calls:
     - `get_dataset(request.dataset_id)` at line 69.
     - `prepare_dataset(dataset)` at line 70.
     - `validate_record_count(...)` at line 71.
     - `run_postgres_benchmark(...)` at line 73.
     - `run_mongodb_benchmark(...)` at line 74.
     - `store_benchmark_result(result)` at line 88.

5. Operation dispatch:
   - PostgreSQL dispatch occurs inside `run_postgres_benchmark` at `backend/app/benchmarks.py:193-212`.
     - If `request.operation == "WRITE"`, it calls `time_postgres_write`.
     - Otherwise, it calls `time_postgres_operation`, which branches on READ, UPDATE, DELETE at lines 315, 329, and 341.
   - MongoDB dispatch occurs inside `run_mongodb_benchmark` at `backend/app/benchmarks.py:372-384`.
     - If `request.operation == "WRITE"`, it calls `time_mongodb_write`.
     - Otherwise, it calls `time_mongodb_operation`, which branches on READ, UPDATE, DELETE at lines 446, 458, and 463.

6. Database execution order:
   - PostgreSQL always runs first.
   - MongoDB always runs second.
   - Evidence: `backend/app/benchmarks.py:73-74`.
   - The repetitions are not interleaved. PostgreSQL completes all repetitions before MongoDB starts.

Execution order can affect results. Because PostgreSQL always runs before MongoDB, MongoDB may benefit from Python code warm-up, CPU frequency effects, Docker resource warm-up, or OS/page cache effects caused by earlier work. This does not explain every observed result, because PostgreSQL is still faster for UPDATE and DELETE while running first, but it is still a repeatability risk. There is no warm-up run and no alternating order.

## 2. Benchmark Request Model

Backend request model:

File: `backend/app/benchmarks.py:30-34`

```py
class BenchmarkRunRequest(BaseModel):
    dataset_id: str
    operation: BenchmarkOperation
    record_count: int = Field(ge=1)
    repetitions: int = Field(ge=1, le=20)
```

Operation type:

File: `backend/app/benchmarks.py:27`

```py
BenchmarkOperation = Literal["WRITE", "READ", "UPDATE", "DELETE"]
```

Accepted active fields:

| Field | Used? | Evidence |
|---|---:|---|
| `dataset_id` | Yes | Used to retrieve the in-memory dataset in `run_benchmark`, `backend/app/benchmarks.py:69`. |
| `operation` | Yes | Used for dispatch in PostgreSQL and MongoDB runners, `backend/app/benchmarks.py:194`, `309-353`, `373`, `438-468`. |
| `record_count` | Yes | Validated, used for slicing prepared records, setup limits, and operation filters. Examples: `backend/app/benchmarks.py:71`, `191`, `201`, `210`, `370`, `382`. |
| `repetitions` | Yes | Controls repetition loops in both runners, `backend/app/benchmarks.py:193`, `372`. |

Frontend payload:

File: `frontend/src/app/page.tsx:390-395`

```ts
{
  dataset_id: dataset.dataset_id,
  operation,
  record_count: dataset.record_count,
  repetitions,
}
```

The UI does not allow a custom record count; it always uses the full selected dataset count. Evidence: read-only "Records used" at `frontend/src/app/page.tsx:560-563`.

`index_enabled` and `selected_field`:

- No active references were found in `backend/` or `frontend/`.
- The only matches are documentation references in `BENCHMARK_IMPLEMENTATION_FACTUAL_SUMMARY.md` and `CHAPTER4.md`.
- Therefore they are not active request fields and are not used by the benchmark implementation.

Recommendation: keep them removed from active code for the current thesis scope. If thesis text still implies active index or selected-field benchmarks, update the text, not the implementation.

One additional model note: `BenchmarkRunRequest` does not explicitly forbid extra fields. The declared API schema contains only the four active fields, but unexpected fields would not be used by any current code path.

## 3. Dataset Loading and Preparation

Dataset API flow:

- Upload endpoint: `upload_dataset`, `backend/app/main.py:76-86`.
- Sample endpoint: `use_sample_dataset`, `backend/app/main.py:94-96`.
- Load endpoint: `load_dataset`, `backend/app/main.py:99-102`.
- Load service: `load_dataset_to_databases`, `backend/app/loaders.py:51-71`.

CSV parsing:

- Function: `parse_csv_dataset`
- File: `backend/app/datasets.py:110-141`
- Uses Python `csv.reader`.
- First row is the header.
- Header fields are stripped.
- Each data value is stripped and stored as a string:

```py
records.append({field: value.strip() for field, value in zip(fields, row, strict=True)})
```

Evidence: `backend/app/datasets.py:136`.

JSON parsing:

- Function: `parse_json_dataset`
- File: `backend/app/datasets.py:144-185`
- Uses `json.loads`.
- Requires a top-level array of flat objects.
- Requires all objects to have the same fields as the first object.
- Rejects nested dict/list values.
- Preserves JSON scalar Python types: numbers remain `int`/`float`, booleans remain `bool`, null remains `None`, strings remain `str`.

Evidence: `backend/app/datasets.py:146`, `150-183`.

Sample dataset loading:

- Function: `load_sample_dataset`
- File: `backend/app/datasets.py:192-216`
- Scans `sample_datasets` with `_scan_sample_datasets`, `backend/app/datasets.py:232-256`.
- Reads the selected file with `_read_dataset_file`, `backend/app/datasets.py:375-381`.
- Parses CSV or JSON through the same parser used for uploaded files, `backend/app/datasets.py:205-208`.

Internal prepared format:

- Function: `prepare_dataset`
- File: `backend/app/loaders.py:74-93`
- Builds a `PreparedDataset` with:
  - `fields`: original dataset field names.
  - `column_map`: PostgreSQL-safe column names.
  - `records`: normalized records with `record_index`.

```py
{
    "record_index": index,
    **{field: record.get(field) for field in dataset.metadata.fields},
}
```

Evidence: `backend/app/loaders.py:81-87`.

Same records loaded into both databases:

- `load_dataset_to_databases` calls `prepare_dataset(dataset)` once, then passes the same prepared object to `load_postgres(prepared)` and `load_mongodb(prepared)`.
- Evidence: `backend/app/loaders.py:51-55`.

Record count verification:

- During load, both database counts are compared with the expected dataset count and with each other in `counts_match`.
- Evidence: `backend/app/loaders.py:56-62`.
- During benchmark, source counts are checked:
  - PostgreSQL: `get_postgres_source_count`, `backend/app/benchmarks.py:190-191`, `234-238`.
  - MongoDB: `source.count_documents({})`, `backend/app/benchmarks.py:369-370`.

Field name normalization:

- PostgreSQL column names are normalized by `build_column_map`, `backend/app/loaders.py:96-116`.
- MongoDB field names are not normalized; original dataset field names are used.
- This means PostgreSQL READ rows use normalized SQL column names, while MongoDB READ documents use original field names.

Data type preservation and conversion:

- CSV data is parsed as strings for both systems.
- JSON scalar data is preserved in the in-memory dataset.
- PostgreSQL stores each dataset column as `TEXT`, so values are converted to strings for column storage:
  - Initial load: `backend/app/loaders.py:177`.
  - WRITE benchmark: `backend/app/benchmarks.py:294`.
- PostgreSQL also stores the original source record as `record_data JSONB`, preserving JSON scalar types inside that JSONB copy:
  - Initial load: `backend/app/loaders.py:178`.
  - WRITE benchmark: `backend/app/benchmarks.py:297`.
- MongoDB stores original scalar values directly in top-level document fields:
  - Initial load: `backend/app/loaders.py:198-200`.
  - WRITE benchmark: `backend/app/benchmarks.py:419-422`.

Fairness implication:

- PostgreSQL stores duplicated payload: text columns plus `record_data JSONB`.
- MongoDB stores top-level fields plus `_id`; it does not store a duplicate full-record JSON field.
- For JSON datasets, PostgreSQL selected columns are text strings while MongoDB selected fields preserve numeric/boolean/null types.
- This can affect WRITE payload size, storage size, READ page/cache behavior, and Python driver conversion cost.

## 4. Work Table / Temporary Collection Strategy

Main source storage names:

- PostgreSQL source table: `benchmark_dataset_records`
  - Constant: `POSTGRES_TABLE_NAME`, `backend/app/loaders.py:20`.
- MongoDB source collection: `benchmark_dataset_records`
  - Constant: `MONGO_COLLECTION_NAME`, `backend/app/loaders.py:21`.

Work storage names:

- PostgreSQL work table: `benchmark_work_records`
  - Constant: `POSTGRES_WORK_TABLE_NAME`, `backend/app/benchmarks.py:23`.
- MongoDB work collection: `benchmark_work_records`
  - Constant: `MONGO_WORK_COLLECTION_NAME`, `backend/app/benchmarks.py:24`.

PostgreSQL work setup:

- Function: `setup_postgres_work_table`
- File: `backend/app/benchmarks.py:241-268`
- Steps:
  1. `DROP TABLE IF EXISTS benchmark_work_records`.
  2. `CREATE TABLE benchmark_work_records (LIKE benchmark_dataset_records INCLUDING ALL)`.
  3. If `copy_records=True`, copy `record_count` rows from the source table with `INSERT INTO work SELECT * FROM source ORDER BY record_index LIMIT %s`.
  4. Add `benchmark_updated BOOLEAN NOT NULL DEFAULT FALSE`.

MongoDB work setup:

- Function: `setup_mongodb_work_collection`
- File: `backend/app/benchmarks.py:404-410`
- Steps:
  1. `work.drop()`.
  2. Read `record_count` source documents sorted by `record_index`.
  3. Add `benchmark_updated = False` to each copied document.
  4. Insert copied docs into the work collection with `insert_many(..., ordered=False)`.

Reset behavior by operation:

| Operation | PostgreSQL setup | MongoDB setup | Timed setup? |
|---|---|---|---|
| WRITE | Drop/create empty work table, add flag column | Drop work collection, prepare docs | No |
| READ | Drop/create work table, copy N source rows, add flag column | Drop work collection, copy N source docs, add flag field | No |
| UPDATE | Same as READ | Same as READ | No |
| DELETE | Same as READ | Same as READ | No |

The work table/collection is reset before each repetition, not only once before the whole benchmark.

Evidence:

- PostgreSQL loop: `backend/app/benchmarks.py:193-215`.
- MongoDB loop: `backend/app/benchmarks.py:372-387`.

Cleanup/reload timing:

- PostgreSQL setup is followed by `connection.commit()` before the measured function is called. Evidence: `backend/app/benchmarks.py:195-206`.
- MongoDB setup/drop occurs before the measured function is called. Evidence: `backend/app/benchmarks.py:374-379`.
- Therefore cleanup and reload time are outside measured benchmark time for both databases.

This is good for operation-only timing, but it means the reported UPDATE and DELETE times do not include the cost of making the work dataset available again.

## 5. WRITE Benchmark Audit

### PostgreSQL WRITE

Function:

- `time_postgres_write`
- File: `backend/app/benchmarks.py:271-305`

SQL shape:

```sql
INSERT INTO benchmark_work_records
  (record_index, <dataset text columns>, record_data)
VALUES
  (%s, %s, ..., %s)
```

Evidence: query construction at `backend/app/benchmarks.py:279-285`.

Implementation details:

- Uses `cursor.executemany(query, values)`.
- Evidence: `backend/app/benchmarks.py:302`.
- Does not use `COPY`.
- Does not use `execute_values`.
- Does not build a single multi-row `INSERT`.
- It prepares all parameter tuples before the timer starts.
- Timer starts at `backend/app/benchmarks.py:301`.
- Commit happens before timing stops:

```py
started = perf_counter()
cursor.executemany(query, values)
affected = cursor.rowcount if cursor.rowcount >= 0 else len(values)
connection.commit()
return elapsed_ms(started), affected
```

Evidence: `backend/app/benchmarks.py:301-305`.

Transaction and commit:

- The insert runs in the connection transaction.
- `connection.commit()` is included in measured time.

Indexes/constraints:

- The source table is created with `record_index BIGINT PRIMARY KEY`, dataset `TEXT` columns, and `record_data JSONB NOT NULL`.
- Evidence: `backend/app/loaders.py:152-158`.
- The work table is created with `LIKE ... INCLUDING ALL`, so it inherits equivalent schema/index/constraint structure from the source table.
- Evidence: `backend/app/benchmarks.py:247-253`.
- A `benchmark_updated BOOLEAN NOT NULL DEFAULT FALSE` column is added before timing, `backend/app/benchmarks.py:264-268`.

Records inserted into empty table each repetition:

- Yes. For WRITE, `setup_postgres_work_table(copy_records=False)` drops and recreates the table before every repetition.
- Evidence: `backend/app/benchmarks.py:193-202`, `247-253`.

Payload:

- Inserted values include:
  - `record_index`
  - one text column for each dataset field
  - `record_data JSONB` duplicate of the original source record
- `benchmark_updated` exists in the table but is not sent in the insert; PostgreSQL fills the default value.

### MongoDB WRITE

Functions:

- `prepare_mongodb_write_documents`
- `time_mongodb_write`
- File: `backend/app/benchmarks.py:413-435`

Implementation:

- Drops the work collection before timing.
- Prepares a list of docs before timing.
- Uses `work.insert_many(docs, ordered=False)`.
- Evidence: `backend/app/benchmarks.py:374-376`, `428-435`.

Document shape:

```py
{
    "_id": record["record_index"],
    "record_index": record["record_index"],
    **{field: record[field] for field in prepared.fields},
    "benchmark_updated": False,
}
```

Evidence: `backend/app/benchmarks.py:417-424`.

Write concern:

- No explicit write concern or journaling option is configured in the code.
- PyMongo uses the MongoClient/database/collection default write concern.
- The timing includes the acknowledged result because `insert_many` returns and `len(result.inserted_ids)` is read.
- Evidence: `backend/app/benchmarks.py:431-432`.

Records inserted into empty collection each repetition:

- Yes. For WRITE, `work.drop()` is called before `time_mongodb_write`.
- Evidence: `backend/app/benchmarks.py:374-376`.

### WRITE Fairness Assessment

Confirmed fair points:

- Both databases insert the same requested number of logical records.
- Both use fresh empty work storage each repetition.
- Both exclude setup/drop time from the measured insert.
- Both include write acknowledgement/commit boundary in their respective client calls.

Confirmed unfair or non-equivalent points:

- PostgreSQL stores duplicated data: text columns plus `record_data JSONB`.
- MongoDB stores top-level fields plus `_id`, with no duplicate full-record JSON field.
- PostgreSQL uses `executemany`, not `COPY` or a multi-value bulk insert.
- MongoDB uses `insert_many`, a native batch insert API.
- PostgreSQL has a primary key index on `record_index`; MongoDB has the automatic `_id` index. These are conceptually similar for uniqueness but the actual write paths differ.

Conclusion for WRITE: MongoDB being much faster is expected from this implementation, but the result is not a clean database-engine comparison. It is strongly influenced by PostgreSQL's less efficient insert method and larger duplicated payload.

## 6. READ Benchmark Audit

### PostgreSQL READ

Function:

- `time_postgres_operation`
- READ branch at `backend/app/benchmarks.py:315-327`

SQL query:

```sql
SELECT record_index, <dataset text columns>, benchmark_updated
FROM benchmark_work_records
WHERE record_index <= %s
ORDER BY record_index
```

Evidence: `backend/app/benchmarks.py:316-324`.

Behavior:

- Does not use `SELECT *`.
- Selects:
  - `record_index`
  - normalized dataset columns from `prepared.column_map.values()`
  - `benchmark_updated`
- Excludes `record_data JSONB`.
- Filters by `record_index <= record_count`.
- Orders by `record_index`.
- Fetches all rows into memory using `cursor.fetchall()`.
- Fetch time and Python materialization are included in timing.

Evidence: `backend/app/benchmarks.py:317-327`.

### MongoDB READ

Function:

- `time_mongodb_operation`
- READ branch at `backend/app/benchmarks.py:446-456`

Query:

```py
filter_query = {"_id": {"$lte": record_count}}
projection = {
    "_id": 0,
    "record_index": 1,
    "benchmark_updated": 1,
    **{field: 1 for field in prepared.fields},
}
docs = list(work.find(filter_query, projection).sort("_id", ASCENDING))
```

Evidence: `backend/app/benchmarks.py:444-455`.

Behavior:

- Uses `find()`.
- Uses projection.
- Excludes `_id`.
- Includes:
  - `record_index`
  - dataset fields using original field names
  - `benchmark_updated`
- Filters by `_id <= record_count`.
- Sorts by `_id`.
- Materializes the cursor with `list(...)`.
- Cursor execution, network transfer, driver decoding, and Python list materialization are included in timing.

### READ Fairness Assessment

Confirmed fair points:

- Both databases read the same number of logical records when source/work data are valid.
- Both read by an indexed dense key:
  - PostgreSQL: `record_index` primary key.
  - MongoDB: `_id`.
- Both materialize all results into Python memory.
- PostgreSQL excludes `record_data`.
- MongoDB excludes `_id`.

Remaining differences:

- PostgreSQL returns normalized SQL column names; MongoDB returns original dataset field names.
- PostgreSQL selected dataset values are text columns; MongoDB values preserve original JSON scalar types.
- PostgreSQL rows are physically wider because the table also contains `record_data JSONB`, even though READ does not select it. This can affect heap/page/cache behavior.
- READ measures database query plus driver transfer plus Python materialization, not pure database execution time.

Conclusion for READ: MongoDB being slightly faster is explainable. The implementation is closer to equivalent than WRITE, but it is still affected by schema/payload differences and by the fixed execution order.

## 7. UPDATE Benchmark Audit

### PostgreSQL UPDATE

Function:

- `time_postgres_operation`
- UPDATE branch at `backend/app/benchmarks.py:329-339`

SQL:

```sql
UPDATE benchmark_work_records
SET benchmark_updated = TRUE
WHERE record_index <= %s
```

Evidence: `backend/app/benchmarks.py:331-335`.

Behavior:

- Updates rows where `record_index <= record_count`.
- Updates the benchmark control column `benchmark_updated`, not a dataset field.
- Uses one set-based SQL statement, not one row at a time.
- Uses `cursor.rowcount` as affected count.
- Includes `connection.commit()` in timing.

Evidence: `backend/app/benchmarks.py:330-339`.

### MongoDB UPDATE

Function:

- `time_mongodb_operation`
- UPDATE branch at `backend/app/benchmarks.py:458-461`

Command:

```py
work.update_many(
    {"_id": {"$lte": record_count}},
    {"$set": {"benchmark_updated": True}},
)
```

Evidence: `backend/app/benchmarks.py:444`, `459-461`.

Behavior:

- Updates documents where `_id <= record_count`.
- Updates `benchmark_updated`, not a dataset field.
- Uses `update_many`.
- Uses `result.modified_count` as affected count.
- Includes write acknowledgement because the method returns a result.

### UPDATE Fairness Assessment

Confirmed fair points:

- Both update the same logical number of records/documents when setup succeeds.
- Both update an existing benchmark field:
  - PostgreSQL adds `benchmark_updated BOOLEAN NOT NULL DEFAULT FALSE` during setup.
  - MongoDB sets `benchmark_updated = False` in copied docs during setup.
- MongoDB is not creating a new field during the timed update.
- Work data is reset before every repetition.

Remaining differences:

- PostgreSQL updates a typed boolean column.
- MongoDB updates a field inside BSON documents.
- PostgreSQL measured time includes transaction commit.
- MongoDB measured time includes acknowledged update completion, but no explicit transaction commit and no explicit write concern/journal setting.

Conclusion for UPDATE: PostgreSQL being faster is explainable and is more likely a real result under this implementation than an obvious benchmark bug. Durability/write-concern differences and execution order should still be documented before thesis experiments.

## 8. DELETE Benchmark Audit

### PostgreSQL DELETE

Function:

- `time_postgres_operation`
- DELETE branch at `backend/app/benchmarks.py:341-351`

SQL:

```sql
DELETE FROM benchmark_work_records
WHERE record_index <= %s
```

Evidence: `backend/app/benchmarks.py:343-347`.

Behavior:

- Uses `DELETE`, not `TRUNCATE`.
- Does not drop/recreate the table inside the timed operation.
- Deletes from the work table, not the main source table.
- Uses `record_index <= record_count`.
- Includes `connection.commit()` in timing.
- Uses `cursor.rowcount` as affected count.

Evidence: `backend/app/benchmarks.py:342-351`.

### MongoDB DELETE

Function:

- `time_mongodb_operation`
- DELETE branch at `backend/app/benchmarks.py:463-466`

Command:

```py
work.delete_many({"_id": {"$lte": record_count}})
```

Evidence: `backend/app/benchmarks.py:444`, `464-466`.

Behavior:

- Uses `delete_many`.
- Does not drop the collection inside the timed delete.
- Deletes from the work collection, not the main source collection.
- Deletes documents where `_id <= record_count`.
- Uses `result.deleted_count` as affected count.
- Includes acknowledged delete completion because the method returns a result.

### DELETE Fairness Assessment

Confirmed fair points:

- Both use real row/document deletion.
- Neither side uses a faster metadata operation such as PostgreSQL `TRUNCATE` or MongoDB `drop()` for the timed DELETE.
- Work data is reloaded before each repetition.
- Each repetition should delete the same number of records/documents if setup succeeds.
- Both delete by indexed dense key:
  - PostgreSQL primary key `record_index`.
  - MongoDB automatic `_id` index.

Gaps:

- The code records `rowcount` and `deleted_count`, but does not validate them against `record_count`.
- The code does not fail if a repetition deletes fewer records than intended.

Conclusion for DELETE: The very large PostgreSQL advantage is not explained by a truncate/drop mismatch. The code path performs comparable logical delete operations. The result may be caused by PostgreSQL and MongoDB storage-engine behavior, default durability/write concern differences, driver overhead, or Docker/cache effects. It should be validated with affected-count checks, warm-up, and alternating order before being used as a final thesis claim.

## 9. Timing Measurement Audit

Timing function:

- Uses `time.perf_counter`.
- Import: `backend/app/benchmarks.py:5`.
- Timer helper: `elapsed_ms(started)`, `backend/app/benchmarks.py:488-489`.

```py
return round((perf_counter() - started) * 1000, 4)
```

Timer boundaries:

| Operation | PostgreSQL timer starts | PostgreSQL timer stops | MongoDB timer starts | MongoDB timer stops |
|---|---|---|---|---|
| WRITE | Before `cursor.executemany` | After `connection.commit()` | Before `insert_many` | After `insert_many` result is returned |
| READ | Before `cursor.execute` | After `cursor.fetchall()` | Before `find(...).sort(...)` materialization | After `list(cursor)` |
| UPDATE | Before `cursor.execute` | After `connection.commit()` | Before `update_many` | After result is returned |
| DELETE | Before `cursor.execute` | After `connection.commit()` | Before `delete_many` | After result is returned |

Evidence:

- PostgreSQL WRITE: `backend/app/benchmarks.py:301-305`.
- PostgreSQL READ: `backend/app/benchmarks.py:317-327`.
- PostgreSQL UPDATE: `backend/app/benchmarks.py:330-339`.
- PostgreSQL DELETE: `backend/app/benchmarks.py:342-351`.
- MongoDB WRITE: `backend/app/benchmarks.py:429-435`.
- MongoDB READ: `backend/app/benchmarks.py:453-456`.
- MongoDB UPDATE: `backend/app/benchmarks.py:459-461`.
- MongoDB DELETE: `backend/app/benchmarks.py:464-466`.

Included in timing:

- PostgreSQL commit for WRITE, UPDATE, DELETE.
- MongoDB acknowledged operation completion for WRITE, UPDATE, DELETE.
- Result fetching/materialization for READ on both databases.
- Driver and Python materialization overhead.

Excluded from timing:

- Dataset parsing.
- Dataset loading into source table/collection.
- Work table/collection drop/create.
- Work table/collection reload for READ, UPDATE, DELETE.
- PostgreSQL `ALTER TABLE ... ADD COLUMN benchmark_updated`.
- MongoDB addition of `benchmark_updated = False` during work setup.
- Preparation of PostgreSQL parameter tuples and MongoDB document lists for WRITE.

Repetition handling:

- Each repetition has one measured elapsed time.
- `run_times_ms` stores per-repetition times.
- `affected_counts` stores per-repetition affected counts.
- Evidence: `backend/app/benchmarks.py:214-215`, `386-387`.

Metric formulas:

File: `backend/app/benchmarks.py:147-177`

```py
total_time_ms = sum(run_times_ms)
operation_count = sum(affected_counts)
average_latency_ms = total_time_ms / operation_count if operation_count > 0 else 0
throughput_ops_sec = operation_count / (total_time_ms / 1000) if total_time_ms > 0 else 0
```

Units:

- `run_times_ms` are milliseconds.
- `total_time_ms`, `average_latency_ms`, `min_time_ms`, `max_time_ms`, and `std_dev_ms` are milliseconds.
- `throughput_ops_sec` is operations per second.
- No direct ms/second formula mismatch was found.

Important naming issue:

- `average_latency_ms` is not latency per database command.
- It is average time per affected row/document: `total_time_ms / operation_count`.
- For set-based READ/UPDATE/DELETE commands, this is a per-record derived value, not a per-query latency measurement.

## 10. Metrics Calculation Audit

Function:

- `calculate_metrics`
- File: `backend/app/benchmarks.py:147-177`

Formulas:

| Metric | Formula | Evidence |
|---|---|---|
| Total execution time | `sum(run_times_ms)` | `backend/app/benchmarks.py:151` |
| Operation count | `sum(affected_counts)` | `backend/app/benchmarks.py:152` |
| Average latency | `total_time_ms / operation_count` | `backend/app/benchmarks.py:153` |
| Throughput | `operation_count / (total_time_ms / 1000)` | `backend/app/benchmarks.py:154` |
| Min time | `min(run_times_ms)` | `backend/app/benchmarks.py:157` |
| Max time | `max(run_times_ms)` | `backend/app/benchmarks.py:158` |
| Std dev | `sqrt(sum((x - mean)^2) / len(run_times_ms))` | `backend/app/benchmarks.py:159-163` |

Standard deviation type:

- Population standard deviation, because it divides by `len(run_times_ms)`, not `len(run_times_ms) - 1`.

Rounding:

- Metrics are rounded before returning and before storage:
  - total/min/max/std: 4 decimals.
  - average latency: 6 decimals.
  - throughput: 4 decimals.
- Evidence: `backend/app/benchmarks.py:169-176`.
- Individual run times are rounded by `elapsed_ms`, `backend/app/benchmarks.py:488-489`.
- UI formatting is visual only, using `toLocaleString`, `formatMs`, and `toFixed` for run labels. Evidence: `frontend/src/app/page.tsx:699`, `1104-1121`.

Operation count correctness:

- The code uses actual affected counts, not `record_count * repetitions`.
- If every repetition affects all requested records, operation count equals `record_count * repetitions`.
- This is safer than assuming success, but there is no validation that affected counts equal the requested count.

Both databases use the same metric formula because both `BenchmarkDatabaseResult` objects call `calculate_metrics(run_times_ms, affected_counts)`.

Evidence:

- PostgreSQL: `backend/app/benchmarks.py:222`.
- MongoDB: `backend/app/benchmarks.py:394`.

## 11. Execution Order and Warm-Up Effects

Order:

- PostgreSQL always runs before MongoDB.
- Evidence: `backend/app/benchmarks.py:73-74`.

No warm-up:

- No warm-up benchmark is implemented.
- Every measured repetition contributes to final metrics.

Connections:

- PostgreSQL opens one connection for all repetitions of the PostgreSQL side of the benchmark.
  - Evidence: `backend/app/benchmarks.py:188-189`.
- MongoDB opens one `MongoClient` for all repetitions of the MongoDB side of the benchmark.
  - Evidence: `backend/app/benchmarks.py:365-368`.

Prepared statements:

- No explicit prepared statements are configured in the benchmark code.
- PostgreSQL uses `cursor.executemany` for WRITE and `cursor.execute` for READ/UPDATE/DELETE.
- MongoDB uses normal PyMongo collection methods.

Risk:

- The second database may benefit from warmed Python code paths, CPU frequency changes, Docker/VM cache effects, and OS file cache state.
- The first database may be disadvantaged.
- Because PostgreSQL is first and MongoDB is second, WRITE and READ MongoDB advantages may be slightly inflated.
- Because PostgreSQL still wins UPDATE and DELETE while running first, fixed order is not the only explanation.

Recommendation:

- Add an unmeasured warm-up phase.
- Alternate or randomize database order per benchmark run.
- Prefer interleaving repetitions if the goal is to reduce temporal bias.

## 12. Database Schema and Payload Fairness

PostgreSQL source schema:

Function:

- `recreate_postgres_table`
- File: `backend/app/loaders.py:146-158`

Schema:

```sql
CREATE TABLE benchmark_dataset_records (
  record_index BIGINT PRIMARY KEY,
  <normalized dataset columns> TEXT,
  record_data JSONB NOT NULL
)
```

Evidence: `backend/app/loaders.py:149-158`.

PostgreSQL work schema:

Function:

- `setup_postgres_work_table`
- File: `backend/app/benchmarks.py:241-268`

Schema strategy:

```sql
CREATE TABLE benchmark_work_records
(LIKE benchmark_dataset_records INCLUDING ALL);

ALTER TABLE benchmark_work_records
ADD COLUMN benchmark_updated BOOLEAN NOT NULL DEFAULT FALSE;
```

Evidence: `backend/app/benchmarks.py:247-268`.

MongoDB source document structure:

Function:

- `load_mongodb`
- File: `backend/app/loaders.py:185-218`

Document shape:

```py
{
  "_id": record["record_index"],
  "record_index": record["record_index"],
  **{field: record[field] for field in prepared.fields},
}
```

Evidence: `backend/app/loaders.py:195-204`.

MongoDB work document structure:

- WRITE work documents are built in `prepare_mongodb_write_documents`, `backend/app/benchmarks.py:413-425`.
- READ/UPDATE/DELETE work documents are copied from source and given `benchmark_updated = False`, `backend/app/benchmarks.py:404-410`.

Payload comparison:

| Storage | Internal fields | Dataset fields | Duplicate full record? |
|---|---|---|---|
| PostgreSQL source | `record_index`, `record_data` | normalized `TEXT` columns | Yes, `record_data JSONB` |
| PostgreSQL work | `record_index`, `record_data`, `benchmark_updated` | normalized `TEXT` columns | Yes, `record_data JSONB` |
| MongoDB source | `_id`, `record_index` | original fields | No |
| MongoDB work | `_id`, `record_index`, `benchmark_updated` | original fields | No |

READ payload comparison:

- PostgreSQL READ excludes `record_data`.
- MongoDB READ excludes `_id`.
- Both include `record_index`, dataset fields, and `benchmark_updated`.
- However, PostgreSQL returns normalized column names and text values; MongoDB returns original field names and original scalar types.

Fairness conclusion:

- The logical dataset is the same, but physical storage payload is not equivalent.
- PostgreSQL stores a significantly larger payload because of `record_data JSONB`.
- This can affect WRITE directly and READ indirectly through row width/cache behavior.

## 13. Docker and Database Configuration

Docker Compose file:

- `docker-compose.yml`

Services:

| Service | Image/runtime | Evidence |
|---|---|---|
| Backend | `python:3.12-slim` via `backend/Dockerfile` | `backend/Dockerfile:1` |
| Frontend | `node:24-alpine` via `frontend/Dockerfile` | `frontend/Dockerfile:1`, `8`, `16` |
| PostgreSQL | `postgres:16-alpine` | `docker-compose.yml:40-41` |
| MongoDB | `mongo:7` | `docker-compose.yml:57-58` |

Backend dependencies:

- FastAPI `0.124.4`
- Uvicorn `0.38.0`
- psycopg `3.3.2`
- PyMongo `4.15.5`

Evidence: `backend/requirements.txt:1-5`.

Networking:

- No custom network is declared.
- Docker Compose therefore places services on the default project network.
- Backend connects to `postgres:5432` and `mongodb:27017`.
- Evidence: `docker-compose.yml:9-10`.

Volumes:

- PostgreSQL persistent volume: `postgres_data:/var/lib/postgresql/data`.
- MongoDB persistent volume: `mongodb_data:/data/db`.
- Sample datasets are mounted read-only into backend.
- Evidence: `docker-compose.yml:14-15`, `49-50`, `62-63`, `70-72`.

Resource limits:

- No CPU or memory limits are configured.
- No Docker `deploy.resources`, `mem_limit`, or CPU quota settings are present.

Database configuration:

- PostgreSQL uses the default container configuration.
- MongoDB uses the default container configuration.
- No PostgreSQL WAL, fsync, shared buffers, or synchronous commit settings are overridden.
- No MongoDB write concern, journaling, WiredTiger cache, or durability settings are overridden.

Fairness implications:

- Both databases run in the same Compose environment, which is good.
- Persistent volumes can preserve physical state and caches across repeated experiments.
- Docker Desktop/host resource contention can affect both databases.
- PostgreSQL default commit durability and MongoDB default acknowledged write behavior are not explicitly aligned.

## 14. Result Storage and UI Display Audit

Result storage:

- Results are stored in MongoDB collection `benchmark_results`.
- Constant: `MONGO_RESULT_COLLECTION_NAME`, `backend/app/benchmarks.py:25`.
- Storage function: `store_benchmark_result`, `backend/app/benchmarks.py:128-144`.
- Uses `replace_one(..., upsert=True)` by `benchmark_id`, `backend/app/benchmarks.py:135-139`.

Result retrieval:

- List endpoint: `GET /api/benchmarks`, `backend/app/main.py:110-112`.
- Detail endpoint: `GET /api/benchmarks/{benchmark_id}`, `backend/app/main.py:115-117`.
- List service sorts by `created_at` descending and excludes MongoDB storage `_id`, `backend/app/benchmarks.py:92-100`.
- Detail service excludes `_id`, `backend/app/benchmarks.py:108-125`.

API response and stored result consistency:

- `store_benchmark_result` stores `result.model_dump(mode="json")`.
- The same `BenchmarkRunResult` object is returned to the frontend.
- Therefore stored result structure is consistent with the API response.

UI display:

- Latest result summary: `BenchmarkSummary`, `frontend/src/app/page.tsx:628-657`.
- Database panels: `DatabaseBenchmarkPanel`, `frontend/src/app/page.tsx:660-705`.
- Metric comparison table: `MetricComparison`, `frontend/src/app/page.tsx:707-787`.
- Charts: `BenchmarkCharts`, `BarComparisonChart`, `RepeatedRunsChart`, `frontend/src/app/page.tsx:789-949`.
- Previous results table: `PreviousResults`, `frontend/src/app/page.tsx:951-1008`.

Labels:

- Result panels show MongoDB as "NoSQL" and PostgreSQL as "SQL".
- Evidence: `frontend/src/app/page.tsx:641-651`.
- Load summary labels match: `frontend/src/app/page.tsx:611-617`.

Faster-column logic:

- `MetricComparison` defines `lowerIsBetter = true` for:
  - total execution time
  - average latency
  - minimum time
  - maximum time
  - standard deviation
- It defines `lowerIsBetter = false` for throughput.
- Evidence: `frontend/src/app/page.tsx:713-750`.
- `pickFasterDatabase` implements this logic correctly.
- Evidence: `frontend/src/app/page.tsx:1124-1138`.

Charts:

- Total execution time chart uses `result.mongodb.metrics.total_time_ms` and `result.postgresql.metrics.total_time_ms`.
- Throughput chart uses `throughput_ops_sec`.
- Repeated runs chart uses `run_times_ms`.
- Evidence: `frontend/src/app/page.tsx:793-806`, `860-875`.

Formatting:

- Commas and decimal formatting are visual in the UI.
- Backend metrics are already rounded before storage.
- Evidence:
  - Backend rounding: `backend/app/benchmarks.py:169-176`.
  - UI formatting: `frontend/src/app/page.tsx:1104-1121`.

Operation counts:

- The database panels show `result.metrics.operation_count`.
- Evidence: `frontend/src/app/page.tsx:690-693`.
- Previous results table does not show operation count; it shows benchmark id, dataset, operation, total times, and throughput leader.
- Evidence: `frontend/src/app/page.tsx:972-1004`.

## 15. Comparison with Expected Behavior

Observed: WRITE MongoDB much faster than PostgreSQL.

- Implementation explanation: yes.
- Code path:
  - PostgreSQL uses `executemany` and inserts text columns plus `record_data JSONB`, `backend/app/benchmarks.py:279-305`.
  - MongoDB uses `insert_many` and inserts top-level fields without duplicate JSONB, `backend/app/benchmarks.py:417-435`.
- Fairness: partially unfair for database comparison because PostgreSQL has both a slower insert method and a larger payload.
- Thesis interpretation: valid as "current platform implementation result"; not valid as a clean PostgreSQL-vs-MongoDB write-performance conclusion without correcting payload and bulk insert strategy.

Observed: READ MongoDB slightly faster than PostgreSQL.

- Implementation explanation: yes.
- Code path:
  - PostgreSQL selects specific columns and excludes `record_data`, `backend/app/benchmarks.py:316-327`.
  - MongoDB excludes `_id` and materializes projected documents, `backend/app/benchmarks.py:447-455`.
- Fairness: closer than WRITE, but not perfect.
- Bias sources:
  - PostgreSQL table rows still physically include `record_data JSONB`.
  - PostgreSQL values are text columns; MongoDB keeps original scalar types.
  - MongoDB always runs second.
- Thesis interpretation: plausible but should be repeated with warm-up/order control and documented as database plus driver plus Python materialization time.

Observed: UPDATE PostgreSQL faster than MongoDB.

- Implementation explanation: yes.
- Code path:
  - PostgreSQL uses one set-based `UPDATE ... SET benchmark_updated = TRUE`, `backend/app/benchmarks.py:331-339`.
  - MongoDB uses one `update_many` with `$set`, `backend/app/benchmarks.py:459-461`.
- Fairness: mostly fair for the current scope.
- Important correction: MongoDB is not slower because it creates a new field; the field already exists before timing.
- Remaining bias:
  - PostgreSQL typed column vs MongoDB document field update.
  - Commit/write concern defaults are not explicitly aligned.
  - Affected counts are not validated against `record_count`.

Observed: DELETE PostgreSQL much faster than MongoDB.

- Implementation explanation: partly yes.
- Code path:
  - PostgreSQL uses real `DELETE FROM ... WHERE record_index <= %s`, `backend/app/benchmarks.py:343-351`.
  - MongoDB uses real `delete_many({"_id": {"$lte": record_count}})`, `backend/app/benchmarks.py:464-466`.
- Fairness: no truncate/drop mismatch was found. Both delete from reloaded work storage each repetition.
- Bias sources:
  - Durability/write concern defaults are not explicitly aligned.
  - Fixed execution order and no warm-up remain uncontrolled.
  - Affected counts are recorded but not enforced.
- Thesis interpretation: the large PostgreSQL advantage is not caused by an obvious metadata-operation bug. It should still be validated with affected-count checks, alternating order, and documented database defaults.

## 16. Issues and Recommendations

| Severity | Area | Finding | Evidence | Recommendation |
|---|---|---|---|---|
| Critical | Payload fairness | PostgreSQL stores dataset fields twice: normalized `TEXT` columns plus `record_data JSONB`; MongoDB stores top-level fields without an equivalent duplicate full-record field. This biases WRITE and can affect storage/cache behavior for READ. | `backend/app/loaders.py:152-158`, `backend/app/loaders.py:163-179`, `backend/app/loaders.py:195-204`, `backend/app/benchmarks.py:279-297`, `backend/app/benchmarks.py:417-424` | Before thesis experiments, make payloads equivalent. Either remove `record_data JSONB` from benchmark tables or add an equivalent full-record field to MongoDB and include the design choice in the thesis. |
| High | PostgreSQL WRITE method | PostgreSQL WRITE uses `cursor.executemany`, not `COPY`, `execute_values`, or a single multi-row insert, while MongoDB uses `insert_many`. This disadvantages PostgreSQL for bulk writes. | `backend/app/benchmarks.py:301-302`, `backend/app/benchmarks.py:431` | Use a PostgreSQL bulk loading method appropriate for the thesis comparison, preferably `COPY` or a controlled multi-row insert mode, and document the method. |
| High | Execution order | PostgreSQL always completes all repetitions before MongoDB starts. There is no alternating order or warm-up. | `backend/app/benchmarks.py:73-74`, `backend/app/benchmarks.py:193-215`, `backend/app/benchmarks.py:372-387` | Add warm-up runs and alternate/randomize database order. For strongest repeatability, interleave repetitions by database. |
| High | Durability/write settings | PostgreSQL commit timing is included, while MongoDB uses default acknowledged writes without explicit write concern or journaling settings. Durability semantics are not explicitly aligned. | PostgreSQL commit in `backend/app/benchmarks.py:304`, `338`, `350`; MongoDB default client in `backend/app/benchmarks.py:365`; no write concern config in code or `docker-compose.yml` | Document defaults clearly or configure comparable durability settings for both systems. |
| Medium | Affected-count validation | The code records `rowcount`, `modified_count`, and `deleted_count`, but does not assert that each repetition affected `record_count` records. | `backend/app/benchmarks.py:303`, `337`, `349`, `432`, `455`, `461`, `466` | Fail or warn when any repetition affects fewer/more than expected. This is especially important for UPDATE and DELETE. |
| Medium | Dataset identity validation | `dataset_id` selects the in-memory prepared dataset, but source database tables/collections do not store or verify the loaded dataset id. A direct API caller can benchmark against stale loaded database contents if counts happen to fit. | `backend/app/benchmarks.py:69-74`, source counts only at `backend/app/benchmarks.py:190-191`, `369-370`; load target has no dataset id in `backend/app/loaders.py:146-218` | Store loaded dataset metadata in each database or backend state and verify that the loaded source data matches the requested `dataset_id`. |
| Medium | READ type equivalence | PostgreSQL READ returns text column values; MongoDB READ returns original scalar values for JSON datasets. Field names also differ because PostgreSQL normalizes names and MongoDB does not. | PostgreSQL conversion at `backend/app/loaders.py:177`, READ columns at `backend/app/benchmarks.py:316`; Mongo original fields at `backend/app/loaders.py:198-200`, projection at `backend/app/benchmarks.py:447-452` | Decide whether the benchmark compares logical values or physical native types. For thesis fairness, document this clearly or normalize both outputs. |
| Medium | Average latency naming | `average_latency_ms` is total time divided by affected rows/documents. For set-based operations, this is per-record average time, not per-query latency. | `backend/app/benchmarks.py:153`; UI label at `frontend/src/app/page.tsx:682`, `721-724` | Rename to "average time per record" or explain the formula in thesis text and UI. |
| Medium | Persistent Docker volumes | PostgreSQL and MongoDB use persistent volumes. Logical data is reset, but physical storage state and caches can persist across experiments. | `docker-compose.yml:49-50`, `62-63`, `70-72` | For final experiments, document whether volumes were freshly recreated or reused. Consider clearing volumes or restarting containers between controlled experiment batches. |
| Low | Reserved field names | Dataset fields are not checked against internal names such as `record_index`, `_id`, or `benchmark_updated`. A dataset with these names could override internal fields in prepared records or MongoDB documents. | `backend/app/loaders.py:81-87`, `backend/app/loaders.py:197-200`, `backend/app/benchmarks.py:417-422`; field validation only checks empties/duplicates at `backend/app/datasets.py:219-229` | Reject or rename reserved dataset fields during parsing/preparation. |
| Low | Rounded stored metrics | Metrics and individual run times are rounded before storage, not only for display. | `backend/app/benchmarks.py:169-176`, `backend/app/benchmarks.py:488-489` | Store raw values and round only in the UI if more precise statistical analysis is needed. |
| Info | DELETE implementation | Timed DELETE uses real delete operations on both systems. No `TRUNCATE` or collection `drop()` is used inside the measured DELETE. | PostgreSQL `DELETE` at `backend/app/benchmarks.py:343-351`; MongoDB `delete_many` at `backend/app/benchmarks.py:464-466` | Keep this behavior for CRUD DELETE fairness. Add affected-count validation. |
| Info | Index/selected-field parameters | `index_enabled` and `selected_field` are not present in active frontend/backend code. | `BenchmarkRunRequest` at `backend/app/benchmarks.py:30-34`; frontend request at `frontend/src/app/page.tsx:390-395`; source search found no active references in `backend/` or `frontend/` | Keep them out of scope unless the thesis scope explicitly expands to indexing experiments. |

## 17. Suggested Next Steps

### 1. Things that are correct and should stay as-is

- Use the same uploaded/sample dataset as the input source for both databases.
- Validate loaded source record counts before benchmark execution.
- Use separate source storage and work storage:
  - `benchmark_dataset_records`
  - `benchmark_work_records`
- Reset work storage before every repetition.
- Reload work storage before each READ, UPDATE, and DELETE repetition.
- Exclude setup/reload time from operation timing if the thesis defines metrics as operation-only CRUD timing.
- Use real DELETE operations instead of `TRUNCATE` or collection drop.
- Update an existing `benchmark_updated` field for UPDATE rather than changing arbitrary dataset fields.
- Use the same metric formulas for both databases.
- Store and display per-repetition run times.

### 2. Things that should be fixed before thesis experiments

- Make PostgreSQL and MongoDB payloads equivalent.
- Replace PostgreSQL WRITE `executemany` with a clearly justified bulk insert strategy.
- Add warm-up runs.
- Alternate or randomize PostgreSQL/MongoDB execution order.
- Validate affected counts for every repetition.
- Store and verify which dataset is currently loaded into each database.
- Document or align durability/write concern settings.
- Decide whether average latency means per-record average time or per-command latency, then rename or document it.
- Control Docker experiment state: volumes, container restarts, host load, and resource availability.

### 3. Things that are optional improvements

- Store raw unrounded timing values and round only in the UI.
- Add median and percentile metrics for repeated runs.
- Add a small benchmark-run metadata block recording Docker image versions, dataset name, record count, operation, repetitions, and timestamp.
- Add explicit environment notes for thesis reproducibility: host CPU/RAM, Docker Desktop version, OS, and whether containers were restarted.
- Add reserved-field validation for uploaded datasets.
- Add an exportable CSV/JSON result export for thesis tables.

### 4. Things that should not be added because they are out of thesis scope

- `index_enabled` toggles and selected-field/index experiments, unless the thesis scope is formally expanded.
- Join benchmarks.
- Aggregation benchmarks.
- Deeply nested JSON benchmarks.
- Multi-user or concurrent workload testing.
- Distributed database cluster testing.
- Query optimizer tuning as a benchmark feature.
- Database-specific micro-optimizations that make the comparison less understandable for the stated local CRUD thesis scope.
