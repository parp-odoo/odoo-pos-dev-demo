import contextlib
from datetime import date
import os
import socket

from odoo import models, Command
from odoo.addons.l10n_de_pos_cert.models import res_company

local_iap_default_endpoint = os.getenv("LOCAL_IAP_DEFAULT_ENDPOINT")


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _set_l10n_de_pos_cert_endpoint(self):
        res_company.DEFAULT_ENDPOINT = local_iap_default_endpoint

    def _is_local_iap_running(self):
        try:
            with socket.create_connection(("localhost", 8001), timeout=1):
                return True
        except OSError:
            return False

    def _load_de_furn_shop(self):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(
            cash_journal_vals={
                'name': 'Cash DE Furn. Shop',
                'show_on_dashboard': False
            }
        )
        furn_config = self.env['pos.config'].create([{
            'name': 'DE Furniture Shop',
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': payment_methods_ids
        }])
        try:
            furn_config._load_onboarding_furniture_demo_data(True)
        except Exception:
            furn_config._load_onboarding_furniture_demo_data()

        return furn_config

    def _load_de_resto(self):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(
            cash_journal_vals={
                'name': 'Cash DE Restaurant',
                'show_on_dashboard': False
            }
        )
        presets = self.get_record_by_ref([
            'pos_restaurant.pos_takein_preset',
            'pos_restaurant.pos_takeout_preset',
            'pos_restaurant.pos_delivery_preset',
        ])
        resto_config = self.env['pos.config'].create({
            'name': 'DE Restaurant',
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': payment_methods_ids,
            'module_pos_restaurant': True,
            'use_presets': bool(presets),
            'default_preset_id': presets[0] if presets else False,
            'available_preset_ids': [(6, 0, presets)],
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each'
        })
        try:
            resto_config._load_restaurant_demo_data(True)
        except Exception:
            resto_config._load_restaurant_demo_data()
        return resto_config

    def _load_de_prep_display(self, config_ids, in_company):
        if 'pos.prep.display' in self.env:
            return self.env['pos.prep.display'].with_company(in_company).create({
                'name': 'DE Preparation Display',
                'pos_config_ids': config_ids,
            })

    def _add_prep_display_and_printers(self, configs, de_company):
        self._load_de_prep_display(configs[1:].ids, de_company)
        for config in configs:
            if config.name != 'DE Furniture Shop':
                self.with_company(de_company)._add_prep_printer(config)
            self.with_company(de_company)._add_receipt_printer(config)

    def _do_fiskaly_registation(self, de_company):
        de_company.name = f"{de_company.name} {date.today():%d-%m}"

        if self._is_local_iap_running():
            with contextlib.suppress(Exception):
                de_company.l10n_de_action_fiskaly_create_new_keys()

    def _load_l10n_de_pos_demo_data_with_company(self, de_company):
        self._set_l10n_de_pos_cert_endpoint()
        self._do_fiskaly_registation(de_company)

        configs = self.env['pos.config']
        configs |= self._load_de_furn_shop()
        configs |= self._load_de_resto()
        self._add_prep_display_and_printers(configs, de_company)

    def load_l10n_de_pos_cert_demo_data(self):
        de_company = self.env.ref('base.demo_company_de')
        DEConfig = self.env['pos.config'].with_company(de_company)
        DEConfig._load_l10n_de_pos_demo_data_with_company(de_company)
