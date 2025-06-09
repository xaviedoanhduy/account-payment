# Copyright 2025 Kencove (https://www.kencove.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PaymentLinkWizard(models.TransientModel):
    _inherit = "payment.link.wizard"

    def _get_additional_link_values(self):
        link_values = super()._get_additional_link_values()
        if self._context.get("force_partner_id"):
            link_values.update(
                {
                    "partner_id": self._context.get("force_partner_id"),
                    "force_override_partner": True,
                }
            )
        return link_values
