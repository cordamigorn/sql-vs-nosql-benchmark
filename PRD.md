# Product Requirements Document

## Design and Implementation of a Web-Based Benchmarking Platform for SQL and NoSQL Databases

**Version:** 1.0  
**Project type:** Engineering thesis project / web-based benchmarking platform  
**Target databases:** PostgreSQL and MongoDB  
**Target environment:** Local Docker-based development environment  
**Deployment scope:** Local single-user usage; public deployment is not required

---

## 1. Product Overview

This project is a web-based benchmarking platform for comparing SQL and NoSQL database performance under controlled and repeatable test conditions.

The platform allows a user to upload a CSV or JSON dataset, load the same dataset into PostgreSQL and MongoDB, execute selected benchmark operations, and compare the results through summary cards, tables, and charts.

The purpose of the system is to make database performance testing more accessible, repeatable, and understandable without requiring manual database setup, command-line benchmarking tools, or custom scripts.

---

## 2. Problem Statement

Developers, students, and researchers often need to compare SQL and NoSQL databases before selecting a database technology for an application. In practice, database benchmarking is frequently performed through manual scripts, command-line tools, or custom local environments.

This creates several problems:

- Benchmark setup is time-consuming.
- Results may differ across environments.
- Manual testing reduces repeatability.
- Users need technical knowledge to configure databases and run tests.
- Results are often not presented in a clear visual format.

This project addresses these issues by providing a web-based system that automates dataset loading, benchmark execution, metric calculation, result storage, and visual comparison for PostgreSQL and MongoDB.

---

## 3. Project Goals

The main goal of this project is to design and implement a local web-based benchmarking platform that compares PostgreSQL and MongoDB under the same test conditions.

Specific goals:

- Allow users to upload CSV and JSON datasets.
- Provide a built-in sample dataset for repeatable thesis experiments.
- Load the same dataset into PostgreSQL and MongoDB.
- Execute CRUD benchmark operations.
- Measure database performance metrics.
- Display PostgreSQL and MongoDB results side by side.
- Visualize benchmark results using charts.
- Store benchmark results for later review.
- Run the complete system in a controlled Docker environment.

---

## 4. Non-Goals

The following features are outside the scope of the first version:

- Multi-user public platform
- User authentication
- Cloud deployment
- Distributed database testing
- Multi-client concurrency testing
- Real-time load testing
- Complex joins
- Advanced aggregation benchmarks
- Support for databases other than PostgreSQL and MongoDB
- Deeply nested JSON benchmarking
- Production-scale performance testing

These items may be discussed as possible future work in the thesis.

---

## 5. Target Users

The platform is designed for:

- The thesis author or researcher conducting controlled experiments
- Students studying database performance
- Developers comparing SQL and NoSQL databases
- Users who want a simple interface for basic database benchmarking

Because this is a thesis project, the system is intended primarily for controlled local usage rather than public deployment.

---

## 6. User Flow

1. The user opens the web application.
2. The user selects a dataset source:
   - Upload CSV file
   - Upload JSON file
   - Use sample dataset
3. The system validates the selected dataset.
4. The system loads the same dataset into PostgreSQL and MongoDB.
5. The user selects a benchmark operation:
   - WRITE
   - READ
   - UPDATE
   - DELETE
6. The user configures benchmark parameters:
   - Record count
   - Number of repetitions
7. The user clicks **Run Benchmark**.
8. The backend executes the selected benchmark on PostgreSQL and MongoDB.
9. The system collects performance results.
10. The frontend displays the results using:
    - Summary cards
    - Comparison table
    - Charts
11. The user can review previous benchmark results.

---

## 7. Core Features

### 7.1 Dataset Upload

The system shall allow the user to upload datasets in the following formats:

- CSV
- JSON

#### CSV Requirements

Uploaded CSV files shall:

- Contain a header row.
- Contain flat tabular data.
- Use consistent columns across all rows.
- Be convertible into a PostgreSQL table and MongoDB collection.

#### JSON Requirements

Uploaded JSON files shall:

- Contain an array of objects.
- Use a flat object structure.
- Avoid deeply nested fields in the first version.

Example JSON format:

```json
[
  {
    "id": 1,
    "customer_id": 101,
    "category": "electronics",
    "price": 299.99,
    "status": "completed"
  }
]
```

### 7.2 Sample Dataset

