# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResGroups(models.Model):
    _inherit = "res.groups"

    restricted_report_action_ids = fields.Many2many(
        comodel_name="ir.actions.report",
        relation="res_groups_restricted_report_action_rel",
        column1="gid",
        column2="act_id",
        string="Restricted Report Actions",
        domain="[('groups_id', '=', False)]",
        help="Report actions restricted for members of this group.",
    )

    def _get_transitive_implied(self, visited=None):
        """Recursively fetches all groups implied by the current recordset."""
        if visited is None:
            visited = set()

        user_type_category = self.env.ref(
            "base.module_category_user_type", raise_if_not_found=False
        )
        user_type_group_ids = []
        if user_type_category:
            user_type_group_ids = (
                self.env["res.groups"]
                .search([("category_id", "=", user_type_category.id)])
                .ids
            )

        res = self.env["res.groups"]
        for record in self:
            if record.id in visited:
                continue
            visited.add(record.id)

            if record.id in user_type_group_ids:
                continue

            valid_implied = record.implied_ids.filtered(
                lambda g: g.id not in user_type_group_ids
            )
            res |= valid_implied
            res |= valid_implied._get_transitive_implied(visited)

        return res

    def write(self, vals):
        res = super().write(vals)
        if "restricted_report_action_ids" in vals:
            self.env.registry.clear_cache()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for vals in vals_list:
            if "restricted_report_action_ids" in vals:
                self.env.registry.clear_cache()
                break
        return records
