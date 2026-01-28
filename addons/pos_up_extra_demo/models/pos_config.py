import os
import uuid
import random

from odoo import api, models, Command

ngrok_url = os.getenv("NGROK_URL")
uk_us_up_username = os.getenv("UK_US_UP_USERNAME")
uk_us_up_api_key = os.getenv("UK_US_UP_API_KEY")

uk_us_up_store_prim_id = os.getenv("UK_US_UP_STORE_PRIM_ID")
uk_us_up_store_sec_id = os.getenv("UK_US_UP_STORE_SEC_ID")


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _set_base_url(self, url):
        # self.env['ir.config_parameter'].sudo().set_str('web.base.url', url)
        self.env['ir.config_parameter'].sudo().set_str('pos_urban_piper.is_production_mode', 'False')

    def _update_urbanpiper_records(self):
        if not hasattr(self, 'is_urbanpiper_webhook_register'):
            return
        self.is_urbanpiper_webhook_register = True

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

        if 'pos.urbanpiper.store' in self.env:
            store = self.env['pos.urbanpiper.store'].with_company(sf_compnay).create({
                'config_id': furn_shop.id,
                'name': 'Mid-Wilshire shop',
                'city': 'San francisco',
                'store_identifier': uk_us_up_store_sec_id,
                'urbanpiper_username': uk_us_up_username,
                'urbanpiper_apikey': uk_us_up_api_key,
                'urbanpiper_aggregator_ids': [
                    Command.create({'delivery_provider_id': provider}) for provider in provider_ids
                ],
            })
            furn_shop.write({
                "module_pos_urban_piper": True,
                "urbanpiper_store_id": store.id,
            })
        else:
            furn_shop.write({
                "module_pos_urban_piper": True,
                "urbanpiper_store_identifier": uk_us_up_store_sec_id,
                'urbanpiper_delivery_provider_ids': [Command.set(provider_ids)],
                'is_urbanpiper_webhook_register': True,
            })
            sf_compnay.write({
                "pos_urbanpiper_username": uk_us_up_username,
                "pos_urbanpiper_apikey": uk_us_up_api_key,
            })
        furn_shop._update_urbanpiper_records()

    def load_pos_ub_extra_demo_data_sf_resto(self, provider_ids):
        resto = self.env.ref('pos_restaurant.pos_config_main_restaurant')
        sf_compnay = resto.company_id

        if 'pos.urbanpiper.store' in self.env:
            store = self.env['pos.urbanpiper.store'].with_company(sf_compnay).create({
                'config_id': resto.id,
                'name': 'be resto',
                'city': 'San francisco',
                'store_identifier': uk_us_up_store_prim_id,
                'urbanpiper_username': uk_us_up_username,
                'urbanpiper_apikey': uk_us_up_api_key,
                'urbanpiper_aggregator_ids': [
                    Command.create({'delivery_provider_id': provider}) for provider in provider_ids
                ],
            })
            resto.write({
                "module_pos_urban_piper": True,
                "urbanpiper_store_id": store.id,
            })
        else:
            resto.write({
                "module_pos_urban_piper": True,
                "urbanpiper_store_identifier": uk_us_up_store_prim_id,
                'urbanpiper_delivery_provider_ids': [Command.set(provider_ids)],
                'is_urbanpiper_webhook_register': True,
            })
        resto._update_urbanpiper_records()

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
        UrbanPiperTestOrder = self.env['pos.urbanpiper.test.order.wizard']
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
