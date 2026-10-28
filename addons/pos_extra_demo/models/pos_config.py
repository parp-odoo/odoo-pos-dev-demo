from odoo import Command, api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.private
    def get_record_by_ref(self, record_refs):
        return [
            record.id for xml_id in record_refs
            if (record := self.env.ref(xml_id, raise_if_not_found=False))
        ]

    def _create_demo_online_pm(self):
        provider = self.env.ref('payment.payment_provider_demo', raise_if_not_found=False)
        if not provider:
            return self.env['pos.payment.method']
        if provider.company_id != self.env.company:
            provider = self.env['payment.provider'].search([
                ('code', '=', 'demo'), ('company_id', '=', self.env.company.id),
            ], limit=1) or provider.copy({'company_id': self.env.company.id})
        return self.env['pos.payment.method'].create({
            'name': 'Demo Online',
            'company_id': self.env.company.id,
            'is_online_payment': True,
            'online_payment_provider_ids': [Command.link(provider.id)],
        })

    def _add_online_payment_provider(self, config):
        payment_methods = self.env['pos.payment.method']
        for company in config.company_id:
            PaymentMethod = self.env['pos.payment.method'].with_company(company)
            payment_method = PaymentMethod.search([
                ('name', 'in', ['Online Payment', 'Demo Online']),
                ('company_id', '=', company.id),
            ], limit=1)
            if not payment_method:
                payment_method = self.with_company(company)._create_demo_online_pm()
            if payment_method:
                config.filtered(lambda pos: pos.company_id == company).write({
                    'payment_method_ids': [Command.link(payment_method.id)],
                })
                payment_methods |= payment_method
        return payment_methods

    def _add_receipt_printer(self, config):
        printer = self.env.ref('pos_extra_demo.receipt_printer_001', raise_if_not_found=False)
        if printer:
            config.write({
                'other_devices': True,
                'iface_cashdrawer': True,
                'preparation_devices': True,
                'receipt_printer_ids': [Command.link(printer.id)],
                'default_receipt_printer_id': printer.id,
            })

    def _get_or_create_demo_config(self, name, values, demo_loader=None):
        config = self.search([
            ('name', '=', name),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if config:
            return config
        journal, payment_commands = self._create_journal_and_payment_methods(
            cash_journal_vals={'name': 'Cash %s' % name, 'show_on_dashboard': False},
        )
        config = self.create({
            'name': name,
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': payment_commands,
            **values,
        })
        if demo_loader:
            # Only the two onboarding loaders are accepted from our localization helpers.
            if demo_loader == 'furniture':
                config._load_onboarding_furniture_demo_data(True)
            elif demo_loader == 'restaurant':
                config._load_restaurant_demo_data(True)
        return config

    @api.private
    def load_pos_extra_demo_data(self):
        configs = self.browse(self.get_record_by_ref([
            'point_of_sale.pos_config_main',
            'point_of_sale.pos_config_clothes',
            'point_of_sale.pos_config_bakery',
        ]))
        self._add_receipt_printer(configs)
        self._add_online_payment_provider(configs)
        furniture_shop = self.env.ref('point_of_sale.pos_config_main', raise_if_not_found=False)
        if furniture_shop:
            furniture_shop.write({
                'use_fast_payment': True,
                'fast_payment_method_ids': [Command.set(furniture_shop.payment_method_ids.filtered(
                    lambda method: method.name in ('Cash', 'Card')
                ).ids)],
            })
