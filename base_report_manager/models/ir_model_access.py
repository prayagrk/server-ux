# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    report_ids = fields.Many2many(
        comodel_name="ir.actions.report",
        relation="ir_model_access_report_rel",
        column1="access_id",
        column2="report_id",
        string="Allowed Reports",
        domain="["
        "'|', ('model_id', '=', model_id), "
        "('binding_model_id', '=', model_id)"
        "]",
        ondelete="cascade",
    )
