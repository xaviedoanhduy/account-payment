# Copyright 2025 Kencove (https://www.kencove.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = [
        "sale.order",
        "payment.portal.link.mixin",
    ]

    has_to_be_paid = fields.Boolean(compute="_compute_has_to_be_paid", store=True)

    @api.depends(
        "transaction_ids.state",
        "amount_total",
        "is_expired",
        "state",
        "require_payment",
    )
    def _compute_has_to_be_paid(self):
        for order in self:
            order.has_to_be_paid = order._has_to_be_paid(True)

    def portal_link_register_payment(self):
        return self.with_context(
            force_partner_id=self.partner_id.id
        )._get_portal_payment_link()
