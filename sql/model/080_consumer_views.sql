CREATE OR REPLACE VIEW {namespace}.`customers_current{suffix}` AS
SELECT s.*
FROM {namespace}.`customers_silver{suffix}` s
JOIN {namespace}.`published_snapshots{suffix}` p
  ON s.snapshot_id = p.snapshot_id
WHERE p.environment = '{environment}';

CREATE OR REPLACE VIEW {namespace}.`customer_contacts{suffix}` AS
SELECT customer_id, name, email, country_code, snapshot_id
FROM {namespace}.`customers_current{suffix}`
WHERE is_contactable = true;

CREATE OR REPLACE VIEW {namespace}.`contactability_current{suffix}` AS
SELECT g.*
FROM {namespace}.`customer_contactability_gold{suffix}` g
JOIN {namespace}.`published_snapshots{suffix}` p
  ON g.snapshot_id = p.snapshot_id
WHERE p.environment = '{environment}';
