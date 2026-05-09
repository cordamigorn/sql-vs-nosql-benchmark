# Phase 7 Test Report

**Date:** 2026-05-09  
**Project:** SQL vs NoSQL Benchmark Platform  
**Scope:** Local Docker-based CRUD benchmark validation for PostgreSQL and MongoDB.

## Summary

Phase 7 was completed as an end-to-end validation pass. The local Docker environment was started, backend endpoints were tested, CSV/JSON/sample dataset flows were verified, CRUD benchmarks were executed, frontend result views were smoke-tested, invalid input handling was checked, and thesis-supporting environment details were recorded.

Overall result: **PASS**

## Environment

| Item | Value |
| --- | --- |
| OS | Microsoft Windows 11 Home Single Language 10.0.26200, 64 bit |
| Machine | CASPER BILGISAYAR SISTEMLERI EXCALIBUR G870 |
| CPU | 12th Gen Intel(R) Core(TM) i5-12450H, 8 cores / 12 logical processors |
| Physical memory | 16.91 GB |
| Docker client/server | 29.2.1 / 29.2.1 |
| Docker Desktop runtime | 12 CPUs, 8.19 GB memory |
| PostgreSQL | PostgreSQL 16.13 on x86_64-pc-linux-musl |
| MongoDB | 7.0.32 |
| Node.js / npm | v24.10.0 / 11.8.0 |
| Next.js / React | ^16.2.4 / 19.2.4 |

## Verification Commands

| Check | Result |
| --- | --- |
| `python -m compileall backend\app` | PASS |
| `npm run lint` | PASS |
| `npm run build` | PASS |
| `npm audit --audit-level=moderate` | PASS, 0 vulnerabilities |
| `docker compose up -d --build` | PASS |
| `docker compose ps` | PASS, frontend/backend/PostgreSQL/MongoDB running |

## Backend API Checks

| Endpoint / Flow | Result |
| --- | --- |
| `GET /` | PASS, service metadata returned |
| `GET /health` | PASS |
| `GET /api/health` | PASS |
| `GET /api/health/databases` | PASS, PostgreSQL and MongoDB healthy |
| `GET /api/datasets/samples` | PASS, 6 sample options returned |
| `POST /api/datasets/sample` | PASS |
| `POST /api/datasets/load` | PASS, PostgreSQL and MongoDB counts matched |
| `POST /api/benchmarks/run` | PASS for WRITE, READ, UPDATE, DELETE |
| `GET /api/benchmarks` | PASS, previous results returned |
| `GET /api/benchmarks/{benchmark_id}` | PASS, requested benchmark detail returned |

## Dataset Flow Checks

| Flow | Dataset | Result |
| --- | --- | --- |
| CSV upload + load + READ benchmark | `sample_orders_1k.csv`, 1,000 records | PASS |
| JSON upload + load + READ benchmark | `sample_orders_1k.json`, 1,000 records | PASS |
| Sample dataset + load + CRUD benchmarks | `sample_orders_1k.csv`, 1,000 records | PASS |

Database load verification after sample load:

| Database | Count |
| --- | ---: |
| PostgreSQL `benchmark_dataset_records` | 1,000 |
| MongoDB `benchmark_dataset_records` | 1,000 |

## Invalid Input Checks

| Case | Expected | Result |
| --- | --- | --- |
| Invalid CSV with inconsistent row length | HTTP 400 | PASS, `CSV row 2 has 1 columns, but the header has 2 columns.` |
| Invalid JSON object instead of array | HTTP 400 | PASS, `JSON dataset must be an array of objects.` |

## CRUD Benchmark Results

Dataset: `sample_orders_1k.csv`  
Record count: 1,000  
Repetitions: 3  
Index and selected-field options were removed from final scope, so all operations use the same dataset size and repetition count.

| Operation | PostgreSQL total | MongoDB total | PostgreSQL throughput | MongoDB throughput | Faster by total time |
| --- | ---: | ---: | ---: | ---: | --- |
| WRITE | 31.4617 ms | 158.5341 ms | 95,354.0336 ops/sec | 18,923.3736 ops/sec | PostgreSQL |
| READ | 6.5519 ms | 6.2374 ms | 457,882.4463 ops/sec | 480,969.6348 ops/sec | MongoDB |
| UPDATE | 50.8522 ms | 34.8749 ms | 58,994.4978 ops/sec | 86,021.7520 ops/sec | MongoDB |
| DELETE | 10.4090 ms | 14.6413 ms | 288,212.1241 ops/sec | 204,899.8381 ops/sec | PostgreSQL |

Detailed metrics were present for both databases:

- total execution time
- average latency
- throughput
- minimum time
- maximum time
- standard deviation
- operation count

## Frontend Checks

Browser smoke testing verified:

| UI Area | Result |
| --- | --- |
| Main dashboard loads | PASS |
| Dataset Setup section renders | PASS |
| Benchmark Configuration section renders | PASS |
| MongoDB / NoSQL and PostgreSQL / SQL lanes render | PASS |
| Sample dataset flow can be executed from UI | PASS |
| Load Dataset to Databases can be executed from UI | PASS |
| Run Benchmark can be executed from UI | PASS |
| Result cards render after benchmark | PASS |
| Comparison table renders | PASS |
| Total execution time chart renders | PASS |
| Throughput chart renders | PASS |
| Repeated runs chart renders | PASS |
| Previous results table renders | PASS |
| Removed `Selected field` and `Enable index` controls are absent | PASS |
| Framework error overlay | PASS, none detected |

## Result Storage

Benchmark history API returned stored results, and benchmark detail lookup returned the requested benchmark ID. MongoDB `benchmark_results` contained stored result records after the test run.

## Notes for Thesis Use

- These results are local measurements from one machine and one Docker Desktop configuration.
- The measured values represent database operation timing inside the benchmark runners, not full end-to-end UI wait time.
- Results may vary across repeated runs due to Docker runtime state, OS scheduling, and hardware load.
- The final scope now focuses on basic CRUD operations with the same dataset, same record count, and same repetition count.

