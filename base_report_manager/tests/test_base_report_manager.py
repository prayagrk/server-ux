# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import TransactionCase

from odoo.addons.base_report_manager import post_init_hook


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

        cls.test_group_1 = cls.env["res.groups"].create({"name": "Test Group 1"})
        cls.test_group_2 = cls.env["res.groups"].create({"name": "Test Group 2"})

        cls.access_group_1 = cls.env["ir.model.access"].create(
            {
                "name": "Access Group 1",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.test_group_1.id,
                "perm_read": True,
                "report_ids": [Command.set([cls.report_1.id])],
            }
        )
        cls.access_group_2 = cls.env["ir.model.access"].create(
            {
                "name": "Access Group 2",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.test_group_2.id,
                "perm_read": True,
                "report_ids": [Command.set([cls.report_2.id])],
            }
        )

        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user_report_1",
                "groups_id": [Command.set([cls.test_group_1.id])],
                "bypass_role_policy": False,
            }
        )

        cls.role1 = cls.env["res.users.role"].create(
            {
                "name": "Role 1",
                "implied_ids": [Command.set([cls.test_group_1.id])],
            }
        )
        cls.role2 = cls.env["res.users.role"].create(
            {
                "name": "Role 2",
                "implied_ids": [Command.set([cls.test_group_2.id])],
            }
        )

    def test_post_init_hook(self):
        access = self.env["ir.model.access"].create(
            {
                "name": "Access Empty",
                "model_id": self.model_res_partner.id,
                "group_id": self.test_group_1.id,
                "perm_read": True,
            }
        )
        self.assertFalse(access.report_ids)

        post_init_hook(self.env)

        self.assertTrue(self.report_1 in access.report_ids)
        self.assertTrue(self.report_2 in access.report_ids)

    def test_parse_model_access(self):
        access_records = self.role1._get_implied_model_access_records()
        permissions = self.role1.parse_model_access(
            access_records, {"perm_read": False}
        )

        self.assertIn(self.model_res_partner.id, permissions)
        report_ids_command = permissions[self.model_res_partner.id].get("report_ids")
        self.assertTrue(report_ids_command)
        self.assertEqual(report_ids_command[0][0], 6)
        self.assertIn(self.report_1.id, report_ids_command[0][2])

    def test_get_bindings_superuser(self):
        bindings = self.env["ir.actions.actions"].sudo().get_bindings("res.partner")
        report_ids = [r.get("id") for r in bindings.get("report", [])]
        self.assertIn(self.report_1.id, report_ids)
        self.assertIn(self.report_2.id, report_ids)

    def test_get_bindings_bypass_role(self):
        self.test_user.bypass_role_policy = True
        self.test_user.groups_id = [Command.set([self.test_group_1.id])]

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        report_ids = [r.get("id") for r in bindings.get("report", [])]

        self.assertIn(self.report_1.id, report_ids)
        self.assertNotIn(self.report_2.id, report_ids)

    def test_get_bindings_active_roles(self):
        self.test_user.bypass_role_policy = False
        self.test_user.role_line_ids = [
            Command.create({"role_id": self.role2.id, "is_enabled": True})
        ]

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        report_ids = [r.get("id") for r in bindings.get("report", [])]

        self.assertNotIn(self.report_1.id, report_ids)
        self.assertIn(self.report_2.id, report_ids)

    def test_get_bindings_no_groups(self):
        self.test_user.groups_id = [Command.clear()]
        self.test_user.role_line_ids.unlink()

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        report_ids = [r.get("id") for r in bindings.get("report", [])]
        self.assertIn(self.report_1.id, report_ids)
        self.assertIn(self.report_2.id, report_ids)
