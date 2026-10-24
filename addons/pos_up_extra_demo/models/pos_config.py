import json
import logging
import os
import random

from odoo import Command, _, api, models
from odoo.exceptions import AccessError, UserError
from odoo.addons.pos_urban_piper import const
from odoo.addons.pos_urban_piper.models.pos_urban_piper_request import UrbanPiperClient

_logger = logging.getLogger(__name__)

QUICK_ORDER_NOTES = (
    'Please deliver with the confidence of a developer in production mode.',
    'If food is late, we blame the staging server.',
    'Handle with care; my testing team is watching.',
    'If this order crashes, clear cache and try again.',
    'Include napkins; my commit history is already messy.',
)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _set_base_url(self, url):
        # Demo loading runs as the installer; parameter writes stay private.
        parameters = self.env['ir.config_parameter']
        if url:
            parameters.set_param('web.base.url', url)
        parameters.set_param('pos_urban_piper.is_production_mode', 'False')

    def _configure_demo_urbanpiper(self, config, store_identifier, username, api_key,
                                  provider_ids, name, city):
        if not config or not all((store_identifier, username, api_key)):
            _logger.info('Skipping optional UrbanPiper setup: missing configuration or credentials')
            return
        config.ensure_one()
        config = config.with_company(config.company_id)
        config.write({
            'module_pos_urban_piper': True,
            'urbanpiper_store_identifier': store_identifier,
            'urbanpiper_delivery_provider_ids': [Command.set(provider_ids)],
            'urbanpiper_webhook_url': config.get_base_url(),
        })
        parameters = self.env['ir.config_parameter']
        parameters.set_param('pos_urban_piper.urbanpiper_username', username)
        parameters.set_param('pos_urban_piper.urbanpiper_apikey', api_key)

    @api.private
    def load_pos_ub_extra_demo_data_sf(self):
        provider_ids = self.get_record_by_ref([
            'pos_urban_piper_ubereats.pos_delivery_provider_ubereats',
            'pos_urban_piper.pos_delivery_provider_doordash',
            'pos_urban_piper.pos_delivery_provider_justeat',
        ])
        self._set_base_url(os.getenv('NGROK_URL'))
        self.load_pos_ub_extra_demo_data_sf_resto(provider_ids)
        self.load_pos_ub_extra_demo_data_sf_furn_shop(provider_ids[:-1])

    @api.private
    def load_pos_ub_extra_demo_data_sf_furn_shop(self, provider_ids):
        config = self.env.ref('point_of_sale.pos_config_main', raise_if_not_found=False)
        self._configure_demo_urbanpiper(
            config, os.getenv('UK_US_UP_STORE_SEC_ID'),
            os.getenv('UK_US_UP_USERNAME'), os.getenv('UK_US_UP_API_KEY'),
            provider_ids, 'Test-P Store', 'San Francisco',
        )

    @api.private
    def load_pos_ub_extra_demo_data_sf_resto(self, provider_ids):
        config = self.env.ref('pos_restaurant.pos_config_main_restaurant', raise_if_not_found=False)
        self._configure_demo_urbanpiper(
            config, os.getenv('UK_US_UP_STORE_PRIM_ID'),
            os.getenv('UK_US_UP_USERNAME'), os.getenv('UK_US_UP_API_KEY'),
            provider_ids, 'Test-P Restaurant', 'San Francisco',
        )

    @api.model
    def action_quick_urbanpiper_test_order(self, store_id, product_id, provider_id):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_('Only Point of Sale users can place demo orders.'))
        config = self.browse(store_id).exists()
        if not config:
            raise UserError(_('Select a Point of Sale for the demo order.'))
        config.check_access('read')
        if config.company_id not in self.env.companies:
            raise AccessError(_('The Point of Sale belongs to another company.'))
        if not config.current_session_id or config.current_session_id.state != 'opened':
            raise UserError(_('Open a Point of Sale session before placing a demo order.'))
        product = self.env['product.template'].browse(product_id).exists()
        if not product:
            raise UserError(_('Select a product for the demo order.'))
        product.check_access('read')
        if not product.available_in_pos or (product.company_id and product.company_id != config.company_id):
            raise UserError(_('Select a Point of Sale product from the same company.'))
        if provider_id not in config.urbanpiper_delivery_provider_ids.ids:
            raise UserError(_('Select a delivery provider configured for this Point of Sale.'))
        wizard = self.env['pos.urbanpiper.test.order.wizard'].with_company(config.company_id).with_context(
            config_id=store_id,
        ).create({
            'product_id': product.id,
            'quantity': 7,
            'delivery_provider_id': provider_id,
            'delivery_instruction': random.choice(QUICK_ORDER_NOTES),
        })
        wizard.make_test_order()
        return True

    @api.private
    def is_urbanpiper_test_order(self, order):
            """Return True if the order is marked as an UrbanPiper test order."""
            if not order.delivery_json:
                return False
            try:
                delivery_data = json.loads(order.delivery_json)
            except (TypeError, ValueError):
                return False
            return bool(delivery_data.get('order', {}).get('urban_piper_test'))

    def order_status_update(self, order_id, new_status, code=None):
            """
            Update order status from urban piper webhook
            """
            self.ensure_one()
            order = self.env['pos.order'].browse(order_id).exists()
            order.ensure_one()
            order.check_access('write')
            if order.config_id != self:
                raise AccessError(_('The order belongs to another Point of Sale.'))
            if new_status == 'Food Ready' and order.state != 'paid':
                self._make_order_payment(order)
            up = UrbanPiperClient(self)
            is_success, message = False, ''
            urban_piper_test = self.is_urbanpiper_test_order(order)
            if urban_piper_test or (order.delivery_provider_id.technical_name == 'careem' and new_status == 'Food Ready'):
                is_success = True
            else:
                is_success, message = up.request_status_update(order.delivery_identifier, new_status, code)
            if is_success:
                order.write({
                    'delivery_status': const.ORDER_STATUS_MAPPING[new_status][1],
                })
            if not urban_piper_test and new_status == 'Acknowledged':
                up.urbanpiper_order_reference_update(order)
            if new_status == 'Cancelled':
                # Prevent loading cancelled orders in `getServerOrders` triggered by `_send_delivery_order_count`
                order.state = 'cancel'
            self._send_delivery_order_count(order_id)
            return {'is_success': is_success, 'message': message}
