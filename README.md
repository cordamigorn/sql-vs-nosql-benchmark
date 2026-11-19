# SQL vs NoSQL Benchmark Platform

> **Bachelor of Engineering thesis project – Computer Science, Vistula University (Warsaw, 2026)**

A web-based tool that compares **PostgreSQL** and **MongoDB** CRUD performance on the same dataset. Upload any flat CSV or JSON file, load it into both databases, run repeated WRITE / READ / UPDATE / DELETE tests, and compare the results side by side in tables and charts.

## Why this project

Choosing between a relational and a document database is a common design decision, but most comparisons use synthetic data. This platform lets you benchmark **your own dataset** under identical conditions, so the decision is based on measured numbers.

## What it measures

For each operation and each database, over 1–20 repetitions:

| Metric | Meaning |
|---|---|
| Average latency (ms) | Average time per record operation |
| Throughput (ops/sec) | Operations completed per second |
| Min / Max time (ms) | Fastest and slowest repetition |

Every run is stored, so earlier results can be listed and compared again.

![Benchmark results dashboard](assets/benchmark-results-ui.png)

## Key findings

Tested with 10K, 100K, 500K and 1M records, 5 measured repetitions + 1 warm-up run per scenario.

**Total execution time at 1,000,000 records** (lower is better):

| Operation | MongoDB | PostgreSQL | Faster |
|---|---:|---:|---|
| WRITE | 29,683 ms | 38,852 ms | **MongoDB** (~1.3×) |
| READ | 14,587 ms | 13,991 ms | PostgreSQL (~4%, near tie) |
| UPDATE | 25,838 ms | 17,109 ms | **PostgreSQL** (~1.5×) |
| DELETE | 16,152 ms | 2,441 ms | **PostgreSQL** (~6.6×) |

- **WRITE:** MongoDB was faster at every dataset size.
- **READ:** results were close; PostgreSQL won at 10K, 500K and 1M, MongoDB at 100K.
- **UPDATE & DELETE:** PostgreSQL was faster at every size, with the biggest gap on DELETE.
- **Conclusion:** neither database is "better" overall. The right choice depends on the workload: write-heavy workloads favour MongoDB, update/delete-heavy workloads favour PostgreSQL.

<sub>Test machine: Intel Core i5-12450H, 16 GB RAM, NVMe SSD, Windows 11, Docker Compose (postgres:16-alpine, mongo:7). Single machine, no concurrency.</sub>

## Tech stack

| Layer | Technology |
|---|---|
| Databases | PostgreSQL 16, MongoDB 7 |
| Backend | Python, FastAPI, psycopg 3, PyMongo |
| Frontend | Next.js, TypeScript |
| Infrastructure | Docker Compose (4 services) |

## How it works

![Architecture](assets/architecture.png)

1. **Dataset input:** CSV/JSON is validated (header row, flat objects, consistent fields).
2. **Load:** the same records are loaded into a PostgreSQL table and a MongoDB collection.
3. **Benchmark:** each repetition runs on a fresh work table/collection, so runs don't affect each other; affected-row counts are validated after every operation.
4. **Results:** metrics are calculated per database and saved to MongoDB; the UI shows them as a table and charts.

---

# Technical guide

The app has four services:

- `frontend`: Next.js UI at `http://localhost:3000`
- `backend`: FastAPI API at `http://localhost:8000`
- `postgres`: PostgreSQL target database
- `mongodb`: MongoDB target database and benchmark result store

## Prerequisites

- Docker Desktop with Docker Compose
- Node.js 24+ for frontend local development
- Python 3.12+ for backend local development

Docker Compose is the easiest way to run the full project because it starts the API, UI, PostgreSQL, and MongoDB together.

## Repository Notes

- `docs/` is ignored by Git and can be used for local thesis notes, reports, and planning files.
- `sample_datasets/` is also ignored by Git because benchmark datasets can be large.
- The backend reads local sample files from `sample_datasets/`. If that folder is empty, use the upload flow in the UI or add local `.csv` / `.json` files there.

## Quick Start With Docker

From the repository root:

```powershell
docker compose up --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/health`

Stop the stack:

```powershell
docker compose down
```

Stop the stack and delete database volumes:

```powershell
docker compose down -v
```

Use `down -v` when you want a clean PostgreSQL and MongoDB state.

## Manual Local Development

Start only the databases:

```powershell
docker compose up -d postgres mongodb
```

### Backend

In a new PowerShell terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:DATABASE_URL = "postgresql://benchmark:benchmark@localhost:5432/benchmark"
$env:MONGO_URL = "mongodb://localhost:27017/benchmark"
$env:CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
$env:SAMPLE_DATASET_DIR = "..\sample_datasets"

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check the API:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/health/databases
```

### Frontend

In another PowerShell terminal:

```powershell
cd frontend
npm ci
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000"
npm run dev
```

Open `http://localhost:3000`.

## How To Use The App

1. Start the stack with Docker Compose or run the backend/frontend manually.
2. Open `http://localhost:3000`.
3. Select a sample dataset or upload a flat `.csv` / `.json` file.
4. Click `Load Dataset to Databases`.
5. Choose an operation: `WRITE`, `READ`, `UPDATE`, or `DELETE`.
6. Choose repetitions between `1` and `20`.
7. Click `Run Benchmark`.
8. Compare MongoDB and PostgreSQL metrics in the results table and charts.

Dataset rules:

- CSV files must include a header row.
- JSON files must be an array of flat objects.
- Nested JSON objects and arrays are rejected.
- Every JSON object must use the same fields as the first object.

## API Smoke Tests

Run these after the backend, PostgreSQL, and MongoDB are healthy.

Health checks:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/health/databases
```

List sample datasets:

```powershell
Invoke-RestMethod http://localhost:8000/api/datasets/samples
```

Load a sample dataset into backend memory:

```powershell
$dataset = Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/datasets/sample `
  -ContentType "application/json" `
  -Body '{"sample_id":"sample_orders_1k_csv"}'

$dataset
```

Load that dataset into PostgreSQL and MongoDB:

```powershell
$loadBody = @{ dataset_id = $dataset.dataset_id } | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/datasets/load `
  -ContentType "application/json" `
  -Body $loadBody
```

Run a benchmark:

```powershell
$benchmarkBody = @{
  dataset_id = $dataset.dataset_id
  operation = "READ"
  record_count = 1000
  repetitions = 3
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/benchmarks/run `
  -ContentType "application/json" `
  -Body $benchmarkBody
```

Upload a CSV or JSON file instead of using a sample:

```powershell
curl.exe -F "file=@sample_datasets/sample_orders_1k.csv" http://localhost:8000/api/datasets/upload
```

## Frontend Checks

From `frontend/`:

```powershell
npm run lint
npm run build
```

## Backend Checks

There is currently no automated pytest suite in the repository. Use the API smoke tests above for backend verification.

For import and dependency verification:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m compileall app
```

## Useful Environment Variables

Backend:

- `APP_NAME`: API title shown in OpenAPI docs
- `DATABASE_URL`: PostgreSQL connection string
- `MONGO_URL`: MongoDB connection string
- `CORS_ORIGINS`: comma-separated allowed frontend origins
- `SAMPLE_DATASET_DIR`: folder used for sample `.csv` and `.json` files

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`: browser-visible backend URL

## Main Endpoints

- `GET /health`
- `GET /api/health/databases`
- `GET /api/datasets/samples`
- `POST /api/datasets/sample`
- `POST /api/datasets/upload`
- `POST /api/datasets/load`
- `POST /api/benchmarks/run`
- `GET /api/benchmarks`
- `GET /api/benchmarks/{benchmark_id}`
