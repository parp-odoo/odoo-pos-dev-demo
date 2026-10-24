from odoo import Command, api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _add_prep_printer(self, config):
        printer = self.env.ref('pos_restaurant_extra_demo.prep_printer_001', raise_if_not_found=False)
        if printer:
            config.write({
                'is_order_printer': True,
                'printer_ids': [Command.link(printer.id)],
            })

    def _get_or_create_demo_prep_display(self, name, configs):
        Display = self.env['pos.prep.display'].with_company(self.env.company)
        display = Display.search([
            ('name', '=', name),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        values = {'pos_config_ids': [Command.set(configs.ids)]}
        if display:
            display.write(values)
        else:
            display = Display.create({'name': name, **values})
        return display

    def _load_pos_self_extra_demo(self):
        kiosk = self.search([
            ('name', '=', 'Kiosk'),
            ('company_id', '=', self.env.company.id),
        ])
        self._add_receipt_printer(kiosk)
        self._add_prep_printer(kiosk)
        displays = self.env['pos.prep.display'].search([
            ('company_id', '=', self.env.company.id),
        ])
        displays.write({'pos_config_ids': [Command.link(config.id) for config in kiosk]})

    @api.private
    def load_pos_restaurant_extra_demo_data(self):
        configs = self.browse(self.get_record_by_ref([
            'pos_restaurant.pos_config_main_restaurant',
            'pos_restaurant.pos_config_main_bar',
        ]))
        self._add_receipt_printer(configs)
        self._add_prep_printer(configs)
        restaurant = self.env.ref('pos_restaurant.pos_config_main_restaurant', raise_if_not_found=False)
        if restaurant:
            session = self.env.ref('pos_restaurant.pos_open_session_2', raise_if_not_found=False)
            if session and session.state != 'closed':
                self.env['pos.order'].search([
                    ('session_id', '=', session.id), ('state', '=', 'draft'),
                ]).write({'state': 'cancel'})
                session.action_pos_session_closing_control()
            self._add_online_payment_provider(restaurant)
            restaurant.write({
                'self_ordering_mode': 'mobile',
                'self_ordering_pay_after': 'each',
            })
        for company in configs.company_id:
            displays = self.env['pos.prep.display'].search([('company_id', '=', company.id)])
            displays.write({
                'pos_config_ids': [Command.set(configs.filtered(lambda pos: pos.company_id == company).ids)],
                'category_ids': [Command.clear()],
            })
        self._load_pos_self_extra_demo()
