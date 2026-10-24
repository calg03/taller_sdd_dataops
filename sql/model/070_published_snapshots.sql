CREATE TABLE IF NOT EXISTS {namespace}.`published_snapshots{suffix}` (
  environment STRING NOT NULL,
  snapshot_id STRING NOT NULL,
  run_id STRING NOT NULL,
  published_at TIMESTAMP NOT NULL,
  source_file STRING NOT NULL
) USING DELTA;
