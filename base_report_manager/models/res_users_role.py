# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    def parse_model_access(self, model_access, perm_fields):
        model_permissions = super().parse_model_access(model_access, perm_fields)

        for acc in model_access:
            model_id = acc.model_id.id

            if "report_ids" not in model_permissions[model_id]:
                model_permissions[model_id]["report_ids"] = set()

            model_permissions[model_id]["report_ids"].update(acc.report_ids.ids)

        for _model_id, perms in model_permissions.items():
            if "report_ids" in perms:
                perms["report_ids"] = [Command.set(list(perms["report_ids"]))]

        return model_permissions
