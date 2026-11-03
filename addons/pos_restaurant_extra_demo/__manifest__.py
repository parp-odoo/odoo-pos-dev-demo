
{
    'name': 'Restaurant Extra Demo',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Helper module for pos developer to save time for configurations',
    'description': """

This module adds Extra demo data and configurations as mensioned below:
- add demo printer to config (resto, bar & kiosk) as receipt as well as prep printer
- add preset data in kiosk
- add "QR + Ordering" self-ordering mode to restaurant
- In Kitchen Display add kiosk config and Drinks pos category

""",
    'depends': ['pos_restaurant', 'pos_self_order', 'pos_extra_demo', 'pos_enterprise'],
    'data': [
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'pos_self_order.assets': [
            ('include', 'pos_extra_demo._assets_debug_menu'),
        ],
        'pos_preparation_display.assets': [
            ('include', 'pos_extra_demo._assets_debug_menu'),
        ],
    },
    'installable': True,
    'auto_install': True,
    'author': 'Parthkumar Patel (PARP)',
    'license': 'LGPL-3',
}
