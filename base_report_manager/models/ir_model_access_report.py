# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrModelAccessReport(models.Model):
    _name = "ir.model.access.report"
    _description = "Model Report Access"
    _order = "model_id"

    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
    )
    group_id = fields.Many2one(
        comodel_name="res.groups",
        string="Group",
        ondelete="cascade",
    )
    report_ids = fields.Many2many(
        comodel_name="ir.actions.report",
        relation="ir_model_access_report_action_report_rel",
        column1="access_id",
        column2="report_id",
        string="Allowed Reports",
        domain="["
        "'|', ('model_id', '=', model_id), "
        "('binding_model_id', '=', model_id)"
        "]",
        ondelete="cascade",
    )
