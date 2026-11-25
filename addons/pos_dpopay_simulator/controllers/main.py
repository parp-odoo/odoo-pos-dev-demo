import requests

from odoo import http
from odoo.http import request


class DpoPaySimulatorProxy(http.Controller):
    """Same-origin proxy to the simulator dashboard, so it also works when only Odoo is reachable."""

    @http.route(
        ['/pos_dpopay_simulator', '/pos_dpopay_simulator/<path:subpath>'],
        type='http', auth='user', methods=['GET', 'POST'], csrf=False, save_session=False,
    )
    def proxy(self, subpath='', **kwargs):
        if not request.httprequest.path.startswith('/pos_dpopay_simulator/'):
            # Relative URLs in the dashboard need the trailing slash.
            return request.redirect('/pos_dpopay_simulator/', local=True)
        if not request.env.user._is_internal():
            return request.make_json_response({'errorMessage': 'Forbidden'}, status=403)
        # Only the dashboard and its API; the DPO API is called by the server, never by the browser.
        if subpath and subpath != 'index.html' and not subpath.startswith(('sim/', 'static/')):
            return request.make_json_response({'errorMessage': 'Not found'}, status=404)

        base_url = request.env['pos.payment.method'].sudo()._get_dpopay_simulator_url()
        if not base_url:
            return request.make_json_response({'errorMessage': 'pos_dpopay_simulator.url is not set'}, status=503)
        try:
            response = requests.request(
                request.httprequest.method,
                f'{base_url}/{subpath}',
                data=request.httprequest.get_data(),
                headers={'Content-Type': request.httprequest.headers.get('Content-Type', 'application/json')},
                timeout=10,
            )
        except requests.exceptions.RequestException as error:
            return request.make_json_response(
                {'errorMessage': f'DPO Pay simulator unreachable at {base_url}: {error}'}, status=502)
        return request.make_response(
            response.content,
            headers=[('Content-Type', response.headers.get('Content-Type', 'application/json')), ('Cache-Control', 'no-store')],
            status=response.status_code,
        )
