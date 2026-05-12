"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

type DatabaseStatus = {
  ok: boolean;
  message: string;
};

type HealthResponse = {
  status: "ok" | "degraded";
  databases: {
    postgresql?: DatabaseStatus;
    mongodb?: DatabaseStatus;
  };
};

type DatasetMetadata = {
  dataset_id: string;
  dataset_name: string;
  record_count: number;
  fields: string[];
  source: "upload" | "sample" | string;
  file_type: "csv" | "json" | string;
};

type SampleDatasetOption = {
  sample_id: string;
  dataset_name: string;
  record_count: number;
  fields: string[];
  file_type: "csv" | "json" | string;
};

type DatabaseLoadResult = {
  ok: boolean;
  record_count: number;
  target_name: string;
  message: string;
};

type DatasetLoadResult = {
  dataset_id: string;
  dataset_name: string;
  expected_record_count: number;
  postgresql: DatabaseLoadResult;
  mongodb: DatabaseLoadResult;
  counts_match: boolean;
};

type BenchmarkOperation = "WRITE" | "READ" | "UPDATE" | "DELETE";

type BenchmarkMetrics = {
  total_time_ms: number;
  average_latency_ms: number;
  throughput_ops_sec: number;
  min_time_ms: number;
  max_time_ms: number;
  std_dev_ms: number;
  operation_count: number;
};

type BenchmarkDatabaseResult = {
  ok: boolean;
  target_name: string;
  run_times_ms: number[];
  affected_counts: number[];
  metrics: BenchmarkMetrics;
  message: string;
};

