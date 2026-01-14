# Copyright 2025 Kencove (https://www.kencove.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = [
        "account.move",
        "payment.portal.link.mixin",
    ]

    def _get_portal_return_action(self):
        self.ensure_one()
        return self.env.ref("account.action_move_out_invoice_type")

    def portal_link_register_payment(self):
        return self.with_context(
            force_partner_id=self.partner_id.id
        )._get_portal_payment_link()
