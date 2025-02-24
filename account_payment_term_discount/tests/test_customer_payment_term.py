# Copyright 2018 Open Source Integrators (http://www.opensourceintegrators.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import Form, common


class TestPaymentTermDiscount(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Refs
        cls.main_company = cls.env.ref("base.main_company")
        cls.partner_id = cls.env.ref("base.res_partner_4")

        Journal = cls.env["account.journal"]
        journal_sale = Journal.search([("type", "=", "sale")], limit=1)
        journal_purchase = Journal.search([("type", "=", "purchase")], limit=1)
        res_users_account_manager = cls.env.ref("account.group_account_manager")
        partner_manager = cls.env.ref("base.group_partner_manager")
        cls.payment_method = cls.env.ref("account.account_payment_method_manual_in")

        # Get required Model
        cls.account_invoice_model = cls.env["account.move"]
        cls.account_model = cls.env["account.account"]
        cls.payment_term_model = cls.env["account.payment.term"]
        cls.user_model = cls.env["res.users"]
        cls.payment_model = cls.env["account.payment"]

        # Create users
        cls.account_manager = cls.user_model.with_context(
            **{"no_reset_password": True}
        ).create(
            dict(
                name="Adviser",
                company_id=cls.main_company.id,
                login="fm_adviser",
                email="accountmanager@yourcompany.com",
                groups_id=[(6, 0, [res_users_account_manager.id, partner_manager.id])],
            )
        )

        # Create account for invoice discount
        cls.account_discount = cls.account_model.with_user(
            cls.account_manager.id
        ).create(
            dict(
                code="custaccdiscount",
                name="Discount Expenses",
                account_type="expense",
                reconcile=True,
            )
        )

        # Create account for bill discount
        cls.account_discount_bill = cls.account_model.with_user(
            cls.account_manager.id
        ).create(
            dict(
                code="billaccdiscount",
                name="Discount Income",
                account_type="income_other",
                reconcile=True,
            )
        )
        # Income account
        cls.income_account = cls.account_model.with_user(cls.account_manager.id).search(
            [
                (
                    "account_type",
                    "=",
                    "income_other",
                )
            ],
            limit=1,
        )

        # Create receivable account
        cls.account_rec1_id = cls.account_model.with_user(
            cls.account_manager.id
        ).create(
            dict(
                code="custaccrec",
                name="Customer invoice receivable",
                account_type="asset_receivable",
                reconcile=True,
            )
        )

        # Create Payment term
        cls.payment_term = cls.payment_term_model.with_user(
            cls.account_manager.id
        ).create(
            dict(
                name="5%10 NET30",
                early_discount=True,
                note="5% discount if payment done within 10 days, otherwise net",
                discount_percentage=5.0,
                discount_days=10,
                discount_expense_account_id=cls.account_discount.id,
                discount_income_account_id=cls.account_discount_bill.id,
                line_ids=[
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 100.0,
                            "nb_days": 30,
                        },
                    )
                ],
            )
        )

        # Create customer invoice
        cls.customer_invoice = cls.account_invoice_model.with_user(
            cls.account_manager.id
        ).create(
            dict(
                name="Test Customer Invoice",
                move_type="out_invoice",
                invoice_date=fields.Date.today(),
                invoice_payment_term_id=cls.payment_term.id,
                journal_id=journal_sale.id,
                partner_id=cls.partner_id.id,
                invoice_line_ids=[
                    (
                        0,
                        0,
                        {
                            "product_id": cls.env.ref("product.product_product_5").id,
                            "quantity": 10.0,
                            "account_id": cls.income_account.id,
                            "name": "product test 5",
                            "price_unit": 100.00,
                            "tax_ids": [],
                        },
                    )
                ],
            )
        )
        # Validate customer invoice
        cls.customer_invoice.action_post()

        # Create vendor bill
        cls.bill = cls.account_invoice_model.with_user(cls.account_manager.id).create(
            dict(
                name="Vendor Bill",
                move_type="in_invoice",
                invoice_date=fields.Date.today(),
                invoice_payment_term_id=cls.payment_term.id,
                journal_id=journal_purchase.id,
                partner_id=cls.partner_id.id,
                invoice_line_ids=[
                    (
                        0,
                        0,
                        {
                            "product_id": cls.env.ref("product.product_product_5").id,
                            "quantity": 10.0,
                            "account_id": cls.income_account.id,
                            "name": "Bill Line",
                            "price_unit": 100.00,
                            "tax_ids": [],
                        },
                    )
                ],
            )
        )
        # Validate customer invoice
        cls.bill.action_post()

    @classmethod
    def _do_payment(cls, invoice, amount, date):
        """
        Create Payment wizard helper function.
        Returns the transient record used.
        """
        ctx = {
            "active_ids": [invoice.id],
            "active_id": invoice.id,
            "active_model": "account.move",
        }
        PaymentWizard = cls.env["account.payment.register"]
        view = "account.view_account_payment_register_form"
        with Form(PaymentWizard.with_context(**ctx), view=view) as f:
            f.amount = amount
            f.payment_date = date
        payment = f.save()
        payment.action_create_payments()
        return payment

    def test_customer_invoice_payment_term_discount(self):
        """Test customer invoice and payment term discount"""
        # Update payment date that's match with condition within 10 days
        payment_date = self.customer_invoice.invoice_date + relativedelta(days=9)
        self._do_payment(self.customer_invoice, 950.0, payment_date)
        # Verify that invoice is now in Paid state
        self.assertIn(self.customer_invoice.payment_state, ["in_payment", "paid"])

    def test_customer_invoice_payment_term_no_discount(self):
        """Create customer invoice and verify workflow without discount"""
        # Update payment date that does not match with condition within 10 days
        payment_date = self.customer_invoice.invoice_date + relativedelta(days=15)
        self._do_payment(self.customer_invoice, 950.0, payment_date)
        # Verify that invoice is now in Partial state
        self.assertIn(
            self.customer_invoice.payment_state, ["partial", "in_payment", "paid"]
        )

    def test_bill_payment_term_discount(self):
        """Vendor Bill applies discount on Expense account"""
        # Update payment date that's match with condition within 10 days
        payment_date = self.bill.invoice_date + relativedelta(days=9)
        payment = self._do_payment(self.bill, 950.0, payment_date)
        # Verify that bill discount account was proposed
        self.assertEqual(
            payment.writeoff_account_id.code, self.account_discount_bill.code
        )
        # Verify that invoice is now in Paid state
        self.assertIn(self.bill.payment_state, ["in_payment", "paid"])
