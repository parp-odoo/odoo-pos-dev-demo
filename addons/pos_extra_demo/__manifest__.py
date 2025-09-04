
{
    'name': 'Point of Sale Exta Demo',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Helper module for pos developer to save time for configurations',
    'description': """

This module adds Extra demo data and configurations as mensioned below:
- create demo printer (add them to all the config for receipt preinting)
- Create demo-online Payment (add it to all the config)

""",
    'depends': ['point_of_sale', 'pos_online_payment', 'payment_demo'],
    'data': [
        'views/pos_assets_index.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'auto_install': ['point_of_sale'],
    'author': 'Parthkumar Patel (PARP)',
    'license': 'OPL-3',
}
