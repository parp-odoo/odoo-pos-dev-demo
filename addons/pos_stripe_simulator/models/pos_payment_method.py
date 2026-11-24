from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_stripe_simulator_url(self):
        return self.env['ir.config_parameter'].sudo().get_str('pos_stripe_simulator.url')

    def _get_stripe_payment_provider(self):
        # Only POS Stripe traffic is redirected; eCommerce Stripe payments are left untouched.
        provider = super()._get_stripe_payment_provider()
        return provider.with_context(pos_stripe_simulator_url=self._get_stripe_simulator_url())
