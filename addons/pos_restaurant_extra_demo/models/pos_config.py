
from odoo import models, Command


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _add_prep_printer(self, config):
        printer = self.env.ref('pos_restaurant_extra_demo.prep_printer_001', raise_if_not_found=False)
        if not printer:
            return
        if 'is_order_printer' in config:
            config.write({
                'is_order_printer': True,
                'printer_ids': [Command.link(printer.id)]
            })
        elif 'printer_ids' in config:
            config.write({
                'use_order_printer': True,
                'printer_ids': [Command.link(printer.id)]
            })
        else:
            config.write({
                'use_order_printer': True,
                'preparation_printer_ids': [Command.link(printer.id)]
            })

    def _load_pos_self_extra_demo(self):
        kiosk_config = self.search([('name', '=', 'Kiosk')])

        self._add_receipt_printer(kiosk_config)
        self._add_prep_printer(kiosk_config)

        # presets = self.get_record_by_ref([
        #     'pos_restaurant.pos_takein_preset',
        #     'pos_restaurant.pos_takeout_preset',
        #     'pos_restaurant.pos_delivery_preset',
        # ])
        # if len(presets):
        #     kiosk_config.write({
        #         'use_presets': bool(presets),
        #         'default_preset_id': presets[0] if presets else False,
        #         'available_preset_ids': [(6, 0, presets)],
        #     })
        if 'pos.prep.display' in self.env:
            prep_display = self.env['pos.prep.display'].search([])
            if prep_display:
                prep_display.pos_config_ids |= kiosk_config

    def load_pos_restaurant_extra_demo_data(self):
        config_ids = self.get_record_by_ref([
            'pos_restaurant.pos_config_main_restaurant',
            'pos_restaurant.pos_config_main_bar',
        ])
        configs = self.browse(config_ids)

        for config in configs:
            self._add_receipt_printer(config)
            self._add_prep_printer(config)

        resto = configs[0]

        resto.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            # 'self_order_online_payment_method_id': demo_on_pm.id
        })

        if 'pos.prep.display' in self.env:
            prep_display = self.env['pos.prep.display'].search([])
            if prep_display:
                prep_display.pos_config_ids = configs
                prep_display.category_ids = []
        self._load_pos_self_extra_demo()
