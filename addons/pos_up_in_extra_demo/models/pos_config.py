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
        config = self.env["pos.config"].with_company(in_company).search([('name', '=', 'IN Furniture Shop')])
        provider_ids = self.get_record_by_ref([
            'l10n_in_pos_urban_piper.pos_delivery_provider_zomato',
            'l10n_in_pos_urban_piper.pos_delivery_provider_swiggy',
        ])

        self.env['ir.config_parameter'].sudo().set_param('web.base.url', ngrok_url)
        self.env['ir.config_parameter'].sudo().set_param('pos_urban_piper.is_production_mode', 'False')

        in_company.write({
            "pos_urbanpiper_username": uk_us_up_username,
            "pos_urbanpiper_apikey": uk_us_up_api_key,
        })

        if 'pos.urban.piper.store' in self.env:
            store = self.env['pos.urban.piper.store'].with_company(in_company).create({
                'config_id': config.id,
                'name': 'Test-P Ahmedabad',
                'store_city': 'Ahmedabad',
                'store_identifier': in_up_store_prim_id,
                'delivery_provider_ids': [Command.set(provider_ids)],
                'urbanpiper_webhook_url': self.env['pos.config'].get_base_url()
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
                'urbanpiper_webhook_url': self.env['pos.config'].get_base_url()
            })