The system shall include a built-in sample dataset for repeatable thesis experiments. This allows benchmark results to be reproduced without depending only on user-uploaded files.

The sample dataset should contain realistic structured records, such as orders, products, customers, transactions, categories, prices, dates, and statuses.

Recommended sample dataset structure:

| Field name | Example type |
| --- | --- |
| `id` | Integer |
| `customer_id` | Integer |
| `product_id` | Integer |
| `category` | String |
| `price` | Decimal |
| `quantity` | Integer |
| `status` | String |
| `created_at` | Date/time |

---

## 8. Benchmark Operations

The platform shall support four CRUD benchmark operations.

### 8.1 WRITE Benchmark

The WRITE benchmark measures how long it takes to insert records into PostgreSQL and MongoDB.

Operation logic:

1. Select `N` records from the dataset.
2. Insert the records into PostgreSQL.
3. Insert the same records into MongoDB.
4. Measure execution time and latency.
5. Calculate throughput.

Example:

- Insert 1,000 records into PostgreSQL.
- Insert the same 1,000 records into MongoDB.
- Compare total execution time and operations per second.

### 8.2 READ Benchmark

The READ benchmark measures how long it takes to retrieve records from PostgreSQL and MongoDB.

The first version shall support simple read operations over the selected dataset records.

Example:

- Read 1,000 records from PostgreSQL.
- Read the same 1,000 records from MongoDB.
- Compare query latency and execution time.

### 8.3 UPDATE Benchmark

The UPDATE benchmark measures how long it takes to update existing records.

Operation logic:

1. Select `N` records.
2. Update one or more fields.
3. Run the same update logic in PostgreSQL and MongoDB.
4. Measure execution time and latency.

Example:

- Update 1,000 benchmark records in PostgreSQL.
- Update the same 1,000 benchmark records in MongoDB.
- Compare PostgreSQL and MongoDB update performance.

### 8.4 DELETE Benchmark

The DELETE benchmark measures how long it takes to delete records.

Operation logic:

1. Select `N` records.
2. Delete selected records from PostgreSQL.
3. Delete the same records from MongoDB.
4. Measure execution time and throughput.

Example:

- Delete 1,000 benchmark records from PostgreSQL.
- Delete the same 1,000 benchmark records from MongoDB.
- Compare deletion performance.

---

## 9. Benchmark Parameters

The user shall be able to configure benchmark parameters before running a test.

### Required Parameters

| Parameter | Description |
| --- | --- |
| Dataset source | Uploaded CSV, uploaded JSON, or sample dataset |
| Operation type | WRITE, READ, UPDATE, or DELETE |
| Record count | Number of records used in the benchmark |
| Repetitions | Number of times the benchmark is repeated |

### Recommended Default Values

| Parameter | Default value |
| --- | --- |
| Dataset | Sample dataset |
| Record count | 1,000 |
| Repetitions | 5 |

---

## 10. Performance Metrics

The platform shall collect and display the following benchmark metrics.

### 10.1 Total Execution Time

The total time required to complete the selected benchmark operation.

Example:

- PostgreSQL WRITE total time: `120 ms`
- MongoDB WRITE total time: `85 ms`

### 10.2 Average Latency

The average time required to complete a single operation or query.

```text
average_latency = total_execution_time / number_of_operations
```

### 10.3 Throughput

The number of operations completed per second.

```text
throughput = number_of_operations / total_execution_time_in_seconds
```

### 10.4 Minimum Time

The fastest execution time among repeated benchmark runs.

### 10.5 Maximum Time

The slowest execution time among repeated benchmark runs.

### 10.6 Standard Deviation

Standard deviation shows how stable or unstable the benchmark results are across repeated runs.

### 10.7 Optional p95 Latency

The 95th percentile latency may be added if implementation time allows. This metric shows the latency value under which 95% of operations were completed.

---

## 11. Result Display Requirements

The frontend shall present benchmark results clearly and consistently.

### 11.1 Summary Cards

The system shall show separate result cards for PostgreSQL and MongoDB.

Each card should display:

- Total execution time
- Average latency
- Throughput
- Minimum time
- Maximum time
- Standard deviation

### 11.2 Comparison Table

The system shall show PostgreSQL and MongoDB results side by side.

Example:

