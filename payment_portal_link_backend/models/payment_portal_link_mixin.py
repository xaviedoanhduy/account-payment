# Copyright 2025 Kencove (https://www.kencove.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PortalPaymentMixin(models.AbstractModel):
    _name = "payment.portal.link.mixin"
    _description = "Payment Portal Link Mixin"

    def _get_portal_payment_link(self):
        self.ensure_one()
        wizard = (
            self.env["payment.link.wizard"]
            .with_context(
                active_model=self._name,
                active_id=self.id,
                **self._context,
            )
            .create({})
        )
        return {
            "type": "ir.actions.act_url",
            "url": wizard.link,
            "target": "self",
        }
