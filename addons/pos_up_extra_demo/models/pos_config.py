import os
import uuid
import random

from odoo import api, models, Command

ngrok_url = os.getenv("NGROK_URL")
uk_us_up_username = os.getenv("UK_US_UP_USERNAME")
uk_us_up_api_key = os.getenv("UK_US_UP_API_KEY")

uk_us_up_store_prim_id = os.getenv("UK_US_UP_STORE_PRIM_ID")
uk_us_up_store_sec_id = os.getenv("UK_US_UP_STORE_SEC_ID")

QUICK_ORDER_NOTES = [
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


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _set_base_url(self, url):
        self.env['ir.config_parameter'].sudo().set_str('web.base.url', url)
        pass

    def load_pos_ub_extra_demo_data_sf(self):
        provider_ids = self.get_record_by_ref([
            'pos_urban_piper.pos_delivery_provider_ubereats',
            'pos_urban_piper.pos_delivery_provider_doordash',
            'pos_urban_piper.pos_delivery_provider_justeat',
        ])

        self._set_base_url(ngrok_url)
        self.load_pos_ub_extra_demo_data_sf_resto(provider_ids)
        self.load_pos_ub_extra_demo_data_sf_furn_shop(provider_ids[:-1])

    def load_pos_ub_extra_demo_data_sf_furn_shop(self, provider_ids):
        furn_shop = self.env.ref('point_of_sale.pos_config_main')
        sf_compnay = furn_shop.company_id

        self.env['pos.urbanpiper.store'].with_company(sf_compnay).create({
            'config_id': furn_shop.id,
            'name': 'Test-P Store',
            'city': 'San francisco',
            'store_identifier': uk_us_up_store_sec_id,
            'urbanpiper_username': uk_us_up_username,
            'urbanpiper_apikey': uk_us_up_api_key,
            'is_webhook_register': True,
            'use_test_mode': True,
            'aggregator_lines': [
                Command.create({'delivery_provider_id': provider}) for provider in provider_ids
            ],
        })

    def load_pos_ub_extra_demo_data_sf_resto(self, provider_ids):
        if demo_store := self.env.ref('pos_urban_piper.pos_urbanpiper_demo_store'):
            demo_store.write({
                'store_identifier': uk_us_up_store_prim_id,
                'urbanpiper_username': uk_us_up_username,
                'urbanpiper_apikey': uk_us_up_api_key,
                'is_webhook_register': True,
            })

    @api.model
    def action_quick_urbanpiper_test_order(self, store_id, product_id, provider_id):
        self.env['pos.urbanpiper.test.order.wizard'].with_context(store_id=store_id)\
            .create({
                'product_id': product_id,
                'quantity': 7,
                'delivery_provider_id': provider_id,
                'delivery_instruction': random.choice(QUICK_ORDER_NOTES),
            }).make_test_order()
