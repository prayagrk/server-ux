# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import TransactionCase


class TestBaseReportManager(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        polluted_columns = [
            ("res_partner", "autopost_bills"),
            ("res_users", "notification_type"),
        ]
        for table, column in polluted_columns:
            cls.env.cr.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='{table}' AND column_name='{column}'
            """)
            if cls.env.cr.fetchone():
                cls.env.cr.execute(
                    f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"
                )

        cls.model_res_partner = cls.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )

        cls.report_1 = cls.env["ir.actions.report"].create(
            {
                "name": "Test Report 1",
                "model": "res.partner",
                "report_type": "qweb-pdf",
                "report_name": "test.report_1",
                "binding_model_id": cls.model_res_partner.id,
            }
        )
        cls.report_2 = cls.env["ir.actions.report"].create(
            {
                "name": "Test Report 2",
                "model": "res.partner",
                "report_type": "qweb-pdf",
                "report_name": "test.report_2",
                "binding_model_id": cls.model_res_partner.id,
            }
        )

        cls.test_group_1 = cls.env["res.groups"].create({"name": "RM Test Group 1"})
        cls.test_group_2 = cls.env["res.groups"].create({"name": "RM Test Group 2"})

        # Grant read access to the model so get_bindings returns reports
        cls.env["ir.model.access"].create(
            {
                "name": "RM Access Group 1",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.test_group_1.id,
                "perm_read": True,
            }
        )
        cls.env["ir.model.access"].create(
            {
                "name": "RM Access Group 2",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.test_group_2.id,
                "perm_read": True,
            }
        )

        # New model: ir.model.access.report
        cls.access_report_group_1 = cls.env["ir.model.access.report"].create(
            {
                "model_id": cls.model_res_partner.id,
                "group_id": cls.test_group_1.id,
                "report_ids": [Command.set([cls.report_1.id])],
            }
        )

        cls.test_user = cls.env["res.users"].create(
            {
                "name": "RM Test User",
                "login": "rm_test_user_1",
                "groups_id": [Command.set([cls.test_group_1.id])],
            }
        )

    def test_get_bindings_no_restrictions_returns_unfiltered(self):
        """If no restrictions are configured on the model, return all bound reports."""
        self.access_report_group_1.unlink()
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        report_ids = [r.get("id") for r in bindings.get("report", [])]
        self.assertIn(self.report_1.id, report_ids)
        self.assertIn(self.report_2.id, report_ids)

    def test_get_bindings_superuser_bypasses_filter(self):
        """Superuser sees all bound reports regardless of access rules."""
        bindings = self.env["ir.actions.actions"].sudo().get_bindings("res.partner")
        report_ids = [r.get("id") for r in bindings.get("report", [])]
        self.assertIn(self.report_1.id, report_ids)
        self.assertIn(self.report_2.id, report_ids)

    def test_get_bindings_user_sees_own_group_reports(self):
        """User sees only reports from their own groups when restrictions are active."""
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        report_ids = [r.get("id") for r in bindings.get("report", [])]
        self.assertIn(self.report_1.id, report_ids)
        self.assertNotIn(self.report_2.id, report_ids)

    def test_get_bindings_all_reports_denied_removes_report_key(self):
        """When all reports are denied (i.e. model is restricted, but user has
        no allowed reports), the 'report' key is removed.
        """
        # User is in group 2 which has no allowed reports
        self.test_user.groups_id = [Command.set([self.test_group_2.id])]
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        self.assertNotIn("report", bindings)

    def test_get_bindings_actions_not_affected(self):
        """Action filtering is not affected by report manager."""
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        self.assertIsInstance(bindings, dict)
