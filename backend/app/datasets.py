from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings


Record = dict[str, Any]


class DatasetMetadata(BaseModel):
    dataset_id: str
    dataset_name: str
    record_count: int
    fields: list[str]
    source: str
    file_type: str


class SampleDatasetOption(BaseModel):
    sample_id: str
    dataset_name: str
    record_count: int
    fields: list[str]
    file_type: str


class SampleDatasetRequest(BaseModel):
    sample_id: str | None = None


@dataclass
class Dataset:
    metadata: DatasetMetadata
    records: list[Record]


_datasets: dict[str, Dataset] = {}


def get_dataset(dataset_id: str) -> Dataset:
    dataset = _datasets.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' was not found.")

    return dataset


def store_dataset(
    *,
    dataset_name: str,
    records: list[Record],
    fields: list[str],
    source: str,
    file_type: str,
) -> DatasetMetadata:
    metadata = DatasetMetadata(
        dataset_id=f"dataset_{uuid4().hex[:12]}",
        dataset_name=dataset_name,
        record_count=len(records),
        fields=fields,
        source=source,
        file_type=file_type,
    )
    _datasets[metadata.dataset_id] = Dataset(metadata=metadata, records=records)
    return metadata


async def parse_uploaded_dataset(file: UploadFile) -> tuple[list[Record], list[str], str]:
    filename = file.filename or "uploaded_dataset"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be UTF-8 encoded.",
        ) from exc

    if extension == "csv":
        records, fields = parse_csv_dataset(text)
        return records, fields, "csv"

    if extension == "json":
        records, fields = parse_json_dataset(text)
        return records, fields, "json"

    raise HTTPException(
        status_code=400,
        detail="Unsupported file type. Upload a .csv or .json file.",
    )


def parse_csv_dataset(text: str) -> tuple[list[Record], list[str]]:
    try:
        rows = csv.reader(StringIO(text))
        header = next(rows)
    except StopIteration as exc:
        raise HTTPException(status_code=400, detail="CSV file must include a header row.") from exc
    except csv.Error as exc:
        raise HTTPException(status_code=400, detail=f"CSV parsing failed: {exc}") from exc

    fields = [field.strip() for field in header]
    validate_fields(fields, "CSV header")

    records: list[Record] = []
    for line_number, row in enumerate(rows, start=2):
        if not row or all(not value.strip() for value in row):
            continue

        if len(row) != len(fields):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"CSV row {line_number} has {len(row)} columns, "
                    f"but the header has {len(fields)} columns."
                ),
            )

        records.append({field: value.strip() for field, value in zip(fields, row, strict=True)})

    if not records:
        raise HTTPException(status_code=400, detail="CSV file must include at least one data row.")

    return records, fields


def parse_json_dataset(text: str) -> tuple[list[Record], list[str]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc.msg}.") from exc

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON dataset must be an array of objects.")

    if not data:
        raise HTTPException(status_code=400, detail="JSON dataset must include at least one object.")

    if not isinstance(data[0], dict):
        raise HTTPException(status_code=400, detail="JSON dataset items must be objects.")

    fields = list(data[0].keys())
    validate_fields(fields, "JSON object")

    expected_fields = set(fields)
    records: list[Record] = []

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"JSON item {index} must be an object.")

        item_fields = set(item.keys())
        if item_fields != expected_fields:
            raise HTTPException(
                status_code=400,
                detail=f"JSON item {index} does not use the same fields as the first item.",
            )

        for key, value in item.items():
            if isinstance(value, dict | list):
                raise HTTPException(
                    status_code=400,
                    detail=f"JSON field '{key}' in item {index} must be flat, not nested.",
                )

        records.append({field: item[field] for field in fields})

    return records, fields


def list_sample_datasets() -> list[SampleDatasetOption]:
    return list(_scan_sample_datasets())


def load_sample_dataset(sample_id: str | None = None) -> DatasetMetadata:
    options = list_sample_datasets()
    if not options:
        raise HTTPException(status_code=404, detail="No sample datasets were found.")

    selected_id = sample_id or "sample_orders_1k_csv"
    selected = next((option for option in options if option.sample_id == selected_id), None)
    if selected is None:
        raise HTTPException(status_code=404, detail=f"Sample dataset '{selected_id}' was not found.")

    path = _sample_path(selected.sample_id)
    text = _read_dataset_file(path)

    if selected.file_type == "csv":
        records, fields = parse_csv_dataset(text)
    else:
        records, fields = parse_json_dataset(text)

    return store_dataset(
        dataset_name=selected.dataset_name,
        records=records,
        fields=fields,
        source="sample",
        file_type=selected.file_type,
    )


