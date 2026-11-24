{
    'name': 'POS Stripe Simulator',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Route POS Stripe Terminal traffic to the local Stripe simulator (development only)',
    'description': """
Development helper: when installed, the POS Stripe integration talks to the
Stripe simulator (stripe-simulator/server.py) instead of api.stripe.com and
js.stripe.com. Set the system parameter ``pos_stripe_simulator.url`` to the
simulator URL as seen from the Odoo server.

Never install this module on a production database.
""",
    'depends': ['pos_stripe'],
    'data': [
        'data/ir_config_parameter.xml',
    ],
    'assets': {
        # Also included by point_of_sale._assets_pos.
        'point_of_sale.payment_terminals': [
            'pos_stripe_simulator/static/src/payment_stripe_patch.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
