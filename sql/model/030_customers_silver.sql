CREATE TABLE IF NOT EXISTS {namespace}.`customers_silver{suffix}` (
  customer_id STRING NOT NULL,
  name STRING NOT NULL,
  age INT NOT NULL,
  country_code STRING NOT NULL,
  email STRING,
  is_adult BOOLEAN NOT NULL,
  has_valid_email BOOLEAN NOT NULL,
  is_contactable BOOLEAN NOT NULL,
  source_row_number BIGINT NOT NULL,
  snapshot_id STRING NOT NULL,
  run_id STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL
) USING DELTA;
