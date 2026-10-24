import unittest
from unittest.mock import patch

from _support import ROOT
from clientes_confiables.databricks_groups import ensure_account_groups


class AccountGroupTests(unittest.TestCase):
    def test_create_and_repeat_does_not_add_members(self):
        created = []
        calls = []

        def request(method, query="", payload=None):
            calls.append((method, payload))
            if method == "GET":
                return {"Resources": [{"id": str(i), "displayName": name} for i, name in enumerate(created)]}
            self.assertEqual(method, "POST")
            self.assertNotIn("members", payload)
            self.assertNotIn("roles", payload)
            created.append(payload["displayName"])
            return {"id": str(len(created)), "displayName": payload["displayName"]}

        groups = {"a": "fixture_engineering", "b": "fixture_bi"}
        ensure_account_groups(groups, request)
        ensure_account_groups(groups, request)
        self.assertEqual(created, list(groups.values()))
        self.assertEqual(sum(method == "POST" for method, _ in calls), 2)

    def test_permission_failure_is_not_treated_as_success(self):
        def request(method, query="", payload=None):
            raise ValueError("GROUP_PROVISIONING_DENIED")
        with self.assertRaisesRegex(ValueError, "GROUP_PROVISIONING_DENIED"):
            ensure_account_groups({"a": "fixture_group"}, request)

    def test_post_requires_followup_verification(self):
        def request(method, query="", payload=None):
            return {"Resources": []} if method == "GET" else {"id": "1"}
        with self.assertRaisesRegex(ValueError, "ACCOUNT_GROUP_NOT_VERIFIED"):
            ensure_account_groups({"a": "fixture_group"}, request)

    def test_duplicate_matching_names_fail(self):
        def request(method, query="", payload=None):
            return {"Resources": [{"displayName": "fixture_group"}] * 2}
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_ACCOUNT_GROUP"):
            ensure_account_groups({"a": "fixture_group"}, request)
