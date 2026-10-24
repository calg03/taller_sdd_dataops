import json
import unittest
from unittest.mock import MagicMock, patch

from _support import ROOT
from clientes_confiables.model_contract import assert_table, contracts, table_name
from clientes_confiables.model_deployment import deploy_model
from clientes_confiables.model_permissions import configured_groups
from clientes_confiables.project_config import object_suffix, sql_context


class DeploymentTests(unittest.TestCase):
    def test_only_numeric_pr_suffix(self):
        self.assertEqual(object_suffix(12), "__pr_12")
        for value in ("0", "-1", "1;DROP TABLE x", "1`", "001", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                object_suffix(value)
        context = sql_context(12)
        for name in contracts():
            self.assertTrue(table_name(context, name).endswith("__pr_12`"))
        with self.assertRaises(ValueError):
            table_name(context, "arbitrary_table")

    def test_exact_contract_and_mismatch_are_detected(self):
        cursor = MagicMock()
        expected = contracts()["customers_silver"]
        rows = [(n, t, "YES" if nullable else "NO") for n, t, nullable in expected]
        cursor.fetchall.return_value = rows
        assert_table(cursor, sql_context(1), "customers_silver")
        cursor.fetchall.return_value = [(n, "STRING", nullable) for n, _, nullable in rows]
        with self.assertRaisesRegex(ValueError, "MODEL_CONTRACT_MISMATCH"):
            assert_table(cursor, sql_context(1), "customers_silver")
        cursor.fetchall.return_value = []
        assert_table(cursor, sql_context(1), "customers_silver", allow_missing=True)
        with self.assertRaises(ValueError):
            assert_table(cursor, sql_context(1), "customers_silver")

    def test_incompatible_table_stops_before_ddl_or_seed(self):
        cursor = MagicMock()
        context = dict(sql_context(1), environment="pr_1")
        with patch("clientes_confiables.model_deployment.assert_table", side_effect=ValueError("MODEL_CONTRACT_MISMATCH")):
            with self.assertRaises(ValueError):
                deploy_model(cursor, context, "run", {}, MagicMock())
        self.assertEqual(cursor.execute.call_count, 1)
        self.assertIn("CREATE SCHEMA", cursor.execute.call_args.args[0])

    def test_order_no_client_inserts_and_isolated_reference(self):
        cursor = MagicMock()
        context = dict(sql_context(42), environment="pr_42")
        callback = MagicMock()
        with patch("clientes_confiables.model_deployment.assert_table"), \
             patch("clientes_confiables.model_deployment.validate_model"), \
             patch("clientes_confiables.model_deployment.apply_permissions"), \
             patch("clientes_confiables.model_deployment.validate_permissions"):
            deploy_model(cursor, context, "run", {}, callback)
        callback.assert_called_once()
        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertEqual(sum("CREATE TABLE" in sql for sql in statements), 7)
        seeds = [sql for sql in statements if "MERGE INTO" in sql]
        self.assertEqual(len(seeds), 5)
        self.assertTrue(all("countries_reference__pr_42" in sql for sql in seeds))
        self.assertFalse(any("DROP " in sql or "TRUNCATE " in sql for sql in statements))
        self.assertFalse(any("INSERT INTO" in sql for sql in statements))

    def test_groups_fail_closed_without_real_names(self):
        with patch("clientes_confiables.model_permissions.load_config", return_value={"groups": {}}):
            with self.assertRaisesRegex(ValueError, "ACCESS_GROUPS_NOT_CONFIGURED"):
                configured_groups()
        group_config = {"groups": dict(engineering="e", governance="g", marketing="m", bi="b")}
        with patch("clientes_confiables.model_permissions.load_config", return_value=group_config):
            self.assertEqual(configured_groups()["bi"], "b")

    def test_sql_files_match_versioned_contract(self):
        for name, columns in contracts().items():
            files = list((ROOT / "sql/model").glob(f"*_{name}.sql"))
            self.assertEqual(len(files), 1)
            content = files[0].read_text(encoding="utf-8")
            self.assertIn(name + "{suffix}", content)
            for column, data_type, nullable in columns:
                definition = f"{column} {data_type}" + ("" if nullable else " NOT NULL")
                self.assertIn(definition, content)


class AuditTests(unittest.TestCase):
    def test_stage_audit_uses_parameters_and_stable_key(self):
        from clientes_confiables.stage_audit import record_stage
        cursor = MagicMock()
        context = dict(sql_context(3), environment="pr_3")
        report = {"run_id": "fixture-run", "snapshot_id": "hash", "started_at": "2026-10-23T12:00:00Z",
                  "finished_at": "2026-10-23T12:01:00Z"}
        record_stage(cursor, context, report, "calidad-shift-left", "SUCCESS", report["started_at"])
        sql, parameters = cursor.execute.call_args.args
        self.assertIn("t.run_id = s.run_id", sql)
        self.assertIn("pipeline_stage_runs__pr_3", sql)
        self.assertNotIn("fixture-run", sql)
        self.assertEqual(parameters["run_id"], "fixture-run")