type BenchmarkRunResult = {
  benchmark_id: string;
  created_at: string;
  dataset_id: string;
  dataset_name: string;
  operation: BenchmarkOperation;
  record_count: number;
  repetitions: number;
  postgresql: BenchmarkDatabaseResult;
  mongodb: BenchmarkDatabaseResult;
};

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dataset, setDataset] = useState<DatasetMetadata | null>(null);
  const [datasetError, setDatasetError] = useState<string | null>(null);
  const [datasetMessage, setDatasetMessage] = useState<string | null>(null);
  const [isDatasetLoading, setIsDatasetLoading] = useState(false);
  const [sampleOptions, setSampleOptions] = useState<SampleDatasetOption[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState("sample_orders_1k_csv");
  const [loadResult, setLoadResult] = useState<DatasetLoadResult | null>(null);
  const [isLoadRunning, setIsLoadRunning] = useState(false);
  const [operation, setOperation] = useState<BenchmarkOperation>("WRITE");
  const [repetitions, setRepetitions] = useState(3);
  const [benchmarkResult, setBenchmarkResult] = useState<BenchmarkRunResult | null>(null);
  const [isBenchmarkRunning, setIsBenchmarkRunning] = useState(false);
  const [previousResults, setPreviousResults] = useState<BenchmarkRunResult[]>([]);
  const [isResultsLoading, setIsResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);

  useEffect(() => {
    async function loadHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/health/databases`, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Backend returned HTTP ${response.status}`);
        }

        const data = (await response.json()) as HealthResponse;
        setHealth(data);
        setError(null);
      } catch (unknownError) {
        const message =
          unknownError instanceof Error
            ? unknownError.message
            : "Backend health check failed.";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    }

    loadHealth();
  }, []);

  useEffect(() => {
    async function loadSampleOptions() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/datasets/samples`, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Sample list returned HTTP ${response.status}`);
        }

        const options = (await response.json()) as SampleDatasetOption[];
        setSampleOptions(options);

        if (options.length > 0 && !options.some((option) => option.sample_id === selectedSampleId)) {
          setSelectedSampleId(options[0].sample_id);
        }
      } catch (unknownError) {
        const message =
          unknownError instanceof Error
            ? unknownError.message
            : "Sample dataset list could not be loaded.";
        setDatasetError(message);
      }
    }

    loadSampleOptions();
  }, [selectedSampleId]);

  useEffect(() => {
    loadBenchmarkResults();
  }, []);

  const overallStatus = useMemo(() => {
    if (isLoading) {
      return "Checking";
    }

    if (error) {
      return "Backend unavailable";
    }

    return health?.status === "ok" ? "Ready" : "Needs attention";
  }, [error, health?.status, isLoading]);

  async function parseDatasetResponse(response: Response) {
    if (response.ok) {
      return (await response.json()) as DatasetMetadata;
    }

    let message = `Dataset request failed with HTTP ${response.status}.`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Keep the generic message when the backend does not return JSON.
    }

    throw new Error(message);
  }

  async function parseLoadResponse(response: Response) {
    if (response.ok) {
      return (await response.json()) as DatasetLoadResult;
    }

    let message = `Dataset loading failed with HTTP ${response.status}.`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Keep the generic message when the backend does not return JSON.
    }

    throw new Error(message);
  }

  async function loadBenchmarkResults() {
    setIsResultsLoading(true);
    setResultsError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/benchmarks`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`Benchmark history returned HTTP ${response.status}.`);
      }

      const results = (await response.json()) as BenchmarkRunResult[];
      setPreviousResults(results);
    } catch (unknownError) {
      const message =
        unknownError instanceof Error
          ? unknownError.message
          : "Benchmark history could not be loaded.";
      setResultsError(message);
    } finally {
      setIsResultsLoading(false);
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setDatasetError("Select a CSV or JSON file before uploading.");
      setDatasetMessage(null);
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    setIsDatasetLoading(true);
    setDatasetError(null);
    setDatasetMessage(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/datasets/upload`, {
        method: "POST",
        body: formData,
      });
      const metadata = await parseDatasetResponse(response);
      setDataset(metadata);
      setLoadResult(null);
      setBenchmarkResult(null);
      setDatasetMessage("Dataset accepted and validated.");
    } catch (unknownError) {
      const message =
        unknownError instanceof Error
          ? unknownError.message
          : "Dataset upload failed.";
      setDataset(null);
      setDatasetError(message);
    } finally {
      setIsDatasetLoading(false);
    }
  }

  async function handleSampleDataset() {
    setIsDatasetLoading(true);
    setDatasetError(null);
    setDatasetMessage(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/datasets/sample`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ sample_id: selectedSampleId }),
      });
      const metadata = await parseDatasetResponse(response);
      setDataset(metadata);
      setLoadResult(null);
      setBenchmarkResult(null);
      setSelectedFile(null);
      setDatasetMessage("Sample dataset selected.");
    } catch (unknownError) {
      const message =
        unknownError instanceof Error
          ? unknownError.message
          : "Sample dataset request failed.";
      setDataset(null);
      setDatasetError(message);
    } finally {
      setIsDatasetLoading(false);
    }
  }

  async function handleLoadDataset() {
    if (!dataset) {
      setDatasetError("Select or upload a dataset before loading it.");
      setDatasetMessage(null);
      return;
    }

    setIsLoadRunning(true);
    setDatasetError(null);
    setDatasetMessage(null);
    setLoadResult(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/datasets/load`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ dataset_id: dataset.dataset_id }),
      });
      const result = await parseLoadResponse(response);
      setLoadResult(result);
      setBenchmarkResult(null);
      setDatasetMessage(
        result.counts_match
          ? "Dataset loaded into PostgreSQL and MongoDB."
          : "Dataset loaded, but record counts do not match."
      );
    } catch (unknownError) {
      const message =
        unknownError instanceof Error
          ? unknownError.message
          : "Dataset loading failed.";
      setDatasetError(message);
    } finally {
      setIsLoadRunning(false);
    }
  }

  async function parseBenchmarkResponse(response: Response) {
    if (response.ok) {
      return (await response.json()) as BenchmarkRunResult;
    }

    let message = `Benchmark failed with HTTP ${response.status}.`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Keep the generic message when the backend does not return JSON.
    }

    throw new Error(message);
  }

  async function handleRunBenchmark(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!dataset || !loadResult?.counts_match) {
      setDatasetError("Load a dataset into both databases before running a benchmark.");
      setDatasetMessage(null);
      return;
    }

    setIsBenchmarkRunning(true);
    setDatasetError(null);
    setDatasetMessage(null);
    setBenchmarkResult(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/benchmarks/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          dataset_id: dataset.dataset_id,
          operation,
          record_count: dataset.record_count,
          repetitions,
        }),
      });
      const result = await parseBenchmarkResponse(response);
      setBenchmarkResult(result);
      await loadBenchmarkResults();
      setDatasetMessage("Benchmark completed on PostgreSQL and MongoDB.");
    } catch (unknownError) {
      const message =
        unknownError instanceof Error ? unknownError.message : "Benchmark failed.";
      setDatasetError(message);
    } finally {
      setIsBenchmarkRunning(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="dashboard">
        <header className="header">
          <div>
            <p className="eyebrow">Local Benchmark Workspace</p>
            <h1>SQL vs NoSQL Benchmark Platform</h1>
            <p className="subtitle">
              Load one CSV or JSON dataset into MongoDB and PostgreSQL, run the
              same CRUD benchmark, then compare NoSQL and SQL performance side by side.
            </p>
          </div>
          <SystemStatus
            health={health}
            loading={isLoading}
            message={error}
            status={overallStatus}
          />
        </header>

        <section className="database-lanes" aria-label="Database comparison targets">
          <TechnologyLane
            accent="nosql"
            description="Document database target for flexible JSON-like records and collection-based CRUD operations."
            label="NoSQL"
            name="MongoDB"
            status={health?.databases.mongodb?.ok}
          />
          <TechnologyLane
            accent="sql"
            description="Relational database target for tabular rows, SQL operations, and structured fields."
            label="SQL"
            name="PostgreSQL"
            status={health?.databases.postgresql?.ok}
          />
        </section>

        <section className="workflow-stack">
          <div className="panel">
          <div className="section-heading">
            <div>
              <h2>Dataset Setup</h2>
              <p>Upload a flat CSV or JSON file, or use the built-in sample dataset.</p>
            </div>
            <button
              className="button secondary"
              type="button"
              onClick={handleSampleDataset}
              disabled={isDatasetLoading || sampleOptions.length === 0}
            >
              Use Sample Dataset
            </button>
          </div>

          <div className="sample-control">
            <label htmlFor="sample-dataset">Sample dataset</label>
            <select
              id="sample-dataset"
              value={selectedSampleId}
              onChange={(event) => setSelectedSampleId(event.target.value)}
              disabled={isDatasetLoading || sampleOptions.length === 0}
            >
              {sampleOptions.map((option) => (
                <option key={option.sample_id} value={option.sample_id}>
                  {option.dataset_name} - {formatInteger(option.record_count)} records
                </option>
              ))}
            </select>
          </div>

          <form className="upload-form" onSubmit={handleUpload}>
            <label className="file-control" htmlFor="dataset-file">
              <span>Dataset file</span>
              <span className="file-input-row">
                <span className="file-picker-button">Choose File</span>
                <span className="file-name">
                  {selectedFile ? selectedFile.name : "No file chosen"}
                </span>
              </span>
              <input
                accept=".csv,.json,text/csv,application/json"
                id="dataset-file"
                type="file"
                onChange={(event) => {
                  setSelectedFile(event.target.files?.[0] ?? null);
                  setDatasetError(null);
                  setDatasetMessage(null);
                }}
              />
            </label>
            <button className="button" type="submit" disabled={isDatasetLoading}>
              {isDatasetLoading ? "Processing" : "Upload Dataset"}
            </button>
          </form>

          {datasetError ? <div className="alert error">{datasetError}</div> : null}
          {datasetMessage ? <div className="alert success">{datasetMessage}</div> : null}

          {dataset ? (
            <>
              <DatasetSummary dataset={dataset} />
              <div className="load-actions">
                <button
                  className="button"
                  type="button"
                  onClick={handleLoadDataset}
                  disabled={isLoadRunning || isDatasetLoading}
                >
                  {isLoadRunning ? "Loading Dataset" : "Load Dataset to Databases"}
                </button>
              </div>
            </>
          ) : null}

          {loadResult ? <LoadSummary result={loadResult} /> : null}
          </div>

          <div className="panel">
          <div className="section-heading">
            <div>
              <h2>Benchmark Configuration</h2>
              <p>Run WRITE, READ, UPDATE, or DELETE with the same parameters on both databases.</p>
            </div>
          </div>

          <form className="benchmark-form" onSubmit={handleRunBenchmark}>
            <label className="form-control">
              <span>Operation</span>
              <select
                value={operation}
                onChange={(event) => setOperation(event.target.value as BenchmarkOperation)}
              >
                <option value="WRITE">WRITE</option>
                <option value="READ">READ</option>
                <option value="UPDATE">UPDATE</option>
                <option value="DELETE">DELETE</option>
              </select>
            </label>

            <label className="form-control">
              <span>Repetitions</span>
              <input
                max={20}
                min={1}
                type="number"
                value={repetitions}
                onChange={(event) => setRepetitions(Number(event.target.value))}
              />
            </label>

            <div className="benchmark-readonly">
              <span>Records used</span>
              <strong>{dataset ? formatInteger(dataset.record_count) : "-"}</strong>
            </div>

            <button
              className="button"
              type="submit"
              disabled={isBenchmarkRunning || !loadResult?.counts_match}
            >
              {isBenchmarkRunning ? "Running Benchmark" : "Run Benchmark"}
            </button>
          </form>
          </div>
        </section>

        <section className="panel full-width-panel">
          <div className="section-heading">
            <div>
              <h2>Results</h2>
              <p>NoSQL results stay on the left; SQL results stay on the right for every comparison.</p>
            </div>
          </div>

          {benchmarkResult ? <BenchmarkSummary result={benchmarkResult} /> : <EmptyResults />}

          <PreviousResults
            error={resultsError}
            isLoading={isResultsLoading}
            results={previousResults}
          />
        </section>
      </div>
    </main>
  );
}

