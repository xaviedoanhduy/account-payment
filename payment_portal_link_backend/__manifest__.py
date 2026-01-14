# Copyright 2025 Kencove (https://www.kencove.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Payment Portal Link Backend",
    "summary": "Register payment for order from backend to portal.",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "category": "Hidden",
    "website": "https://github.com/OCA/account-payment",
    "author": "Kencove, Trobz, Odoo Community Association (OCA)",
    "maintainers": ["xaviedoanhduy"],
    "application": False,
    "installable": True,
    "depends": [
        "account_payment",
        "sale",
    ],
    "data": [
        "templates/payment_templates.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],
}