| Metric | PostgreSQL | MongoDB | Faster |
| --- | ---: | ---: | --- |
| Total time | 120 ms | 85 ms | MongoDB |
| Average latency | 0.12 ms | 0.085 ms | MongoDB |
| Throughput | 8,333 ops/sec | 11,764 ops/sec | MongoDB |

### 11.3 Charts

The system shall include charts such as:

- Bar chart for total execution time
- Bar chart for throughput
- Line chart for repeated runs
- Comparison chart for PostgreSQL vs MongoDB

---

## 12. System Architecture

The system shall consist of the following components.

### 12.1 Frontend

The frontend is responsible for:

- Dataset upload interface
- Benchmark configuration form
- Run benchmark action
- Result visualization
- Previous results display

Recommended technologies:

- React or Next.js
- Chart.js or Recharts

### 12.2 Backend

The backend is responsible for:

- Receiving uploaded datasets
- Validating CSV and JSON files
- Loading data into PostgreSQL and MongoDB
- Executing benchmark operations
- Measuring performance metrics
- Returning results to the frontend
- Storing benchmark results

Recommended technologies:

- FastAPI
- Python

### 12.3 PostgreSQL Database

PostgreSQL is responsible for:

- Storing the relational version of the dataset
- Executing SQL benchmark operations
- Storing benchmark results if PostgreSQL is selected as the result store

### 12.4 MongoDB Database

MongoDB is responsible for:

- Storing the document-based version of the dataset
- Executing NoSQL benchmark operations
- Storing benchmark results if MongoDB is selected as the result store

### 12.5 Result Storage

The system shall store benchmark results for later review.

Result storage and previous result review are part of the final project scope. In the MVP, the system may initially display only the latest benchmark result.

Stored result data may include:

- Benchmark ID
- Dataset name
- Operation type
- Record count
- Repetitions
- PostgreSQL metrics
- MongoDB metrics
- Timestamp

---

## 13. Docker Environment

The system shall use Docker Compose to run the required services in a controlled local environment.

Recommended services:

```yaml
services:
  frontend:
    description: React or Next.js frontend

  backend:
    description: FastAPI backend and benchmark engine

  postgres:
    description: PostgreSQL database

  mongodb:
    description: MongoDB database
```

Optional services:

```yaml
services:
  pgadmin:
    description: PostgreSQL visual management tool

  mongo-express:
    description: MongoDB visual management tool
```

Docker is used to:

- Keep PostgreSQL and MongoDB in the same controlled environment.
- Simplify setup.
- Make experiments easier to reproduce.
- Avoid manual database installation.
- Keep database versions fixed.

---

## 14. Functional Requirements

| ID | Requirement |
| --- | --- |
| FR-1 | The system shall allow the user to upload CSV and JSON files. |
| FR-2 | The system shall validate uploaded datasets before loading them into the databases. |
| FR-3 | The system shall allow the user to run benchmarks using a built-in sample dataset. |
| FR-4 | The system shall load the same dataset into PostgreSQL and MongoDB. |
| FR-5 | The system shall allow the user to select one benchmark operation: WRITE, READ, UPDATE, or DELETE. |
| FR-6 | The system shall allow the user to select record count and repetitions for each benchmark run. |
| FR-7 | The system shall execute the selected benchmark operation on PostgreSQL and MongoDB. |
| FR-8 | The system shall collect performance metrics from both databases. |
| FR-9 | The system shall display benchmark results using tables and charts. |
| FR-10 | The system shall store benchmark results for later review. |
| FR-11 | The system shall allow the user to view previous benchmark results. |
| FR-12 | The system shall show clear error messages for invalid files, database connection errors, and failed benchmark runs. |

---

## 15. Non-Functional Requirements

| ID | Requirement | Description |
| --- | --- | --- |
| NFR-1 | Usability | The user interface should be simple and easy to understand. The user should be able to run a benchmark without command-line tools. |
| NFR-2 | Repeatability | The same dataset and benchmark parameters should produce comparable results across repeated runs. |
| NFR-3 | Reliability | The system should handle invalid files and database errors without crashing. |
| NFR-4 | Portability | The system should run locally using Docker Compose. |
| NFR-5 | Performance | The platform should execute benchmark operations efficiently and return results in a reasonable time. |
| NFR-6 | Maintainability | The codebase should separate frontend, backend, benchmark logic, and database access logic. |
| NFR-7 | Security | The system should validate uploaded files and avoid executing unsafe user input. Advanced authentication is not required for the first version because the system is local and single-user. |