function LoadSummary({ result }: { result: DatasetLoadResult }) {
  return (
    <div className="load-summary">
      <div className="load-summary-heading">
        <strong>Database Load Verification</strong>
        <span className={`badge ${result.counts_match ? "ok" : ""}`}>
          {result.counts_match ? "Counts Match" : "Mismatch"}
        </span>
      </div>
      <div className="summary-grid three-columns">
        <SummaryItem
          label="Expected"
          value={formatInteger(result.expected_record_count)}
        />
        <SummaryItem
          label="NoSQL / MongoDB"
          value={`${formatInteger(result.mongodb.record_count)} documents`}
        />
        <SummaryItem
          label="SQL / PostgreSQL"
          value={`${formatInteger(result.postgresql.record_count)} rows`}
        />
      </div>
      <div className="target-list">
        <span>MongoDB target: {result.mongodb.target_name}</span>
        <span>PostgreSQL target: {result.postgresql.target_name}</span>
      </div>
    </div>
  );
}

function BenchmarkSummary({ result }: { result: BenchmarkRunResult }) {
  return (
    <div className="benchmark-summary">
      <div className="load-summary-heading">
        <strong>{result.operation} Benchmark Result</strong>
        <span className="badge ok">{result.benchmark_id}</span>
      </div>
      <div className="summary-grid three-columns">
        <SummaryItem label="Records" value={formatInteger(result.record_count)} />
        <SummaryItem label="Repetitions" value={formatInteger(result.repetitions)} />
        <SummaryItem label="Operation" value={result.operation} />
      </div>
      <div className="benchmark-result-grid">
        <DatabaseBenchmarkPanel
          accent="nosql"
          label="NoSQL"
          name="MongoDB"
          result={result.mongodb}
        />
        <DatabaseBenchmarkPanel
          accent="sql"
          label="SQL"
          name="PostgreSQL"
          result={result.postgresql}
        />
      </div>
      <MetricComparison result={result} />
      <BenchmarkCharts result={result} />
    </div>
  );
}

