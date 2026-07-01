# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from . import models
from odoo import Command


def post_init_hook(env):
    """
    Populate report_ids for all existing ir.model.access records
    to prevent breaking existing report access upon module installation.
    """
    access_records = env["ir.model.access"].search([])

    if not access_records:
        return

    model_ids = access_records.mapped("model_id").ids

    all_reports = env["ir.actions.report"].search(
        [
            "|",
            ("model_id", "in", model_ids),
            ("binding_model_id", "in", model_ids),
        ]
    )

    reports_by_model = {}
    for r in all_reports:
        if r.model_id:
            reports_by_model.setdefault(r.model_id.id, []).append(r.id)
        if r.binding_model_id:
            reports_by_model.setdefault(r.binding_model_id.id, []).append(r.id)

    for mid in reports_by_model:
        reports_by_model[mid] = list(set(reports_by_model[mid]))

    for acc in access_records:
        mid = acc.model_id.id
        if mid in reports_by_model:
            acc.report_ids = [Command.set(reports_by_model[mid])]
