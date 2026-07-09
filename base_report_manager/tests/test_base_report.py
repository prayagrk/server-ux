# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestBaseReport(TransactionCase):
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

        cls.group_user = cls.env.ref("base.group_user")

        cls.child_group = cls.env["res.groups"].create(
            {
                "name": "User: Own Documents Only",
                "implied_ids": [Command.link(cls.group_user.id)],
            }
        )
        cls.parent_group = cls.env["res.groups"].create(
            {
                "name": "User: All Documents",
                "implied_ids": [Command.link(cls.child_group.id)],
            }
        )

        cls.unrelated_group = cls.env["res.groups"].create(
            {
                "name": "Project / User",
                "implied_ids": [Command.link(cls.group_user.id)],
            }
        )

        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Test Report User",
                "login": "test_report_user",
                "groups_id": [Command.set([cls.env.ref("base.group_system").id])],
            }
        )

        cls.model_res_partner = cls.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )

        cls.report_action = cls.env["ir.actions.report"].create(
            {
                "name": "Test Report",
                "model": "res.partner",
                "binding_model_id": cls.model_res_partner.id,
                "report_name": "test_report",
                "report_type": "qweb-pdf",
            }
        )

    def test_fields_domain(self):
        """Test that domain only allows reports with no native groups."""
        self.assertEqual(
            self.env["res.groups"]._fields["restricted_report_action_ids"].domain,
            "[('groups_id', '=', False)]",
        )

    def test_restricted_report_inheritance(self):
        """Test that restricting a report hides it from bindings."""
        self.child_group.write(
            {"restricted_report_action_ids": [Command.link(self.report_action.id)]}
        )
        self.test_user.write(
            {
                "groups_id": [
                    Command.set(
                        [self.parent_group.id, self.env.ref("base.group_system").id]
                    )
                ]
            }
        )
        self.report_action.with_user(self.test_user)._get_action_dict()
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        report_bindings = [r["id"] for r in bindings.get("report", [])]
        self.assertIn(self.report_action.id, report_bindings)

        self.child_group.write(
            {"restricted_report_action_ids": [Command.unlink(self.report_action.id)]}
        )
        self.parent_group.write(
            {"restricted_report_action_ids": [Command.link(self.report_action.id)]}
        )
        with self.assertRaises(AccessError):
            self.report_action.with_user(self.test_user)._get_action_dict()

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        report_bindings = [r["id"] for r in bindings.get("report", [])]
        self.assertNotIn(self.report_action.id, report_bindings)

        self.test_user.write(
            {
                "groups_id": [
                    Command.set(
                        [
                            self.child_group.id,
                            self.unrelated_group.id,
                            self.env.ref("base.group_system").id,
                        ]
                    )
                ]
            }
        )

        with self.assertRaises(AccessError):
            self.report_action.with_user(self.test_user)._get_action_dict()

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        report_bindings = [r["id"] for r in bindings.get("report", [])]
        self.assertNotIn(self.report_action.id, report_bindings)

    def test_superuser_bypass(self):
        """Superuser bypasses restrictions entirely."""
        self.child_group.write(
            {"restricted_report_action_ids": [Command.link(self.report_action.id)]}
        )
        root_user = self.env.ref("base.user_root") or self.env.user.browse(1)
        self.report_action.with_user(root_user)._check_action_restrictions()
        self.assertFalse(
            self.report_action.with_user(root_user)._is_action_restricted()
        )
        bindings = (
            self.env["ir.actions.actions"]
            .with_user(root_user)
            .get_bindings("res.partner")
        )
        report_bindings = [r["id"] for r in bindings.get("report", [])]
        self.assertIn(self.report_action.id, report_bindings)

    def test_create_group_clears_cache(self):
        """Creating a group with restricted actions clears the registry cache."""
        self.env["res.groups"].create(
            {
                "name": "Test Cache Clear Group",
                "restricted_report_action_ids": [Command.link(self.report_action.id)],
            }
        )

    def test_no_group_overlap(self):
        """User has no group overlap with the restricted group."""
        self.child_group.write(
            {"restricted_report_action_ids": [Command.link(self.report_action.id)]}
        )
        self.test_user.write(
            {
                "groups_id": [
                    Command.set(
                        [
                            self.unrelated_group.id,
                            self.env.ref("base.group_system").id,
                        ]
                    )
                ]
            }
        )
        self.assertFalse(
            self.report_action.with_user(self.test_user)._is_action_restricted()
        )

    def test_get_bindings_filtering_pop(self):
        """Test that report key is popped when all report bindings are restricted."""
        self.child_group.write(
            {"restricted_report_action_ids": [Command.link(self.report_action.id)]}
        )
        self.test_user.write(
            {
                "groups_id": [
                    Command.set(
                        [self.child_group.id, self.env.ref("base.group_system").id]
                    )
                ]
            }
        )

        import unittest.mock as mock

        mock_result = {"report": [{"id": self.report_action.id, "name": "Test Report"}]}
        with mock.patch(
            "odoo.addons.base.models.ir_actions.IrActions.get_bindings",
            return_value=mock_result,
        ):
            bindings = (
                self.env["ir.actions.actions"]
                .with_user(self.test_user)
                .get_bindings("res.partner")
            )
            self.assertNotIn("report", bindings)

    def test_superclass_restriction(self):
        """If a superclass restricts the action, it is restricted."""
        patched_classes = []
        mro = self.report_action.__class__.__mro__
        start_idx = 0
        for idx, cls in enumerate(mro):
            if cls.__name__ == "IrActionsActions":
                start_idx = idx + 1
                break

        for cls in mro[start_idx:]:
            if cls is not object:
                type.__setattr__(cls, "_is_action_restricted", lambda self: True)
                patched_classes.append(cls)

        try:
            self.assertTrue(
                self.report_action.with_user(self.test_user)._is_action_restricted()
            )
        finally:
            for cls in patched_classes:
                if hasattr(cls, "_is_action_restricted"):
                    type.__delattr__(cls, "_is_action_restricted")
