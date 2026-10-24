MERGE INTO {namespace}.`countries_reference{suffix}` t
USING (SELECT :code AS country_code, :name AS country_name,
              :region AS region, :version AS reference_version) s
ON t.country_code = s.country_code
WHEN MATCHED AND (t.country_name <> s.country_name OR t.region <> s.region
                  OR t.reference_version <> s.reference_version)
  THEN UPDATE SET country_name = s.country_name, region = s.region,
                  reference_version = s.reference_version, run_id = :run_id,
                  loaded_at = current_timestamp()
WHEN NOT MATCHED THEN INSERT
  (country_code, country_name, region, reference_version, run_id, loaded_at)
  VALUES (s.country_code, s.country_name, s.region, s.reference_version,
          :run_id, current_timestamp());
