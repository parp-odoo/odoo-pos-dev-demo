from odoo import Command, api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _load_pos_hr_extra_demo_data(self):
        admin = self.env.ref('hr.employee_admin')
        configs = self.search([('company_id', '=', admin.company_id.id)])
        values = {
            'module_pos_hr': True,
            'minimal_employee_ids': [Command.set(self.env.ref('pos_hr_extra_demo.employee_minimal').ids)],
            'basic_employee_ids': [Command.set(self.env.ref('pos_hr_extra_demo.employee_cashier').ids)],
            'advanced_employee_ids': [Command.set(self.env.ref('pos_hr_extra_demo.employee_manager').ids + admin.ids)],
        }
        # pos_hr writes company-dependent manager fields one configuration at a time.
        for config in configs:
            config.write({field: list(commands) if isinstance(commands, list) else commands
                          for field, commands in values.items()})
