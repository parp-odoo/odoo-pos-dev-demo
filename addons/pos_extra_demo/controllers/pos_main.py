
from odoo import http
from odoo.http import request
from odoo.addons.point_of_sale.controllers.main import PosController


class PosExtraDemoController(PosController):

    @http.route()
    def pos_receipt_download(self, order_id=None, company_id=None):
        pos_order = request.env['pos.order'].with_company(company_id).browse(int(order_id))
        if not pos_order.exists():
            return request.not_found()
        image = pos_order.order_receipt_generate_html()
        return request.make_response(image, [
            ('Content-Length', len(image)),
            ('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"),
        ])
