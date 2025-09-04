
{
    'name': 'POS India localisation Exta Demo',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Helper module for pos developer to save time for configurations',
    'description': """

This module adds Extra demo data and configurations as mensioned below:
- add IN Furniture Shop, IN Resto(with mobile self order) and IN Kiosk configs in Indian Company
- add RazorPay and PineLab payment methods to those config as well.
- create prep display for resto and kiosk
""",
    'depends': ['pos_restaurant_extra_demo', 'l10n_in_pos', 'pos_razorpay', 'pos_pine_labs'],
    'data': [
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
    },
    'installable': True,
    'auto_install': ['l10n_in_pos'],
    'author': 'Parthkumar Patel (PARP)',
    'license': 'OPL-3',
}
