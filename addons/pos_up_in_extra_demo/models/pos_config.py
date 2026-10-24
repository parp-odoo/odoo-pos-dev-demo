import os

from odoo import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.private
    def load_pos_ub_extra_demo_data(self):
        company = self.env.ref('base.demo_company_in', raise_if_not_found=False)
        if not company:
            return
        Config = self.with_company(company)
        config = Config.search([
            ('name', '=', 'IN Restaurant'), ('company_id', '=', company.id),
        ], limit=1)
        provider_ids = Config.get_record_by_ref([
            'pos_urban_piper.pos_delivery_provider_zomato',
            'pos_urban_piper.pos_delivery_provider_swiggy',
        ])
        Config._set_base_url(os.getenv('NGROK_URL'))
        Config._configure_demo_urbanpiper(
            config, os.getenv('IN_UP_STORE_PRIM_ID'),
            os.getenv('IN_UP_USERNAME'), os.getenv('IN_UP_API_KEY'),
            provider_ids, 'Test-P Ahmedabad', 'Ahmedabad',
        )
