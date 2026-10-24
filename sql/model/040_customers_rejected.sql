CREATE TABLE IF NOT EXISTS {namespace}.`customers_rejected{suffix}` (
  customer_id STRING,
  name STRING,
  age STRING,
  country STRING,
  email STRING,
  source_file STRING NOT NULL,
  source_row_number BIGINT NOT NULL,
  rejection_reasons ARRAY<STRING> NOT NULL,
  snapshot_id STRING NOT NULL,
  run_id STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL
) USING DELTA;
