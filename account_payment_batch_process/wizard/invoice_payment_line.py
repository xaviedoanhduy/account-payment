# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
import math

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round

try:
    from num2words import num2words
except ImportError:
    logging.getLogger(__name__).warning(
        "The num2words python library is not installed."
    )
    num2words = None


class InvoicePaymentLine(models.TransientModel):
    _name = "invoice.payment.line"
    _description = "Invoice Payment Line"
    _rec_name = "invoice_id"
    _check_company_auto = True

    @api.depends("amount")
    def _compute_payment_difference(self):
        for rec in self:
            rec.payment_difference = rec.balance - rec.amount

    invoice_id = fields.Many2one(
        "account.move", string="Supplier Invoice", required=True
    )
    partner_id = fields.Many2one("res.partner", string="Supplier Name", required=True)
    balance = fields.Float("Balance Amount", required=True)
    wizard_id = fields.Many2one("account.payment.register", string="Wizard")
    amount = fields.Float(required=True)
    check_amount_in_words = fields.Char(string="Amount in Words")
    payment_difference = fields.Float(
        compute="_compute_payment_difference", string="Difference Amount"
    )
    payment_difference_handling = fields.Selection(
        [("open", "Keep open"), ("reconcile", "Mark invoice as fully paid")],
        default="open",
        string="Action",
        copy=False,
    )
    writeoff_account_id = fields.Many2one(
        "account.account",
        string="Account",
        domain=[("deprecated", "!=", True)],
        copy=False,
        check_company=True,
    )
    reason_code = fields.Many2one("payment.adjustment.reason")
    note = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company", default=lambda self: self.env.company
    )

    @api.onchange("amount")
    def _onchange_amount(self):
        check_amount_in_words = num2words(math.floor(self.amount), lang="en").title()
        decimals = self.amount % 1
        if decimals >= 10**-2:
            check_amount = str(
                int(round(float_round(decimals * 100, precision_rounding=1)))
            )
            check_amount_in_words += self.env._(f" and {check_amount}/100")
        self.check_amount_in_words = check_amount_in_words
        self.payment_difference = self.balance - self.amount

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        """
        Raise warning while the invoice is changed.
        """
        raise ValidationError(self.env._("Invoice is unchangeable!"))

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """
        Raise warning while the Customer is changed.
        """
        raise ValidationError(self.env._("Partner is unchangeable!"))

    @api.onchange("balance")
    def _onchange_balance(self):
        """
        Raise warning while the Balance Amount is changed.
        """
        raise ValidationError(self.env._("Balance is unchangeable!"))
