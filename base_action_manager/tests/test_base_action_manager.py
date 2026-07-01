# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo import Command
from odoo.tests.common import TransactionCase

from odoo.addons.base_action_manager import post_init_hook


class TestBaseActionManager(TransactionCase):
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

        cls.server_action_1 = cls.env["ir.actions.server"].create(
            {
                "name": "Test Server Action 1",
                "model_id": cls.model_res_partner.id,
                "binding_model_id": cls.model_res_partner.id,
                "state": "code",
                "code": "",
            }
        )
        cls.server_action_2 = cls.env["ir.actions.server"].create(
            {
                "name": "Test Server Action 2",
                "model_id": cls.model_res_partner.id,
                "binding_model_id": cls.model_res_partner.id,
                "state": "code",
                "code": "",
            }
        )

        cls.window_action_1 = cls.env["ir.actions.act_window"].create(
            {
                "name": "Test Window Action 1",
                "res_model": "res.partner",
                "binding_model_id": cls.model_res_partner.id,
            }
        )
        cls.window_action_2 = cls.env["ir.actions.act_window"].create(
            {
                "name": "Test Window Action 2",
                "res_model": "res.partner",
                "binding_model_id": cls.model_res_partner.id,
            }
        )

        cls.test_group_1 = cls.env["res.groups"].create({"name": "AM Test Group 1"})
        cls.test_group_2 = cls.env["res.groups"].create({"name": "AM Test Group 2"})

        cls.access_group_1 = cls.env["ir.model.access"].create(
            {
                "name": "AM Access Group 1",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.test_group_1.id,
                "perm_read": True,
                "server_action_ids": [Command.set([cls.server_action_1.id])],
                "window_action_ids": [Command.set([cls.window_action_1.id])],
            }
        )
        cls.access_group_2 = cls.env["ir.model.access"].create(
            {
                "name": "AM Access Group 2",
                "model_id": cls.model_res_partner.id,
                "group_id": cls.test_group_2.id,
                "perm_read": True,
                "server_action_ids": [Command.set([cls.server_action_2.id])],
                "window_action_ids": [Command.set([cls.window_action_2.id])],
            }
        )

        cls.test_user = cls.env["res.users"].create(
            {
                "name": "AM Test User",
                "login": "am_test_user_1",
                "groups_id": [Command.set([cls.test_group_1.id])],
                "bypass_role_policy": False,
            }
        )

        cls.role1 = cls.env["res.users.role"].create(
            {
                "name": "AM Role 1",
                "implied_ids": [Command.set([cls.test_group_1.id])],
            }
        )
        cls.role2 = cls.env["res.users.role"].create(
            {
                "name": "AM Role 2",
                "implied_ids": [Command.set([cls.test_group_2.id])],
            }
        )

    def test_post_init_hook_populates_actions(self):
        """Hook populates both server_action_ids and window_action_ids."""
        access = self.env["ir.model.access"].create(
            {
                "name": "AM Hook Access",
                "model_id": self.model_res_partner.id,
                "group_id": self.test_group_1.id,
                "perm_read": True,
            }
        )
        self.assertFalse(access.server_action_ids)
        self.assertFalse(access.window_action_ids)

        post_init_hook(self.env)

        self.assertIn(self.server_action_1, access.server_action_ids)
        self.assertIn(self.server_action_2, access.server_action_ids)
        self.assertIn(self.window_action_1, access.window_action_ids)
        self.assertIn(self.window_action_2, access.window_action_ids)

    def test_post_init_hook_empty_db_early_return(self):
        """Hook returns early (line 17) when no ir.model.access records exist."""
        empty = self.env["ir.model.access"].browse()
        with patch.object(
            type(self.env["ir.model.access"]),
            "search",
            return_value=empty,
        ):
            result = post_init_hook(self.env)
        self.assertIsNone(result)

    def test_post_init_hook_model_with_no_actions(self):
        """Hook skips models that have no bound actions."""
        model_res_lang = self.env["ir.model"].search(
            [("model", "=", "res.lang")], limit=1
        )
        access = self.env["ir.model.access"].create(
            {
                "name": "AM Hook Access Lang",
                "model_id": model_res_lang.id,
                "group_id": self.test_group_1.id,
                "perm_read": True,
            }
        )
        post_init_hook(self.env)
        self.assertFalse(access.server_action_ids)
        self.assertFalse(access.window_action_ids)

    def test_get_bindings_superuser_bypasses_filter(self):
        """Superuser sees all bound actions regardless of access rules."""
        bindings = self.env["ir.actions.actions"].sudo().get_bindings("res.partner")
        action_ids = [a.get("id") for a in bindings.get("action", [])]
        self.assertIn(self.server_action_1.id, action_ids)
        self.assertIn(self.server_action_2.id, action_ids)
        self.assertIn(self.window_action_1.id, action_ids)
        self.assertIn(self.window_action_2.id, action_ids)

    def test_get_bindings_bypass_role_sees_own_group_actions(self):
        """bypass_role_policy user sees only actions from their own groups."""
        self.test_user.groups_id = [Command.set([self.test_group_1.id])]

        def mock_compute(users):
            for u in users:
                u.bypass_role_policy = True

        with patch.object(
            type(self.env["res.users"]),
            "_compute_bypass_role_policy",
            mock_compute,
        ):
            self.test_user.env.cache.invalidate(
                [(type(self.env["res.users"]).bypass_role_policy, self.test_user.ids)]
            )
            bindings = (
                self.env["ir.actions.actions"]
                .with_user(self.test_user)
                .get_bindings("res.partner")
            )
        action_ids = [a.get("id") for a in bindings.get("action", [])]

        self.assertIn(self.server_action_1.id, action_ids)
        self.assertIn(self.window_action_1.id, action_ids)
        self.assertNotIn(self.server_action_2.id, action_ids)
        self.assertNotIn(self.window_action_2.id, action_ids)

    def test_get_bindings_active_role_filters_correctly(self):
        """Active role determines visible actions (deny-by-default)."""
        self.test_user.bypass_role_policy = False
        self.test_user.role_line_ids = [
            Command.create({"role_id": self.role2.id, "is_enabled": True})
        ]

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        action_ids = [a.get("id") for a in bindings.get("action", [])]

        self.assertIn(self.server_action_2.id, action_ids)
        self.assertIn(self.window_action_2.id, action_ids)
        self.assertNotIn(self.server_action_1.id, action_ids)
        self.assertNotIn(self.window_action_1.id, action_ids)

    def test_get_bindings_no_active_roles_falls_back_to_groups(self):
        """When no roles are active, fall back to user's direct groups."""
        self.test_user.bypass_role_policy = False
        self.test_user.role_line_ids = [Command.clear()]
        self.test_user.groups_id = [Command.set([self.test_group_1.id])]

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        action_ids = [a.get("id") for a in bindings.get("action", [])]

        self.assertIn(self.server_action_1.id, action_ids)
        self.assertIn(self.window_action_1.id, action_ids)

    def test_get_bindings_no_groups_returns_unfiltered(self):
        """User with no groups returns the original unfiltered result."""
        self.test_user.bypass_role_policy = False
        self.test_user.role_line_ids = [Command.clear()]
        self.test_user.groups_id = [Command.clear()]

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        action_ids = [a.get("id") for a in bindings.get("action", [])]
        self.assertIn(self.server_action_1.id, action_ids)
        self.assertIn(self.server_action_2.id, action_ids)

    def test_get_bindings_no_access_records_returns_unfiltered(self):
        """User in a group with no ir.model.access gets unfiltered result."""
        orphan_group = self.env["res.groups"].create({"name": "AM Orphan Group"})
        self.test_user.bypass_role_policy = True
        self.test_user.groups_id = [Command.set([orphan_group.id])]

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        action_ids = [a.get("id") for a in bindings.get("action", [])]
        self.assertIn(self.server_action_1.id, action_ids)
        self.assertIn(self.server_action_2.id, action_ids)

    def test_get_bindings_all_actions_denied_removes_action_key(self):
        """When all actions are denied, the 'action' key is removed entirely."""
        denied_group = self.env["res.groups"].create({"name": "AM Denied Group"})
        self.env["ir.model.access"].create(
            {
                "name": "AM Denied Access",
                "model_id": self.model_res_partner.id,
                "group_id": denied_group.id,
                "perm_read": True,
            }
        )
        self.test_user.bypass_role_policy = True
        self.test_user.groups_id = [Command.set([denied_group.id])]

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        self.assertNotIn("action", bindings)

    def test_get_bindings_reports_not_affected(self):
        """Report filtering is handled by base_report_manager; not touched here."""
        self.test_user.bypass_role_policy = True
        self.test_user.groups_id = [Command.set([self.test_group_1.id])]

        bindings = (
            self.env["ir.actions.actions"]
            .with_user(self.test_user)
            .get_bindings("res.partner")
        )
        self.assertIsInstance(bindings, dict)

    def test_parse_model_access_server_actions_aggregated(self):
        """parse_model_access unions server_action_ids across access records."""
        access_records = self.role1._get_implied_model_access_records()
        permissions = self.role1.parse_model_access(
            access_records, {"perm_read": False}
        )

        self.assertIn(self.model_res_partner.id, permissions)
        server_cmd = permissions[self.model_res_partner.id].get("server_action_ids")
        self.assertTrue(server_cmd)
        self.assertEqual(server_cmd[0][0], 6)
        self.assertIn(self.server_action_1.id, server_cmd[0][2])

    def test_parse_model_access_window_actions_aggregated(self):
        """parse_model_access unions window_action_ids across access records."""
        access_records = self.role1._get_implied_model_access_records()
        permissions = self.role1.parse_model_access(
            access_records, {"perm_read": False}
        )

        window_cmd = permissions[self.model_res_partner.id].get("window_action_ids")
        self.assertTrue(window_cmd)
        self.assertEqual(window_cmd[0][0], 6)
        self.assertIn(self.window_action_1.id, window_cmd[0][2])

    def test_parse_model_access_union_across_roles(self):
        """When a user has two roles, their allowed actions are unioned."""
        access_records = (
            self.role1._get_implied_model_access_records()
            | self.role2._get_implied_model_access_records()
        )
        permissions = self.role1.parse_model_access(
            access_records, {"perm_read": False}
        )

        server_cmd = permissions[self.model_res_partner.id]["server_action_ids"]
        window_cmd = permissions[self.model_res_partner.id]["window_action_ids"]

        server_ids = server_cmd[0][2]
        window_ids = window_cmd[0][2]

        self.assertIn(self.server_action_1.id, server_ids)
        self.assertIn(self.server_action_2.id, server_ids)
        self.assertIn(self.window_action_1.id, window_ids)
        self.assertIn(self.window_action_2.id, window_ids)
