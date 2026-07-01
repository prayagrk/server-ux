# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrActionsActions(models.Model):
    _inherit = "ir.actions.actions"

    @api.model
    def get_bindings(self, model_name):
        result = super().get_bindings(model_name)

        # Bypass checks for the superuser
        if self.env.is_superuser():
            return result

        current_user = self.env.user

        if getattr(current_user, "bypass_role_policy", False):
            group_ids = current_user.groups_id.ids
        else:
            active_lines = current_user.role_line_ids.filtered(
                lambda line: line.is_enabled
            )
            roles = active_lines.mapped("role_id")
            if roles:
                group_ids = roles.mapped("group_id").ids
            else:
                group_ids = current_user.groups_id.ids

        if not group_ids:
            return result

        access_records = (
            self.env["ir.model.access"]
            .sudo()
            .search(
                [
                    ("model_id.model", "=", model_name),
                    ("group_id", "in", group_ids),
                ]
            )
        )

        if not access_records:
            return result

        allowed_action_ids = (
            access_records.mapped("server_action_ids").ids
            + access_records.mapped("window_action_ids").ids
        )

        filtered_result = dict(result)

        if "action" in filtered_result:
            filtered_result["action"] = [
                act
                for act in filtered_result["action"]
                if act.get("id") in allowed_action_ids
            ]
            if not filtered_result["action"]:
                filtered_result.pop("action")

        return filtered_result
