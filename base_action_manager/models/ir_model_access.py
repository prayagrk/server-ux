# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    server_action_ids = fields.Many2many(
        comodel_name="ir.actions.server",
        relation="ir_model_access_server_action_rel",
        column1="access_id",
        column2="server_action_id",
        string="Allowed Server Actions",
        domain="[('binding_model_id', '=', model_id)]",
        ondelete="cascade",
    )

    window_action_ids = fields.Many2many(
        comodel_name="ir.actions.act_window",
        relation="ir_model_access_window_action_rel",
        column1="access_id",
        column2="window_action_id",
        string="Allowed Window Actions",
        domain="[('binding_model_id', '=', model_id)]",
        ondelete="cascade",
    )