---

## 16. System Constraints

The system has the following constraints:

- Only PostgreSQL and MongoDB are included.
- Only CSV and flat JSON datasets are supported.
- Only CRUD benchmark operations are included.
- The system runs locally.
- The system is designed for single-user usage.
- Public deployment is not required.
- Concurrent multi-user workloads are not included.
- Distributed or cloud database testing is not included.
- Results are specific to the selected dataset, hardware, database versions, and test configuration.

---

## 17. Data Model

### 17.1 Uploaded Dataset Model

The system should internally represent uploaded data as a list of records with dataset metadata.

Example:

```json
{
  "dataset_id": "sample_orders",
  "dataset_name": "Sample Orders Dataset",
  "record_count": 10000,
  "fields": ["id", "customer_id", "category", "price", "status", "created_at"]
}
```

### 17.2 Benchmark Result Model

Example:

```json
{
  "benchmark_id": "bench_001",
  "dataset_name": "sample_orders",
  "operation": "READ",
  "record_count": 1000,
  "repetitions": 5,
  "postgresql": {
    "total_time_ms": 120,
    "average_latency_ms": 0.12,
    "throughput_ops_sec": 8333,
    "min_time_ms": 110,
    "max_time_ms": 135,
    "std_dev_ms": 8.2
  },
  "mongodb": {
    "total_time_ms": 85,
    "average_latency_ms": 0.085,
    "throughput_ops_sec": 11764,
    "min_time_ms": 80,
    "max_time_ms": 93,
    "std_dev_ms": 4.7
  },
  "created_at": "2026-05-04T12:00:00"
}
```

---

## 18. API Requirements

### 18.1 Upload Dataset

```http
POST /api/datasets/upload
```

Purpose: upload a CSV or JSON dataset.

Example response:

```json
{
  "dataset_id": "dataset_001",
  "dataset_name": "orders.csv",
  "record_count": 10000,
  "fields": ["id", "customer_id", "price", "status"]
}
```

### 18.2 Use Sample Dataset

```http
POST /api/datasets/sample
```

Purpose: load the built-in sample dataset.

### 18.3 Run Benchmark

```http
POST /api/benchmarks/run
```

Example request:

```json
{
  "dataset_id": "dataset_001",
  "operation": "READ",
  "record_count": 1000,
  "repetitions": 5
}
```

Example response:

```json
{
  "benchmark_id": "bench_001",
  "postgresql": {
    "total_time_ms": 120,
    "average_latency_ms": 0.12,
    "throughput_ops_sec": 8333
  },
  "mongodb": {
    "total_time_ms": 85,
    "average_latency_ms": 0.085,
    "throughput_ops_sec": 11764
  }
}
```

### 18.4 Get Benchmark Results

```http
GET /api/benchmarks
```

Purpose: return previous benchmark results.

### 18.5 Get Benchmark Detail

```http
GET /api/benchmarks/{benchmark_id}
```

Purpose: return detailed information for a selected benchmark.

---

## 19. Benchmark Execution Logic

For each benchmark run, the backend shall follow this general process:

1. Receive benchmark configuration from the frontend.
2. Prepare PostgreSQL and MongoDB test data.
3. Clear previous temporary benchmark data if required.
4. Execute the selected operation on PostgreSQL.
5. Measure PostgreSQL performance.
6. Execute the selected operation on MongoDB.
7. Measure MongoDB performance.
8. Repeat the test according to the configured repetition count.
9. Calculate final metrics.
10. Store the benchmark result.
11. Return the result to the frontend.

---

## 20. Fairness Rules

To keep the comparison fair:

- Both databases must use the same dataset.
- Both databases must use the same number of records.
- Both databases must run inside the same Docker environment.
- The same operation type must be executed on both databases.
- Benchmark parameters must be identical.
- Tests must be repeated multiple times.
- Results must be calculated using the same metric formulas.
- Database versions should be documented.
- Hardware specifications should be documented in the thesis.

---

## 21. UI Requirements

### 21.1 Main Dashboard

The main dashboard shall include:

- Project title
- Dataset upload section
- Sample dataset button
- Benchmark operation selector
- Benchmark parameter form
- Run benchmark button
- PostgreSQL result card
- MongoDB result card
- Comparison chart
- Previous benchmark results table

