import os
from odoo import models, Command

ngrok_url = os.getenv("NGROK_URL")
uk_us_up_username = os.getenv("UK_US_UP_USERNAME")
uk_us_up_api_key = os.getenv("UK_US_UP_API_KEY")

uk_us_up_store_prim_id = os.getenv("UK_US_UP_STORE_PRIM_ID")
uk_us_up_store_sec_id = os.getenv("UK_US_UP_STORE_SEC_ID")


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _set_base_url(self, url):
        try:
            self.env['ir.config_parameter'].sudo().set_param('web.base.url', ngrok_url)
            self.env['ir.config_parameter'].sudo().set_param('pos_urban_piper.is_production_mode', 'False')
        except Exception:
            self.env['ir.config_parameter'].sudo().set_str('web.base.url', ngrok_url)
            self.env['ir.config_parameter'].sudo().set_str('pos_urban_piper.is_production_mode', 'False')

    def load_pos_ub_extra_demo_data_sf(self):
        provider_ids = self.get_record_by_ref([
            'pos_urban_piper_ubereats.pos_delivery_provider_ubereats',
            'pos_urban_piper.pos_delivery_provider_doordash',
            'pos_urban_piper.pos_delivery_provider_justeat',
        ])

        self._set_base_url(ngrok_url)
        self.load_pos_ub_extra_demo_data_sf_resto(provider_ids[:-1])
        self.load_pos_ub_extra_demo_data_sf_furn_shop(provider_ids)

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
                'urbanpiper_webhook_url': self.env['pos.config'].get_base_url()
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
                'urbanpiper_webhook_url': self.env['pos.config'].get_base_url()
            })
            sf_compnay.write({
                "pos_urbanpiper_username": uk_us_up_username,
                "pos_urbanpiper_apikey": uk_us_up_api_key,
            })

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
                'urbanpiper_webhook_url': self.env['pos.config'].get_base_url()
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
                'urbanpiper_webhook_url': self.env['pos.config'].get_base_url()
            })
