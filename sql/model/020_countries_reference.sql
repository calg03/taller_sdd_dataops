CREATE TABLE IF NOT EXISTS {namespace}.`countries_reference{suffix}` (
  country_code STRING NOT NULL,
  country_name STRING NOT NULL,
  region STRING NOT NULL,
  reference_version STRING NOT NULL,
  run_id STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL
) USING DELTA;
