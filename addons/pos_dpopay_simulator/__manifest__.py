{
    'name': 'POS DPO Pay Simulator',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Route POS DPO Pay traffic to the local DPO Pay simulator (development only)',
    'description': """
Development helper: when installed, the POS DPO Pay integration talks to the DPO
Pay simulator (simulators/dpo-terminal/server.py) instead of network.global. Set
the system parameter ``pos_dpopay_simulator.url`` to the simulator URL as seen
from the Odoo server.

Never install this module on a production database.
""",
    'depends': ['pos_dpopay'],
    'data': [
        'data/ir_config_parameter.xml',
        'views/pos_payment_method_views.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