### 21.2 Dataset Upload Section

The upload section shall include:

- File input
- Accepted file types
- Validation message
- Uploaded dataset summary

### 21.3 Benchmark Configuration Section

The benchmark form shall include:

- Operation selector
- Record count input
- Repetition input

### 21.4 Results Section

The results section shall include:

- PostgreSQL metrics
- MongoDB metrics
- Faster database indicator
- Comparison table
- Charts

---

## 22. Acceptance Criteria

The project is considered complete when:

- The frontend can upload CSV and JSON datasets.
- The system can use a built-in sample dataset.
- The backend can load the same dataset into PostgreSQL and MongoDB.
- The user can select WRITE, READ, UPDATE, or DELETE benchmarks.
- The backend can execute the selected operation on both databases.
- The system can measure execution time, average latency, and throughput.
- The system can display results in tables and charts.
- The system can store benchmark results.
- The application can run locally using Docker Compose.
- The project scope remains limited to single-user CRUD benchmarking.

---

## 23. MVP Scope

The minimum viable product shall include:

- CSV upload
- Sample dataset
- PostgreSQL connection
- MongoDB connection
- WRITE benchmark
- READ benchmark
- Total execution time
- Average latency
- Throughput
- Result cards
- Comparison table
- Docker Compose setup

After the MVP, the following features may be added:

- JSON upload
- UPDATE benchmark
- DELETE benchmark
- Result history
- Charts
- Standard deviation
- Export results as CSV or PDF

### Implementation Scope Warning

Only the MVP and core thesis scope should be implemented first. Features listed under Non-Goals, Future Work, or after-MVP scope must not be implemented unless the core system is already complete.

---

## 24. Suggested Development Milestones

### Milestone 1: Project Setup

- Create frontend project.
- Create backend project.
- Create Docker Compose file.
- Add PostgreSQL and MongoDB containers.
- Test database connections.

### Milestone 2: Dataset Handling

- Implement CSV upload.
- Implement JSON upload.
- Implement sample dataset.
- Validate dataset structure.
- Load data into PostgreSQL and MongoDB.

### Milestone 3: Benchmark Engine

- Implement WRITE benchmark.
- Implement READ benchmark.
- Implement UPDATE benchmark.
- Implement DELETE benchmark.
- Add timing logic.
- Add repetition logic.

### Milestone 4: Metrics and Result Storage

- Calculate total execution time.
- Calculate average latency.
- Calculate throughput.
- Calculate minimum and maximum time.
- Calculate standard deviation.
- Store benchmark results.

### Milestone 5: Frontend Dashboard

- Build upload UI.
- Build benchmark configuration UI.
- Build result cards.
- Build comparison table.
- Add charts.

### Milestone 6: Testing and Thesis Experiment

- Run tests with the sample dataset.
- Record database versions.
- Record hardware specifications.
- Collect final thesis results.
- Create tables and charts for the thesis results chapter.

---

## 25. Risks and Mitigations

| Risk | Description | Mitigation |
| --- | --- | --- |
| R-1 | Uploaded datasets may have inconsistent structure. | Support only flat CSV and flat JSON. Validate files before database loading. |
| R-2 | PostgreSQL and MongoDB use different data models. | Use flat structured data and store equivalent fields in both databases. |
| R-3 | Benchmark results may vary between runs. | Repeat each benchmark multiple times and report average, minimum, maximum, and standard deviation. |
| R-4 | Project scope may become too large. | Keep the first version limited to CRUD operations. Exclude concurrency, cloud testing, joins, and aggregation. |
| R-5 | Hardware affects benchmark results. | Run both databases on the same machine. Document hardware and software versions. Use Docker for controlled setup. |

---

## 26. Future Work

Possible future improvements include:

- Multi-user concurrency testing
- Cloud deployment
- Support for more databases
- Advanced aggregation benchmarks
- Join-based benchmark scenarios
- Larger datasets
- Real-time monitoring
- CPU and memory usage measurement
- Exportable PDF benchmark reports
- Authentication and user accounts
- Public web deployment

---

## 27. Final Scope Statement

The final version of this project will be a local, single-user, web-based benchmarking platform that compares PostgreSQL and MongoDB using CSV or JSON datasets. The platform will focus on CRUD benchmark operations and will measure execution time, latency, and throughput under the same controlled Docker-based environment.
