CREATE TABLE IF NOT EXISTS {namespace}.`pipeline_stage_runs{suffix}` (
  run_id STRING NOT NULL,
  snapshot_id STRING,
  stage_name STRING NOT NULL,
  attempt_number INT NOT NULL,
  status STRING NOT NULL,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  input_rows BIGINT,
  output_rows BIGINT,
  rejected_rows BIGINT,
  rejection_pct DECIMAL(7,4),
  error_code STRING,
  error_summary STRING,
  commit_sha STRING NOT NULL,
  environment STRING NOT NULL
) USING DELTA;
