import os

from odoo import Command, _, api, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_additional_pm(self):
        bank_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(self.env.company.id),
                ('type', '=', 'bank'),
            ], limit=1)
        if not bank_journal:
            raise UserError(_('Create a bank journal for the demo company first.'))
        values_list = [
            {
                'name': 'Demo Razorpay',
                'journal_id': bank_journal.id,
                'payment_method_type': 'terminal',
                'use_payment_terminal': 'razorpay',
                'razorpay_username': os.getenv('RAZORPAY_USERNAME'),
                'razorpay_tid': os.getenv('RAZORPAY_TID'),
                'razorpay_api_key': os.getenv('RAZORPAY_API_KEY'),
                'razorpay_test_mode': True,
                'razorpay_allowed_payment_modes': 'all',
            },
            {
                'name': 'Demo Pine Labs',
                'journal_id': bank_journal.id,
                'payment_method_type': 'terminal',
                'use_payment_terminal': 'pine_labs',
                'pine_labs_merchant': os.getenv('PINE_LABS_MERCHANT'),
                'pine_labs_store': os.getenv('PINE_LABS_STORE'),
                'pine_labs_client': os.getenv('PINE_LABS_CLIENT'),
                'pine_labs_security_token': os.getenv('PINE_LABS_SECURITY_TOKEN'),
                'pine_labs_allowed_payment_mode': 'all',
                'pine_labs_test_mode': True
            }
        ]
        PaymentMethod = self.env['pos.payment.method']
        methods = PaymentMethod.search([
            ('name', 'in', [values['name'] for values in values_list]),
            ('company_id', '=', self.env.company.id),
        ])
        missing_values = [values for values in values_list if values['name'] not in methods.mapped('name')]
        return methods | PaymentMethod.create(missing_values)

    def _load_l10n_in_resto(self):
        preset_ids = self.get_record_by_ref([
            'pos_restaurant.pos_takein_preset',
            'pos_restaurant.pos_takeout_preset',
            'pos_restaurant.pos_delivery_preset',
        ])
        return self._get_or_create_demo_config('IN Restaurant', {
            'module_pos_restaurant': True,
            'use_presets': bool(preset_ids),
            'default_preset_id': preset_ids[0] if preset_ids else False,
            'available_preset_ids': [Command.set(preset_ids)],
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
        }, demo_loader='restaurant')

    def _load_l10n_in_kiosk(self):
        return self._get_or_create_demo_config('IN Kiosk', {
            'limit_categories': True,
            'iface_available_categ_ids': [Command.set(self.get_record_by_ref([
                'pos_restaurant.food', 'pos_restaurant.drinks',
            ]))],
            'module_pos_restaurant': True,
            'self_ordering_mode': 'kiosk',
            'payment_method_ids': [Command.clear()],
        })

    def _load_l10n_in_furn_shop(self):
        return self._get_or_create_demo_config('IN Furniture Shop', {}, demo_loader='furniture')

    def _load_prep_display(self, config_ids, in_company):
        Config = self.with_company(in_company)
        return Config._get_or_create_demo_prep_display('IN Preparation Display', Config.browse(config_ids))

    @api.private
    def load_l10n_in_pos_extra_demo_data(self):
        company = self.env.ref('base.demo_company_in', raise_if_not_found=False)
        if not company:
            return
        Config = self.with_company(company)
        furniture = Config._load_l10n_in_furn_shop()
        restaurant = Config._load_l10n_in_resto()
        kiosk = Config._load_l10n_in_kiosk()
        configs = furniture | restaurant | kiosk
        Config._load_prep_display((restaurant | kiosk).ids, company)
        Config._add_prep_printer(restaurant | kiosk)
        Config._add_receipt_printer(configs)
        Config._add_online_payment_provider(configs)
        payment_methods = Config._get_additional_pm()
        configs.write({'payment_method_ids': [Command.link(method.id) for method in payment_methods]})
