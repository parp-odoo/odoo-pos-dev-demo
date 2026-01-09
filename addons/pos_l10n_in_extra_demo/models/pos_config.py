import os
from odoo import models, Command

razorpay_username = os.getenv("RAZORPAY_USERNAME")
razorpay_tid = os.getenv("RAZORPAY_TID")
razorpay_api_key = os.getenv("RAZORPAY_API_KEY")

pine_labs_merchant = os.getenv("PINE_LABS_MERCHANT")
pine_labs_store = os.getenv("PINE_LABS_STORE")
pine_labs_client = os.getenv("PINE_LABS_CLIENT")
pine_labs_security_token = os.getenv("PINE_LABS_SECURITY_TOKEN")


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_additional_pm(self):
        sale_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(self.env.company.id),
                ('type', '=', 'sale'),
            ], limit=1)
        return self.env['pos.payment.method'].create([
            {
                'name': 'Demo Razorpay',
                'journal_id': sale_journal.id,
                'payment_method_type': 'terminal',
                'use_payment_terminal': 'razorpay',
                'razorpay_username': razorpay_username,
                'razorpay_tid': razorpay_tid,
                'razorpay_api_key': razorpay_api_key,
                'razorpay_test_mode': True,
                'razorpay_allowed_payment_modes': 'all',
            },
            {
                'name': 'Demo Pine Labs',
                'journal_id': sale_journal.id,
                'payment_method_type': 'terminal',
                'use_payment_terminal': 'pine_labs',
                'pine_labs_merchant': pine_labs_merchant,
                'pine_labs_store': pine_labs_store,
                'pine_labs_client': pine_labs_client,
                'pine_labs_security_token': pine_labs_security_token,
                'pine_labs_allowed_payment_mode': 'all',
                'pine_labs_test_mode': True
            }
        ])

    def _load_l10n_in_resto(self):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(cash_journal_vals={'name': 'Cash IN Restaurant', 'show_on_dashboard': False})
        restaurant_categories = self.get_categories([
            'pos_restaurant.food',
            'pos_restaurant.drinks',
        ])
        resto_config = self.env['pos.config'].create({
            'name': 'IN Restaurant',
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': payment_methods_ids,
            'limit_categories': True,
            'iface_available_categ_ids': restaurant_categories,
            'iface_splitbill': True,
            'module_pos_restaurant': True,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each'
        })
        return resto_config

    def _load_l10n_in_kiosk(self):
        journal, _ = self._create_journal_and_payment_methods()
        restaurant_categories = self.get_record_by_ref([
            'pos_restaurant.food',
            'pos_restaurant.drinks',
        ])
        kiosk_config = self.env['pos.config'].create({
            'name': 'IN Kiosk',
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'limit_categories': True,
            'iface_available_categ_ids': restaurant_categories,
            'iface_splitbill': True,
            'module_pos_restaurant': True,
            'self_ordering_mode': 'kiosk',
            'payment_method_ids': []
        })
        return kiosk_config

    def _load_l10n_in_furn_shop(self):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(cash_journal_vals={'name': 'Cash IN Furn. Shop', 'show_on_dashboard': False})
        furniture_categories = self.get_categories([
            'point_of_sale.pos_category_miscellaneous',
            'point_of_sale.pos_category_desks',
            'point_of_sale.pos_category_chairs'
        ])
        furn_config = self.env['pos.config'].create([{
            'name': 'IN Furniture Shop',
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': payment_methods_ids,
            'limit_categories': True,
            'iface_available_categ_ids': furniture_categories,
        }])
        return furn_config

    def _load_prep_display(self, config_ids, in_company):
        return self.env['pos_preparation_display.display'].with_company(in_company).create({
            'name': 'IN Preparation Display',
            'pos_config_ids': config_ids,
        })

    def load_l10n_in_pos_extra_demo_data(self):
        in_company = self.env.ref('base.demo_company_in')

        configs = self.env['pos.config']
        configs |= self.with_company(in_company)._load_l10n_in_furn_shop()
        configs |= self.with_company(in_company)._load_l10n_in_resto()
        configs |= self.with_company(in_company)._load_l10n_in_kiosk()

        pms = self.with_company(in_company)._get_additional_pm()
        self._load_prep_display(configs[1:].ids, in_company)
        for config in configs:
            if config.name != 'IN Furniture Shop':
                self.with_company(in_company)._add_prep_printer(config)
                self.with_company(in_company)._add_receipt_printer(config)
            self.with_company(in_company)._add_online_payment_provider(config)
            config.write({'payment_method_ids': [Command.link(pm.id) for pm in pms]})