function DatabaseBenchmarkPanel({
  accent,
  label,
  name,
  result,
}: {
  accent: "nosql" | "sql";
  label: string;
  name: string;
  result: BenchmarkDatabaseResult;
}) {
  return (
    <div className={`benchmark-db-panel ${accent}`}>
      <div className="load-summary-heading">
        <div>
          <span className="db-label">{label}</span>
          <strong>{name}</strong>
        </div>
        <span className={`badge ${result.ok ? "ok" : ""}`}>{result.ok ? "OK" : "Error"}</span>
      </div>
      <div className="summary-grid metric-grid">
        <SummaryItem label="Total time" value={formatMs(result.metrics.total_time_ms)} />
        <SummaryItem label="Avg latency" value={formatMs(result.metrics.average_latency_ms)} />
        <SummaryItem
          label="Throughput"
          value={`${formatNumber(result.metrics.throughput_ops_sec)} ops/sec`}
        />
        <SummaryItem label="Min time" value={formatMs(result.metrics.min_time_ms)} />
        <SummaryItem label="Max time" value={formatMs(result.metrics.max_time_ms)} />
        <SummaryItem label="Std dev" value={formatMs(result.metrics.std_dev_ms)} />
        <SummaryItem
          label="Operations"
          value={formatInteger(result.metrics.operation_count)}
        />
        <SummaryItem label="Target" value={result.target_name} mono />
      </div>
      <div className="run-list">
        {result.run_times_ms.map((time, index) => (
          <span key={`${name}-${index}`}>
            Run {index + 1}: {time.toFixed(3)} ms
          </span>
        ))}
      </div>
    </div>
  );
}

