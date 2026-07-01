# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from . import models
from odoo import Command


def post_init_hook(env):
    """
    Populate server_action_ids and window_action_ids for all existing
    ir.model.access records so that existing action access is preserved
    upon module installation.
    """
    access_records = env["ir.model.access"].search([])

    if not access_records:
        return

    model_ids = access_records.mapped("model_id").ids

    all_server_actions = env["ir.actions.server"].search(
        [("binding_model_id", "in", model_ids)]
    )
    all_window_actions = env["ir.actions.act_window"].search(
        [("binding_model_id", "in", model_ids)]
    )

    server_by_model = {}
    for action in all_server_actions:
        server_by_model.setdefault(action.binding_model_id.id, []).append(action.id)

    window_by_model = {}
    for action in all_window_actions:
        window_by_model.setdefault(action.binding_model_id.id, []).append(action.id)

    for acc in access_records:
        mid = acc.model_id.id
        if mid in server_by_model:
            acc.server_action_ids = [Command.set(server_by_model[mid])]
        if mid in window_by_model:
            acc.window_action_ids = [Command.set(window_by_model[mid])]
