import re

import requests

from odoo import http
from odoo.http import request

# What the simulated JS SDK needs; available to anyone who can open a POS or a self-order kiosk.
SDK_ROUTES = [
    ('GET', r'terminal/v1/?'),
    ('GET', r'sim/state'),
    ('POST', r'sim/discover'),
    ('POST', r'sim/readers/[\w-]+/(connect|disconnect|heartbeat)'),
    ('GET', r'v1/payment_intents/[\w-]+'),
    ('POST', r'sim/payment_intents/[\w-]+/(collect|confirm)'),
    ('POST', r'sim/charges/[\w-]+/refund'),
]


class StripeSimulatorProxy(http.Controller):
    """Same-origin proxy to the simulator, so the browser never needs to reach it directly."""

    @http.route(
        ['/pos_stripe_simulator', '/pos_stripe_simulator/<path:subpath>'],
        type='http', auth='public', methods=['GET', 'POST', 'DELETE'], csrf=False, save_session=False,
    )
    def proxy(self, subpath='', **kwargs):
        method = request.httprequest.method
        allowed = request.env.user._is_internal() or any(
            method == route_method and re.fullmatch(pattern, subpath) for route_method, pattern in SDK_ROUTES
        )
        if not allowed:
            return request.make_json_response({'error': {'message': 'Forbidden'}}, status=403)

        base_url = request.env['pos.payment.method'].sudo()._get_stripe_simulator_url()
        if not base_url:
            return request.make_json_response({'error': {'message': 'pos_stripe_simulator.url is not set'}}, status=503)
        try:
            response = requests.request(
                method,
                f"{base_url.rstrip('/')}/{subpath}",
                params=request.httprequest.args,
                data=request.httprequest.get_data(),
                headers={'Content-Type': request.httprequest.headers.get('Content-Type', 'application/json')},
                timeout=10,
            )
        except requests.exceptions.RequestException as error:
            return request.make_json_response(
                {'error': {'code': 'network_error', 'message': f'Stripe simulator unreachable at {base_url}: {error}'}},
                status=502,
            )
        return request.make_response(
            response.content,
            headers=[('Content-Type', response.headers.get('Content-Type', 'application/json')), ('Cache-Control', 'no-store')],
            status=response.status_code,
        )
