# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    def _postprocess_access_rights(self, tree):
        """Disable the import action based on the user's
        effective model access rights."""
        target_model = tree.get("model_access_rights")
        tree = super()._postprocess_access_rights(tree)

        if not target_model or tree.tag not in ("list", "kanban"):
            return tree

        user = self.env.user
        if user.bypass_role_policy:
            return tree
        active_roles = user.role_line_ids.filtered(lambda r: r.is_enabled).mapped(
            "role_id"
        )
        if active_roles:
            group_ids = active_roles.mapped("group_id").ids
        else:
            group_ids = user.groups_id.ids
        has_import = (
            self.env["ir.model.access"]
            .sudo()
            .search_count(
                [
                    ("model_id.model", "=", target_model),
                    ("perm_import", "=", True),
                    "|",
                    ("group_id", "=", False),
                    ("group_id", "in", group_ids),
                ]
            )
            > 0
        )

        if not has_import:
            tree.set("import", "0")

        return tree
