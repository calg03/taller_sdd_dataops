CREATE TABLE IF NOT EXISTS {namespace}.`customer_contactability_gold{suffix}` (
  aggregation_level STRING NOT NULL,
  country_group STRING NOT NULL,
  country_code STRING,
  country_name STRING NOT NULL,
  region STRING,
  adult_customers BIGINT NOT NULL,
  contactable_adults BIGINT NOT NULL,
  non_contactable_adults BIGINT NOT NULL,
  contactable_pct DECIMAL(7,4),
  published_at TIMESTAMP NOT NULL,
  snapshot_id STRING NOT NULL,
  run_id STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL
) USING DELTA;
