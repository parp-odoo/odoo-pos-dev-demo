import os
from odoo import models, Command

ngrok_url = os.getenv("NGROK_URL")
uk_us_up_username = os.getenv("IN_UP_USERNAME")
uk_us_up_api_key = os.getenv("IN_UP_API_KEY")

in_up_store_prim_id = os.getenv("IN_UP_STORE_PRIM_ID")


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def load_pos_ub_extra_demo_data(self):
        in_company = self.env.ref('base.demo_company_in')
        config = self.env["pos.config"].with_company(in_company).search([('name', '=', 'IN Restaurant')])
        provider_ids = self.get_record_by_ref([
            'pos_urban_piper.pos_delivery_provider_zomato',
            'pos_urban_piper.pos_delivery_provider_swiggy',
        ])
        self._set_base_url(ngrok_url)
        if 'pos.urbanpiper.store' in self.env:
            store = self.env['pos.urbanpiper.store'].with_company(in_company).create({
                'config_id': config.id,
                'name': 'Test-P Ahmedabad',
                'city': 'Ahmedabad',
                'store_identifier': in_up_store_prim_id,
                'urbanpiper_username': uk_us_up_username,
                'urbanpiper_apikey': uk_us_up_api_key,
                'urbanpiper_aggregator_ids': [
                    Command.create({'delivery_provider_id': provider}) for provider in provider_ids
                ],
            })
            config.write({
                "module_pos_urban_piper": True,
                "urbanpiper_store_id": store.id,
            })
        else:
            config.write({
                "module_pos_urban_piper": True,
                "urbanpiper_store_identifier": in_up_store_prim_id,
                'urbanpiper_delivery_provider_ids': [Command.set(provider_ids)],
                'is_urbanpiper_webhook_register': True,
            })
            in_company.write({
                "pos_urbanpiper_username": uk_us_up_username,
                "pos_urbanpiper_apikey": uk_us_up_api_key,
            })
