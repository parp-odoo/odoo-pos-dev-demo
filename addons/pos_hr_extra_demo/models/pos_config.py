from odoo import Command, api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _load_pos_hr_extra_demo_data(self):
        admin = self.env.ref('hr.employee_admin')
        # Close only the bundled restaurant demo session before enabling employee login.
        session = self.env.ref('pos_restaurant.pos_open_session_2', raise_if_not_found=False)
        if session and session.state != 'closed':
            self.env['pos.order'].search([
                ('session_id', '=', session.id), ('state', '=', 'draft'),
            ]).write({'state': 'cancel'})
            session.action_pos_session_closing_control()
        configs = self.search([('company_id', '=', admin.company_id.id)])
        values = {
            'module_pos_hr': True,
            'basic_employee_ids': [Command.set(self.env.ref('pos_hr_extra_demo.employee_cashier').ids)],
            'advanced_employee_ids': [Command.set(self.env.ref('pos_hr_extra_demo.employee_manager').ids + admin.ids)],
        }
        # pos_hr writes company-dependent manager fields one configuration at a time.
        for config in configs:
            config.write({field: list(commands) if isinstance(commands, list) else commands
                          for field, commands in values.items()})
