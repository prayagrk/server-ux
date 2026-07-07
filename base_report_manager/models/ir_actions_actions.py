# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class IrActionsActions(models.Model):
    _inherit = "ir.actions.actions"

    def _get_report_manager_group_ids(self):
        """Helper to get group IDs for report check."""
        return self.env.user.groups_id.ids

    @api.model
    def get_bindings(self, model_name):
        result = super().get_bindings(model_name)
        # Bypass checks for the superuser
        if self.env.is_superuser():
            return result

        access_report_model = self.env["ir.model.access.report"].sudo()
        has_restrictions = (
            access_report_model.search_count([("model_id.model", "=", model_name)]) > 0
        )
        if not has_restrictions:
            return result

        group_ids = self._get_report_manager_group_ids()

        access_records = access_report_model.search(
            [
                ("model_id.model", "=", model_name),
                "|",
                ("group_id", "=", False),
                ("group_id", "in", group_ids),
            ]
        )
        allowed_report_ids = access_records.mapped("report_ids").ids
        filtered_result = dict(result)

        if "report" in filtered_result:
            filtered_result["report"] = [
                act
                for act in filtered_result["report"]
                if act.get("id") in allowed_report_ids
            ]
            if not filtered_result["report"]:
                filtered_result.pop("report")

        return filtered_result
