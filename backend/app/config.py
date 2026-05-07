import os


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    app_name: str = os.getenv("APP_NAME", "SQL vs NoSQL Benchmark API")
    sample_dataset_dir: str = os.getenv("SAMPLE_DATASET_DIR", "sample_datasets")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://benchmark:benchmark@localhost:5432/benchmark",
    )
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017/benchmark")
    cors_origins: list[str] = _split_csv(
        os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        )
    )


settings = Settings()
