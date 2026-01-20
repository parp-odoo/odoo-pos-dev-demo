import logging
from odoo import models, Command

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_record_by_ref(self, recordRefs):
        # Here because it is not there in older version of base code
        return [self.env.ref(record).id for record in recordRefs if self.env.ref(record, raise_if_not_found=False)]

    def _create_demo_online_pm(self):
        provider_demo = self.env.ref('payment.payment_provider_demo', raise_if_not_found=False)
        if not provider_demo:
            return False
        return self.env['pos.payment.method'].create({
            'name': 'Demo Online',
            'is_online_payment': True,
            'online_payment_provider_ids': [Command.link(provider_demo.id)]
        })

    def _add_online_payment_provider(self, config):
        demo_online_pm = self.env['pos.payment.method'].search([('name', 'in', ['Online Payment', 'Demo Online']), ('company_id', '=', self.env.company.id)])
        if not demo_online_pm:
            demo_online_pm = self._create_demo_online_pm()
        if demo_online_pm and config:
            config.write({'payment_method_ids': [Command.link(demo_online_pm.id)]})
        return demo_online_pm

    def _add_receipt_printer(self, config):
        config.write({
            'other_devices': True,
            'epson_printer_ip': 'pos.stva.ovh/test-p'
        })

    def load_pos_extra_demo_data(self):
        config_ids = self.get_record_by_ref([
            'point_of_sale.pos_config_main',
            'point_of_sale.pos_config_clothes',
            'point_of_sale.pos_config_bakery'
        ])
        configs = self.browse(config_ids)

        for config in configs:
            self._add_receipt_printer(config)
            self._add_online_payment_provider(config)
