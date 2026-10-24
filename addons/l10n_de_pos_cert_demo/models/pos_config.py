from datetime import date
import logging
import os
import socket
from urllib.parse import urlsplit

import requests

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _set_l10n_de_pos_cert_endpoint(self):
        endpoint = os.getenv('LOCAL_IAP_DEFAULT_ENDPOINT')
        if endpoint:
            self.env['ir.config_parameter'].set_str('l10n_de_fiskaly_iap.endpoint', endpoint)
        return endpoint

    def _is_local_iap_running(self):
        endpoint = os.getenv('LOCAL_IAP_DEFAULT_ENDPOINT')
        if not endpoint:
            return False
        url = urlsplit(endpoint)
        if not url.hostname:
            return False
        try:
            with socket.create_connection((url.hostname, url.port or (443 if url.scheme == 'https' else 80)), timeout=1):
                return True
        except OSError:
            return False

    def _load_de_furn_shop(self):
        return self._get_or_create_demo_config(
            'DE Furniture Shop', {}, demo_loader='furniture',
        )

    def _load_de_resto(self):
        preset_ids = self.get_record_by_ref([
            'pos_restaurant.pos_takein_preset',
            'pos_restaurant.pos_takeout_preset',
            'pos_restaurant.pos_delivery_preset',
        ])
        return self._get_or_create_demo_config('DE Restaurant', {
            'module_pos_restaurant': True,
            'use_presets': bool(preset_ids),
            'default_preset_id': preset_ids[0] if preset_ids else False,
            'available_preset_ids': [(6, 0, preset_ids)],
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
        }, demo_loader='restaurant')

    def _load_de_prep_display(self, config_ids, in_company):
        Config = self.with_company(in_company)
        return Config._get_or_create_demo_prep_display(
            'DE Preparation Display', Config.browse(config_ids),
        )

    def _add_prep_display_and_printers(self, configs, de_company):
        Config = self.with_company(de_company)
        restaurants = configs.filtered(lambda config: config.module_pos_restaurant)
        Config._load_de_prep_display(restaurants.ids, de_company)
        Config._add_prep_printer(restaurants)
        Config._add_receipt_printer(configs)

    def _do_fiskaly_registation(self, de_company):
        suffix = date.today().strftime('%d-%m')
        if not de_company.name.endswith(suffix):
            de_company.name = '%s %s' % (de_company.name, suffix)
        if not self._is_local_iap_running():
            return
        try:
            with self.env.cr.savepoint():
                de_company.l10n_de_action_fiskaly_create_new_keys()
        except (UserError, requests.RequestException):
            _logger.exception('Could not register the German demo company with local IAP')

    def _load_l10n_de_pos_demo_data_with_company(self, de_company):
        self._set_l10n_de_pos_cert_endpoint()
        self._do_fiskaly_registation(de_company)
        configs = self._load_de_furn_shop() | self._load_de_resto()
        self._add_prep_display_and_printers(configs, de_company)

    @api.private
    def load_l10n_de_pos_cert_demo_data(self):
        company = self.env.ref('base.demo_company_de', raise_if_not_found=False)
        if company:
            self.with_company(company)._load_l10n_de_pos_demo_data_with_company(company)
