from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.benchmarks import (
    BenchmarkRunRequest,
    BenchmarkRunResult,
    get_benchmark_result,
    list_benchmark_results,
    run_benchmark,
)
from app.config import settings
from app.database import check_mongodb, check_postgres
from app.datasets import (
    DatasetMetadata,
    SampleDatasetOption,
    SampleDatasetRequest,
    get_dataset,
    list_sample_datasets,
    load_sample_dataset,
    parse_uploaded_dataset,
    store_dataset,
)
from app.loaders import DatasetLoadRequest, DatasetLoadResult, load_dataset_to_databases

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for the PostgreSQL and MongoDB benchmarking platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "database_health": "/api/health/databases",
    }


@app.get("/api/health", tags=["health"])
def api_health() -> dict[str, str]:
    return health()


@app.get("/api/health/databases", tags=["health"])
def database_health() -> dict[str, object]:
    checks = [check_postgres(), check_mongodb()]

    return {
        "status": "ok" if all(check.ok for check in checks) else "degraded",
        "databases": {
            check.service: {
                "ok": check.ok,
                "message": check.message,
            }
            for check in checks
        },
    }


@app.post("/api/datasets/upload", response_model=DatasetMetadata, tags=["datasets"])
async def upload_dataset(file: UploadFile) -> DatasetMetadata:
    records, fields, file_type = await parse_uploaded_dataset(file)

    return store_dataset(
        dataset_name=file.filename or "uploaded_dataset",
        records=records,
        fields=fields,
        source="upload",
        file_type=file_type,
    )


@app.get("/api/datasets/samples", response_model=list[SampleDatasetOption], tags=["datasets"])
def get_sample_datasets() -> list[SampleDatasetOption]:
    return list_sample_datasets()


@app.post("/api/datasets/sample", response_model=DatasetMetadata, tags=["datasets"])
def use_sample_dataset(request: SampleDatasetRequest | None = None) -> DatasetMetadata:
    return load_sample_dataset(request.sample_id if request else None)


@app.post("/api/datasets/load", response_model=DatasetLoadResult, tags=["datasets"])
def load_dataset(request: DatasetLoadRequest) -> DatasetLoadResult:
    dataset = get_dataset(request.dataset_id)
    return load_dataset_to_databases(dataset)


@app.post("/api/benchmarks/run", response_model=BenchmarkRunResult, tags=["benchmarks"])
def run_benchmark_endpoint(request: BenchmarkRunRequest) -> BenchmarkRunResult:
    return run_benchmark(request)


@app.get("/api/benchmarks", response_model=list[BenchmarkRunResult], tags=["benchmarks"])
def get_benchmark_results_endpoint() -> list[BenchmarkRunResult]:
    return list_benchmark_results()


@app.get("/api/benchmarks/{benchmark_id}", response_model=BenchmarkRunResult, tags=["benchmarks"])
def get_benchmark_result_endpoint(benchmark_id: str) -> BenchmarkRunResult:
    return get_benchmark_result(benchmark_id)