function MetricComparison({ result }: { result: BenchmarkRunResult }) {
  const rows: {
    key: keyof BenchmarkMetrics;
    label: string;
    lowerIsBetter: boolean;
    formatter: (value: number) => string;
  }[] = [
    {
      key: "total_time_ms",
      label: "Total execution time",
      lowerIsBetter: true,
      formatter: formatMs,
    },
    {
      key: "average_latency_ms",
      label: "Average latency",
      lowerIsBetter: true,
      formatter: formatMs,
    },
    {
      key: "throughput_ops_sec",
      label: "Throughput",
      lowerIsBetter: false,
      formatter: (value) => `${formatNumber(value)} ops/sec`,
    },
    {
      key: "min_time_ms",
      label: "Minimum time",
      lowerIsBetter: true,
      formatter: formatMs,
    },
    {
      key: "max_time_ms",
      label: "Maximum time",
      lowerIsBetter: true,
      formatter: formatMs,
    },
    {
      key: "std_dev_ms",
      label: "Standard deviation",
      lowerIsBetter: true,
      formatter: formatMs,
    },
  ];

  return (
    <div className="comparison-table-wrap">
      <strong>Comparison Table</strong>
      <table className="comparison-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>NoSQL / MongoDB</th>
            <th>SQL / PostgreSQL</th>
            <th>Faster</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const mongodbValue = result.mongodb.metrics[row.key];
            const postgresqlValue = result.postgresql.metrics[row.key];
            const faster = pickFasterDatabase(
              postgresqlValue,
              mongodbValue,
              row.lowerIsBetter
            );

            return (
              <tr key={row.key}>
                <td>{row.label}</td>
                <td>{row.formatter(mongodbValue)}</td>
                <td>{row.formatter(postgresqlValue)}</td>
                <td>{faster}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function BenchmarkCharts({ result }: { result: BenchmarkRunResult }) {
  return (
    <div className="chart-section">
      <div className="chart-grid">
        <BarComparisonChart
          label="Total Execution Time"
          mongodbValue={result.mongodb.metrics.total_time_ms}
          postgresqlValue={result.postgresql.metrics.total_time_ms}
          unit="ms"
        />
        <BarComparisonChart
          label="Throughput"
          mongodbValue={result.mongodb.metrics.throughput_ops_sec}
          postgresqlValue={result.postgresql.metrics.throughput_ops_sec}
          unit="ops/sec"
        />
      </div>
      <RepeatedRunsChart result={result} />
    </div>
  );
}

function BarComparisonChart({
  label,
  mongodbValue,
  postgresqlValue,
  unit,
}: {
  label: string;
  mongodbValue: number;
  postgresqlValue: number;
  unit: string;
}) {
  const maxValue = Math.max(postgresqlValue, mongodbValue, 1);
  const rows = [
    {
      name: "MongoDB",
      value: mongodbValue,
      className: "mongodb",
    },
    {
      name: "PostgreSQL",
      value: postgresqlValue,
      className: "postgresql",
    },
  ];

  return (
    <div className="chart-panel">
      <div className="chart-heading">
        <strong>{label}</strong>
        <span>{unit}</span>
      </div>
      <div className="bar-chart" aria-label={`${label} chart`}>
        {rows.map((row) => (
          <div className="bar-row" key={`${label}-${row.name}`}>
            <span>{row.name}</span>
            <div className="bar-track">
              <div
                className={`bar-fill ${row.className}`}
                style={{ width: `${Math.max((row.value / maxValue) * 100, 2)}%` }}
              />
            </div>
            <strong>{formatChartValue(row.value)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function RepeatedRunsChart({ result }: { result: BenchmarkRunResult }) {
  const series = [
    {
      name: "MongoDB",
      values: result.mongodb.run_times_ms,
      className: "mongodb",
      stroke: "#16a34a",
    },
    {
      name: "PostgreSQL",
      values: result.postgresql.run_times_ms,
      className: "postgresql",
      stroke: "#2563eb",
    },
  ];
  const maxTime = Math.max(...series.flatMap((item) => item.values), 1);
  const maxRuns = Math.max(...series.map((item) => item.values.length), 1);

  return (
    <div className="chart-panel line-chart-panel">
      <div className="chart-heading">
        <strong>Repeated Runs</strong>
        <span>ms per repetition</span>
      </div>
      <svg
        aria-label="Repeated runs line chart"
        className="line-chart"
        preserveAspectRatio="none"
        role="img"
        viewBox="0 0 100 60"
      >
        <line className="chart-grid-line" x1="0" x2="100" y1="15" y2="15" />
        <line className="chart-grid-line" x1="0" x2="100" y1="30" y2="30" />
        <line className="chart-grid-line" x1="0" x2="100" y1="45" y2="45" />
        {series.map((item) => {
          const points = item.values
            .map((value, index) => {
              const x = maxRuns === 1 ? 0 : (index / (maxRuns - 1)) * 100;
              const y = 56 - (value / maxTime) * 52;
              return `${x.toFixed(3)},${y.toFixed(3)}`;
            })
            .join(" ");

          return (
            <g key={item.name}>
              <polyline
                fill="none"
                points={points}
                stroke={item.stroke}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.4"
              />
              {item.values.map((value, index) => {
                const x = maxRuns === 1 ? 0 : (index / (maxRuns - 1)) * 100;
                const y = 56 - (value / maxTime) * 52;

                return (
                  <circle
                    cx={x}
                    cy={y}
                    fill={item.stroke}
                    key={`${item.name}-${index}`}
                    r="1.8"
                  />
                );
              })}
            </g>
          );
        })}
      </svg>
      <div className="chart-legend">
        {series.map((item) => (
          <span key={item.name}>
            <i className={item.className} />
            {item.name}
          </span>
        ))}
      </div>
      <div className="run-list">
        {Array.from({ length: maxRuns }, (_, index) => (
          <span key={`run-comparison-${index}`}>
            Run {index + 1}: MongoDB {formatMs(result.mongodb.run_times_ms[index] ?? 0)} / PostgreSQL{" "}
            {formatMs(result.postgresql.run_times_ms[index] ?? 0)}
          </span>
        ))}
      </div>
    </div>
  );
}

function PreviousResults({
  error,
  isLoading,
  results,
}: {
  error: string | null;
  isLoading: boolean;
  results: BenchmarkRunResult[];
}) {
  return (
    <div className="previous-results">
      <div className="load-summary-heading">
        <strong>Previous Results</strong>
        <span className="badge">{isLoading ? "Loading" : `${results.length} stored`}</span>
      </div>

      {error ? <div className="alert error">{error}</div> : null}
      {!error && results.length === 0 ? (
        <p>No benchmark results have been stored yet.</p>
      ) : null}

      {results.length > 0 ? (
        <div className="comparison-table-wrap compact">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Benchmark</th>
                <th>Dataset</th>
                <th>Operation</th>
                <th>NoSQL total</th>
                <th>SQL total</th>
                <th>Throughput leader</th>
              </tr>
            </thead>
            <tbody>
              {results.slice(0, 10).map((result) => (
                <tr key={result.benchmark_id}>
                  <td className="mono">{result.benchmark_id}</td>
                  <td>{result.dataset_name}</td>
                  <td>{result.operation}</td>
                  <td>{formatMs(result.mongodb.metrics.total_time_ms)}</td>
                  <td>{formatMs(result.postgresql.metrics.total_time_ms)}</td>
                  <td>
                    {pickFasterDatabase(
                      result.postgresql.metrics.throughput_ops_sec,
                      result.mongodb.metrics.throughput_ops_sec,
                      false
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function SystemStatus({
  health,
  loading,
  message,
  status,
}: {
  health: HealthResponse | null;
  loading: boolean;
  message: string | null;
  status: string;
}) {
  const backendOk = !message && !loading;
  const mongodbOk = Boolean(health?.databases.mongodb?.ok);
  const postgresqlOk = Boolean(health?.databases.postgresql?.ok);

  return (
    <aside className="system-status" aria-label="System status">
      <div
        className={`status-pill ${
          message ? "error" : health?.status === "ok" ? "ok" : "degraded"
        }`}
      >
        {status}
      </div>
      <div className="status-mini-grid">
        <StatusDot label="API" loading={loading} ok={backendOk} />
        <StatusDot label="NoSQL" loading={loading} ok={mongodbOk} />
        <StatusDot label="SQL" loading={loading} ok={postgresqlOk} />
      </div>
    </aside>
  );
}

function StatusDot({
  label,
  loading,
  ok,
}: {
  label: string;
  loading: boolean;
  ok: boolean;
}) {
  return (
    <span className={`status-dot ${ok ? "ok" : loading ? "" : "error"}`}>
      <i />
      {label}
    </span>
  );
}

function TechnologyLane({
  accent,
  description,
  label,
  name,
  status,
}: {
  accent: "nosql" | "sql";
  description: string;
  label: string;
  name: string;
  status?: boolean;
}) {
  return (
    <div className={`technology-lane ${accent}`}>
      <div>
        <span className="lane-label">{label}</span>
        <h2>{name}</h2>
      </div>
      <p>{description}</p>
      <span className={`lane-status ${status ? "ok" : ""}`}>
        {status ? "Connected" : "Waiting"}
      </span>
    </div>
  );
}

function EmptyResults() {
  return (
    <div className="empty-results">
      <div className="empty-result-card nosql">
        <span className="db-label">NoSQL</span>
        <strong>MongoDB results</strong>
        <p>Run a benchmark to show document database metrics on the left.</p>
      </div>
      <div className="empty-result-card sql">
        <span className="db-label">SQL</span>
        <strong>PostgreSQL results</strong>
        <p>Run a benchmark to show relational database metrics on the right.</p>
      </div>
    </div>
  );
}

function formatMs(value: number) {
  return `${formatNumber(value)} ms`;
}

function formatNumber(value: number) {
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 4,
  });
}

function formatChartValue(value: number) {
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function formatInteger(value: number) {
  return value.toLocaleString();
}

function pickFasterDatabase(
  postgresqlValue: number,
  mongodbValue: number,
  lowerIsBetter: boolean
) {
  if (postgresqlValue === mongodbValue) {
    return "Tie";
  }

  if (lowerIsBetter) {
    return postgresqlValue < mongodbValue ? "SQL / PostgreSQL" : "NoSQL / MongoDB";
  }

  return postgresqlValue > mongodbValue ? "SQL / PostgreSQL" : "NoSQL / MongoDB";
}

function DatasetSummary({ dataset }: { dataset: DatasetMetadata }) {
  return (
    <div className="dataset-summary">
      <div className="summary-grid">
        <SummaryItem label="Dataset ID" value={dataset.dataset_id} mono />
        <SummaryItem label="Name" value={dataset.dataset_name} />
        <SummaryItem label="Records" value={formatInteger(dataset.record_count)} />
        <SummaryItem label="Source" value={dataset.source} />
        <SummaryItem label="Type" value={dataset.file_type.toUpperCase()} />
      </div>

      <div className="field-section">
        <strong>Fields</strong>
        <div className="field-list">
          {dataset.fields.map((field) => (
            <span className="field-chip" key={field}>
              {field}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function SummaryItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="summary-item">
      <span>{label}</span>
      <strong className={mono ? "mono" : ""}>{value}</strong>
    </div>
  );
}
