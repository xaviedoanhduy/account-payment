# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    def write(self, vals):
        res = super().write(vals)
        if vals.get("discount_days"):
            for term in self:
                # get all invoice related to this payment term and update
                # validity discount date
                invoices = self.env["account.move"].search(
                    [
                        ("state", "=", "posted"),
                        ("invoice_payment_term_id", "=", term.id),
                    ]
                )
                for inv in invoices:
                    # Check payment date discount validation
                    # Update discount validity days
                    inv.discount_date = inv.invoice_date + relativedelta(
                        days=vals.get("discount_days")
                    )
        return res
