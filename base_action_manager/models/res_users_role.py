# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    def parse_model_access(self, model_access, perm_fields):
        model_permissions = super().parse_model_access(model_access, perm_fields)

        for acc in model_access:
            model_id = acc.model_id.id

            if "server_action_ids" not in model_permissions[model_id]:
                model_permissions[model_id]["server_action_ids"] = set()
            if "window_action_ids" not in model_permissions[model_id]:
                model_permissions[model_id]["window_action_ids"] = set()

            # Union: all allowed actions across all access rules for this model
            model_permissions[model_id]["server_action_ids"].update(
                acc.server_action_ids.ids
            )
            model_permissions[model_id]["window_action_ids"].update(
                acc.window_action_ids.ids
            )

        for _model_id, perms in model_permissions.items():
            if "server_action_ids" in perms:
                perms["server_action_ids"] = [
                    Command.set(list(perms["server_action_ids"]))
                ]
            if "window_action_ids" in perms:
                perms["window_action_ids"] = [
                    Command.set(list(perms["window_action_ids"]))
                ]

        return model_permissions
