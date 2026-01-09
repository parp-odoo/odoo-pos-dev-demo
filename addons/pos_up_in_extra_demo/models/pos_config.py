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
            'pos_urban_piper_zomato.pos_delivery_provider_zomato',
            'pos_urban_piper_swiggy.pos_delivery_provider_swiggy',
        ])
        self._set_base_url(ngrok_url)
        config.write({
            "module_pos_urban_piper": True,
            "urbanpiper_store_identifier": in_up_store_prim_id,
            'urbanpiper_delivery_provider_ids': [Command.set(provider_ids)],
        })
        self.env['ir.config_parameter'].sudo().set_param('pos_urban_piper.urbanpiper_username', uk_us_up_username)
        self.env['ir.config_parameter'].sudo().set_param('pos_urban_piper.urbanpiper_apikey', uk_us_up_api_key)
