{
    'name': 'POS India Localization Extra Demo',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Create Indian shop, restaurant and kiosk demos with payment terminals.',
    'description': 'Create Indian shop, restaurant and kiosk demos with payment terminals.',
    'depends': ['pos_restaurant_extra_demo', 'l10n_in_pos', 'pos_razorpay', 'pos_pine_labs'],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_in_pos'],
    'author': 'Parthkumar Patel (PARP)',
    'license': 'LGPL-3',
    'version': '1.1.0',
}