def validate_fields(fields: list[str], label: str) -> None:
    if not fields:
        raise HTTPException(status_code=400, detail=f"{label} must define at least one field.")

    if any(not field for field in fields):
        raise HTTPException(status_code=400, detail=f"{label} contains an empty field name.")

    duplicates = sorted({field for field in fields if fields.count(field) > 1})
    if duplicates:
        duplicate_list = ", ".join(duplicates)
        raise HTTPException(status_code=400, detail=f"{label} contains duplicate fields: {duplicate_list}.")


@lru_cache(maxsize=1)
def _scan_sample_datasets() -> tuple[SampleDatasetOption, ...]:
    directory = Path(settings.sample_dataset_dir)
    if not directory.exists():
        return ()

    options: list[SampleDatasetOption] = []
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in {".csv", ".json"}:
            continue

        file_type = path.suffix.lower().lstrip(".")
        fields, record_count = _sample_file_metadata(path, file_type)
        options.append(
            SampleDatasetOption(
                sample_id=f"{path.stem}_{file_type}",
                dataset_name=path.name,
                record_count=record_count,
                fields=fields,
                file_type=file_type,
            )
        )

    options.sort(key=lambda option: (option.record_count, option.file_type, option.dataset_name))
    return tuple(options)


def _sample_file_metadata(path: Path, file_type: str) -> tuple[list[str], int]:
    if file_type == "csv":
        return _csv_sample_file_metadata(path)

    inferred_count = _infer_sample_record_count(path)
    if inferred_count is not None:
        return _json_sample_fields(path), inferred_count

    text = _read_dataset_file(path)
    records, fields = parse_json_dataset(text)
    return fields, len(records)


def _csv_sample_file_metadata(path: Path) -> tuple[list[str], int]:
    inferred_count = _infer_sample_record_count(path)

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = csv.reader(file)
            header = next(rows)
            fields = [field.strip() for field in header]
            validate_fields(fields, "CSV header")

            if inferred_count is not None:
                return fields, inferred_count

            record_count = sum(1 for row in rows if row and any(value.strip() for value in row))
            return fields, record_count
    except StopIteration as exc:
        raise HTTPException(status_code=400, detail="CSV file must include a header row.") from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Sample dataset '{path.name}' must be UTF-8 encoded.") from exc
    except csv.Error as exc:
        raise HTTPException(status_code=400, detail=f"CSV parsing failed: {exc}") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read sample dataset '{path.name}'.") from exc


def _json_sample_fields(path: Path) -> list[str]:
    decoder = json.JSONDecoder()
    buffer = ""
    array_start: int | None = None

    try:
        with path.open("r", encoding="utf-8-sig") as file:
            while True:
                chunk = file.read(65536)
                if not chunk and not buffer:
                    raise HTTPException(status_code=400, detail="JSON dataset must include at least one object.")

                buffer += chunk
                if array_start is None:
                    array_start = buffer.find("[")
                    if array_start == -1:
                        if not chunk:
                            raise HTTPException(status_code=400, detail="JSON dataset must be an array of objects.")
                        continue

                item_start = array_start + 1
                while item_start < len(buffer) and buffer[item_start].isspace():
                    item_start += 1

                if item_start < len(buffer) and buffer[item_start] == "]":
                    raise HTTPException(status_code=400, detail="JSON dataset must include at least one object.")

                try:
                    item, _ = decoder.raw_decode(buffer[item_start:])
                except json.JSONDecodeError:
                    if chunk:
                        continue
                    raise

                if not isinstance(item, dict):
                    raise HTTPException(status_code=400, detail="JSON dataset items must be objects.")

                fields = list(item.keys())
                validate_fields(fields, "JSON object")
                return fields
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Sample dataset '{path.name}' must be UTF-8 encoded.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc.msg}.") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read sample dataset '{path.name}'.") from exc


def _infer_sample_record_count(path: Path) -> int | None:
    suffix = path.stem.rsplit("_", 1)[-1].lower()
    match = re.fullmatch(r"(\d+)([km]?)", suffix)
    if match is None:
        return None

    value = int(match.group(1))
    unit = match.group(2)
    if unit == "k":
        return value * 1_000
    if unit == "m":
        return value * 1_000_000
    return value


def _sample_path(sample_id: str) -> Path:
    directory = Path(settings.sample_dataset_dir).resolve()
    file_type = sample_id.rsplit("_", 1)[-1]
    stem = sample_id.removesuffix(f"_{file_type}")
    path = (directory / f"{stem}.{file_type}").resolve()

    if directory not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid sample dataset identifier.")

    if path.suffix.lower() not in {".csv", ".json"} or not path.exists():
        raise HTTPException(status_code=404, detail=f"Sample dataset '{sample_id}' was not found.")

    return path


def _read_dataset_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Sample dataset '{path.name}' must be UTF-8 encoded.") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read sample dataset '{path.name}'.") from exc
