from odoo import Command, api, models

SIMULATOR_METHOD_NAME = 'DPO Simulator'


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_dpopay_simulator_url(self):
        return (self.env['ir.config_parameter'].sudo().get_str('pos_dpopay_simulator.url') or '').rstrip('/')

    def _get_dpopay_base_url(self, is_token=False):
        simulator_url = self._get_dpopay_simulator_url()
        if not simulator_url:
            return super()._get_dpopay_base_url(is_token=is_token)
        self.ensure_one()
        if is_token:
            return f'{simulator_url}/v1'
        return f'{simulator_url}/ngenius-webapi/payments/push/v1/tid:{self.dpopay_tid}/mid:{self.dpopay_mid}'

    def action_open_dpopay_simulator(self):
        return {'type': 'ir.actions.act_url', 'url': '/pos_dpopay_simulator/', 'target': 'new'}

    @api.model
    def _create_dpopay_simulator_demo_method(self):
        """Add a "DPO Simulator" terminal to the shops of the current company (demo databases)."""
        company = self.env.company
        configs = self.env['pos.config'].search([('company_id', '=', company.id)])
        journal = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(company),
            ('type', '=', 'bank'),
        ], limit=1)
        if not configs or not journal:
            return self
        method = self.search([('name', '=', SIMULATOR_METHOD_NAME), ('company_id', '=', company.id)], limit=1)
        if not method:
            method = self.create({
                'name': SIMULATOR_METHOD_NAME,
                'company_id': company.id,
                'type': 'bank',
                'journal_id': journal.id,
                'payment_method_type': 'terminal',
                'payment_provider': 'dpopay',
                'dpopay_client_id': 'simulator-client',
                'dpopay_client_secret': 'simulator-secret',
                'dpopay_mid': '509404034669',
                'dpopay_tid': '28002683',
                'dpopay_chain_id': 'DPO-SIMULATOR',
                'dpopay_payment_mode': 'card',
                'dpopay_test_mode': True,
            })
        configs.filtered(lambda c: method not in c.payment_method_ids).write({
            'payment_method_ids': [Command.link(method.id)],
        })
        return method
