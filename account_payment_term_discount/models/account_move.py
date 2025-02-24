# Copyright 2018 Open Source Integrators (http://www.opensourceintegrators.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    discount_amt = fields.Monetary(
        "Discount Possible",
        help="Discount amount possible with the given payment term",
        compute="_compute_discount_amt",
        store=True,
    )
    discount_date = fields.Date(
        compute="_compute_discount_date",
        help="Compute discount on the invoice based on the payment term discount "
        "percentage."
        "and the current date",
        store=True,
    )
    discount_taken = fields.Monetary("Discount taken", copy=False)
    check_payment_discount = fields.Boolean(compute="_compute_payment_disc")
    shipping_lines_total = fields.Monetary(
        help="Exclude shipping lines total from discount if applicable " "in terms",
        compute="_compute_shipping_lines_total",
    )

    @api.depends("state", "amount_residual", "invoice_payment_term_id", "invoice_date")
    def _compute_discount_amt(self):
        for invoice in self.filtered("invoice_payment_term_id"):
            discount_information = (
                invoice.invoice_payment_term_id._check_payment_term_discount(invoice)
            )
            if discount_information[0] > 0.0:
                invoice.discount_amt = abs(round(discount_information[0], 2))
                # If discount taken make disc amt to 0 as disc is no more valid
                if invoice.discount_taken != 0:
                    invoice.discount_amt = 0
            else:
                invoice.discount_amt = 0.0

    @api.depends("invoice_date", "invoice_payment_term_id")
    def _compute_discount_date(self):
        "This will retain a value based on invoice date and discount term"
        for invoice in self:
            disc_date = False
            payment_term = invoice.invoice_payment_term_id
            if payment_term.early_discount:
                invoice_date = invoice.invoice_date or fields.Date.today()
                disc_date = invoice_date + relativedelta(
                    days=payment_term.discount_days
                )
            # Empty disc date if pass today's date or discount already used
            if disc_date and (
                disc_date <= fields.Date.today() or invoice.discount_taken != 0
            ):
                disc_date = False
            invoice.discount_date = disc_date

    @api.depends("amount_residual", "invoice_payment_term_id", "invoice_date")
    def _compute_payment_disc(self):
        for invoice in self:
            if invoice.invoice_payment_term_id:
                discount_information = (
                    invoice.invoice_payment_term_id._check_payment_term_discount(
                        invoice
                    )
                )
                if discount_information[0] > 0.0:
                    invoice.check_payment_discount = True
                    continue
            invoice.check_payment_discount = False

    @api.depends("invoice_line_ids")
    def _compute_shipping_lines_total(self):
        for invoice in self:
            shipping_lines_total = 0.0
            for line in invoice.invoice_line_ids.filtered(
                lambda x: x.product_id.is_exclude_shipping_amount
            ):
                shipping_lines_total += line.price_subtotal
            invoice.shipping_lines_total = shipping_lines_total
