# Copyright (C) Camptocamp Austria (<http://www.camptocamp.at>)
# Copyright 2018 Open Source Integrators (http://www.opensourceintegrators.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    is_exclude_shipping_lines = fields.Boolean(
        string="Exclude Shipping from Discount",
        help="Check this box if you want to exclude shipping charges from discount",
    )
    discount_income_account_id = fields.Many2one(
        "account.account",
        string="Discount on Purchases Account",
        help="This account will be used to post the discount on purchases.",
    )
    discount_expense_account_id = fields.Many2one(
        "account.account",
        string="Discount on Sales Account",
        help="This account will be used to post the discount on sales.",
    )

    def _get_payment_term_discount(self, invoice=None, payment_date=None, amount=0.0):
        payment_discount = 0.0
        discount_account_id = 0.0
        invoice_date = fields.Date.from_string(invoice.invoice_date or payment_date)
        till_discount_date = invoice_date + relativedelta(days=self.discount_days)
        if self.discount_percentage and payment_date <= till_discount_date:
            payment_discount = round((amount * self.discount_percentage) / 100.0, 2)
            if invoice.move_type in ("out_invoice", "in_refund"):
                discount_account_id = self.discount_expense_account_id.id
            else:
                discount_account_id = self.discount_income_account_id.id
        return abs(payment_discount), discount_account_id, abs(amount)

    def _check_payment_term_discount(self, invoice=None, payment_date=None):
        payment_discount = 0.0
        applied_amount_total = 0.0
        discount_account_id = 0.0
        if not invoice:
            return payment_discount, discount_account_id, applied_amount_total
        if not payment_date:
            payment_date = fields.Date.context_today(self)
        else:
            payment_date = fields.Date.from_string(payment_date)

        for payment_term in self.filtered(lambda p: p.early_discount):
            if payment_term.early_pay_discount_computation == "included":
                amount = invoice.amount_total
            else:
                amount = invoice.amount_untaxed_signed
            if payment_term.is_exclude_shipping_lines:
                amount -= invoice.shipping_lines_total
            discount_information = payment_term._get_payment_term_discount(
                invoice, payment_date, amount
            )
            payment_discount = discount_information[0]
            discount_account_id = discount_information[1]
            applied_amount_total = invoice.amount_residual
        return payment_discount, discount_account_id, applied_amount_total
