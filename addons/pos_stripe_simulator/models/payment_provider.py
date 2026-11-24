from odoo import models
from odoo.tools.urls import urljoin as url_join


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _build_request_url(self, endpoint, *, is_proxy_request=False, **kwargs):
        simulator_url = self.env.context.get('pos_stripe_simulator_url')
        if self.code == 'stripe' and simulator_url and not is_proxy_request:
            return url_join(simulator_url.rstrip('/') + '/v1/', endpoint)
        return super()._build_request_url(endpoint, is_proxy_request=is_proxy_request, **kwargs)
