# Copyright 2025 Kencove (https://www.kencove.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import werkzeug

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):
    @http.route()
    def payment_pay(
        self,
        reference=None,
        amount=None,
        invoice_id=None,
        currency_id=None,
        company_id=None,
        partner_id=None,
        provider_id=None,
        access_token=None,
        sale_order_id=None,
        force_override_partner=False,
        **kwargs,
    ):
        # Cast numeric parameters as int or float and void them if their str value is malformed
        amount = self._cast_as_float(amount)
        (
            invoice_id,
            currency_id,
            provider_id,
            partner_id,
            sale_order_id,
            company_id,
        ) = tuple(
            map(
                self._cast_as_int,
                (
                    invoice_id,
                    currency_id,
                    provider_id,
                    partner_id,
                    sale_order_id,
                    company_id,
                ),
            )
        )

        order_sudo = request.env["sale.order"].sudo()
        if sale_order_id:
            order_sudo = order_sudo.browse(sale_order_id).exists()
            if not order_sudo:
                raise ValidationError(_("The provided parameters are invalid."))

        invoice_sudo = request.env["account.move"].sudo()
        if invoice_id:
            invoice_sudo = invoice_sudo.browse(invoice_id).exists()
            if not invoice_sudo:
                raise ValidationError(_("The provided parameters are invalid."))

        response = super().payment_pay(
            reference=reference,
            amount=amount,
            invoice_id=invoice_id,
            currency_id=currency_id,
            company_id=company_id,
            partner_id=partner_id,
            provider_id=provider_id,
            access_token=access_token,
            sale_order_id=sale_order_id,
            **kwargs,
        )
        if not partner_id or not force_override_partner:
            return response

        amount = amount or 0.0
        force_partner = request.env["res.partner"].sudo().browse(partner_id)
        company_id = (
            company_id or force_partner.company_id.id or request.env.user.company_id.id
        )
        company = request.env["res.company"].sudo().browse(company_id)
        currency_id = currency_id or company.currency_id.id

        # Make sure that the currency exists and is active
        currency = request.env["res.currency"].browse(currency_id).exists()
        if not currency or not currency.active:
            raise werkzeug.exceptions.NotFound()

        # Select all providers and tokens that match the constraints
        providers_sudo = (
            request.env["payment.provider"]
            .sudo()
            ._get_compatible_providers(
                company_id, partner_id, amount, currency_id=currency.id, **kwargs
            )
        )  # In sudo mode to read the fields of providers and partner (if not logged in)
        if (
            provider_id in providers_sudo.ids
        ):  # Only keep the desired provider if it's suitable
            providers_sudo = providers_sudo.browse(provider_id)
        payment_tokens = (
            request.env["payment.token"]
            .sudo()
            .search(
                [
                    ("provider_id", "in", providers_sudo.ids),
                    ("partner_id", "=", partner_id),
                ]
            )
        )
        # Make sure that the partner's company matches the company passed as parameter.
        if not PaymentPortal._can_partner_pay_in_company(force_partner, company):
            providers_sudo = request.env["payment.provider"].sudo()
            payment_tokens = request.env["payment.token"]

        # Compute the fees taken by providers supporting the feature
        fees_by_provider = {
            provider_sudo: provider_sudo._compute_fees(
                amount, currency, force_partner.country_id
            )
            for provider_sudo in providers_sudo.filtered("fees_active")
        }

        # Generate a new access token in case the partner id or the currency id was updated
        access_token = payment_utils.generate_access_token(
            partner_id, amount, currency.id
        )
        rendering_context = {
            **response.qcontext,
            "providers": providers_sudo,
            "tokens": payment_tokens,
            "fees_by_provider": fees_by_provider,
            "show_tokenize_input": self._compute_show_tokenize_input_mapping(
                providers_sudo, logged_in=True, **kwargs
            ),
            "partner_id": partner_id,
            "access_token": access_token,
            "partner_is_different": False,
        }
        if order_sudo:
            backend_link = self._get_backend_link(order_sudo)
            rendering_context.update(
                {
                    "backend_link": backend_link,
                    "landing_route": rendering_context["landing_route"]
                    + f"?force_backend=1&sale_order_id={order_sudo.id}",
                }
            )
        if invoice_sudo:
            backend_link = self._get_backend_link(invoice_sudo)
            rendering_context.update(
                {
                    "backend_link": backend_link,
                    "landing_route": rendering_context["landing_route"]
                    + f"?force_backend=1&invoice_id={invoice_sudo.id}",
                }
            )
        return request.render(
            self._get_payment_page_template_xmlid(**kwargs), rendering_context
        )

    @http.route()
    def payment_confirm(self, tx_id, access_token, **kwargs):
        response = super().payment_confirm(
            tx_id=tx_id, access_token=access_token, **kwargs
        )
        if not kwargs.get("force_backend"):
            return response
        model_backend = False
        if kwargs.get("sale_order_id"):
            sale_order_id = self._cast_as_int(kwargs.get("sale_order_id"))
            model_backend = (
                request.env["sale.order"].sudo().browse(sale_order_id).exists()
            )
        elif kwargs.get("invoice_id"):
            invoice_id = self._cast_as_int(kwargs.get("invoice_id"))
            model_backend = (
                request.env["account.move"].sudo().browse(invoice_id).exists()
            )
        if not model_backend:
            return response
        backend_link = self._get_backend_link(model_backend)
        response.qcontext.update(
            {
                "backend_link": backend_link,
                "reference": model_backend.name,
            }
        )
        return response

    def _get_backend_link(self, model_backend):
        return (
            f"/web#model={model_backend._name}"
            f"&id={model_backend.id}"
            f"&action={model_backend._get_portal_return_action().id}"
            f"&view_type=form"
        )

    @staticmethod
    def _update_landing_route(tx_sudo, access_token):
        if tx_sudo.operation == "validation":
            access_token = payment_utils.generate_access_token(
                tx_sudo.partner_id.id, tx_sudo.amount, tx_sudo.currency_id.id
            )
        if "?force_backend" in tx_sudo.landing_route:
            tx_sudo.landing_route = (
                f"{tx_sudo.landing_route}"
                f"&tx_id={tx_sudo.id}&access_token={access_token}"
            )
        else:
            tx_sudo.landing_route = (
                f"{tx_sudo.landing_route}"
                f"?tx_id={tx_sudo.id}&access_token={access_token}"
            )
