# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import AccessError


class IrActionsActions(models.Model):
    _inherit = "ir.actions.actions"

    def _is_action_restricted(self):
        """Returns True if the current action is restricted for the current user,
        taking group privilege inheritance into account.
        """
        self.ensure_one()
        if self.env.is_superuser():
            return False

        if (
            hasattr(super(), "_is_action_restricted")
            and super()._is_action_restricted()
        ):
            return True

        user = self.env.user
        action_sudo = self.sudo()
        action_type = action_sudo.type or action_sudo._name

        res_groups_sudo = self.env["res.groups"].sudo()
        if action_type == "ir.actions.report":
            explicit_restricting = res_groups_sudo.search(
                [("restricted_report_action_ids", "in", action_sudo.ids)]
            )
        else:
            explicit_restricting = res_groups_sudo.search(
                [
                    ("restricted_report_action_ids", "in", action_sudo.ids),
                ]
            )

        if not explicit_restricting:
            return False

        all_restricted_groups = (
            explicit_restricting | explicit_restricting._get_transitive_implied()
        )

        user_groups = user.sudo().groups_id
        user_restricted_groups = user_groups & all_restricted_groups

        if not user_restricted_groups:
            return False

        non_restricting_groups = user_groups - all_restricted_groups
        non_restricting_implied = non_restricting_groups._get_transitive_implied()
        if user_restricted_groups & non_restricting_implied:
            return False

        return True

    def _check_action_restrictions(self):
        """Raises AccessError if any action in self is restricted.

        For the current user.
        """
        for action in self:
            if action._is_action_restricted():
                raise AccessError(
                    _(
                        "You are not allowed to access this action because it "
                        "is restricted for one of your user groups."
                    )
                )

    def _get_action_dict(self):
        """Verify restrictions before loading action details for execution."""
        self._check_action_restrictions()
        return super()._get_action_dict()

    @api.model
    def get_bindings(self, model_name):
        """Filter out restricted reports from print sidebar and bindings."""
        result = super().get_bindings(model_name)
        if self.env.is_superuser():
            return result

        filtered_result = dict(result)
        if "report" in filtered_result:
            report_ids = [
                rep.get("id") for rep in filtered_result["report"] if rep.get("id")
            ]
            if report_ids:
                reports = self.browse(report_ids)
                restricted_report_ids = {
                    report.id for report in reports if report._is_action_restricted()
                }
                if restricted_report_ids:
                    filtered_result["report"] = [
                        rep
                        for rep in filtered_result["report"]
                        if rep.get("id") not in restricted_report_ids
                    ]
                    if not filtered_result["report"]:
                        filtered_result.pop("report")

        return filtered_result
