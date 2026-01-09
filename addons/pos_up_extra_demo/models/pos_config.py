import os
import uuid
import random
import json

from odoo import api, models, Command
from odoo.addons.pos_urban_piper import const

from odoo.addons.pos_urban_piper.models.pos_urban_piper_request import UrbanPiperClient

ngrok_url = os.getenv("NGROK_URL")
uk_us_up_username = os.getenv("UK_US_UP_USERNAME")
uk_us_up_api_key = os.getenv("UK_US_UP_API_KEY")

uk_us_up_store_prim_id = os.getenv("UK_US_UP_STORE_PRIM_ID")
uk_us_up_store_sec_id = os.getenv("UK_US_UP_STORE_SEC_ID")


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _set_base_url(self, url):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', url)
        self.env['ir.config_parameter'].sudo().set_param('pos_urban_piper.is_production_mode', 'False')

    def load_pos_ub_extra_demo_data_sf(self):
        provider_ids = self.get_record_by_ref([
            'pos_urban_piper_ubereats.pos_delivery_provider_ubereats',
            'pos_urban_piper.pos_delivery_provider_doordash',
            'pos_urban_piper.pos_delivery_provider_justeat',
        ])

        self._set_base_url(ngrok_url)
        self.load_pos_ub_extra_demo_data_sf_resto(provider_ids)
        self.load_pos_ub_extra_demo_data_sf_furn_shop(provider_ids[:-1])

    def load_pos_ub_extra_demo_data_sf_furn_shop(self, provider_ids):
        furn_shop = self.env.ref('point_of_sale.pos_config_main')
        furn_shop.write({
            "module_pos_urban_piper": True,
            "urbanpiper_store_identifier": uk_us_up_store_sec_id,
            'urbanpiper_delivery_provider_ids': [Command.set(provider_ids)],
        })
        self.env['ir.config_parameter'].sudo().set_param('pos_urban_piper.urbanpiper_username', uk_us_up_username)
        self.env['ir.config_parameter'].sudo().set_param('pos_urban_piper.urbanpiper_apikey', uk_us_up_api_key)

    def load_pos_ub_extra_demo_data_sf_resto(self, provider_ids):
        resto = self.env.ref('pos_restaurant.pos_config_main_restaurant')

        resto.write({
            "module_pos_urban_piper": True,
            "urbanpiper_store_identifier": uk_us_up_store_prim_id,
            'urbanpiper_delivery_provider_ids': [Command.set(provider_ids)],
        })

    @api.model
    def action_quick_urbanpiper_test_order(self, store_id, product_id, provider_id):
        order_notes = [
            "Please deliver with the confidence of a developer in production mode. 🚀",
            "If food is late, we blame the staging server. 🐢",
            "Handle with care; my testing team is watching. 👀",
            "If this order crashes, clear cache and try again. 💥",
            "Please ignore this note. It's just here for testing… or is it? 🤫",
            "Pack it tight; my ORM doesn't like loose relations. 🔗",
            "Include napkins; my commit history is already messy. 🧻",
            "Ring the bell like you found a production bug at 5 PM. 🔔",
            "Leave at the door. I'm in a meeting explaining why tests matter. 📉",
        ]
        UrbanPiperTestOrder = self.env['pos.urbanpiper.test.order.wizard'].sudo()
        if 'pos.urbanpiper.store' in self.env:
            UrbanPiperTestOrder = UrbanPiperTestOrder.with_context(store_id=store_id)
        else:
            UrbanPiperTestOrder = UrbanPiperTestOrder.with_context(config_id=store_id)

        identifier = str(uuid.uuid4())
        UrbanPiperTestOrder.create({
            'product_id': product_id,
            'quantity': 7,
            'delivery_provider_id': provider_id,
            'delivery_instruction': random.choice(order_notes),
        }).make_test_order(identifier)

    def is_urbanpiper_test_order(self, order):
        """Return True if the order is marked as an UrbanPiper test order."""
        if not order.delivery_json:
            return False
        delivery_data = json.loads(order.delivery_json)
        return bool(delivery_data.get('order', {}).get('urban_piper_test'))

    def order_status_update(self, order_id, new_status, code=None):
        """
        Update order status from urban piper webhook
        """
        self.ensure_one()
        order = self.env['pos.order'].browse(order_id)
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
