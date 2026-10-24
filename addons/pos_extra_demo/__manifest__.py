{
    'name': 'Point of Sale Extra Demo',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Configure receipt printers, demo online payments and fast payment.',
    'description': 'Configure receipt printers, demo online payments and fast payment.',
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
    'license': 'LGPL-3',
    'version': '1.1.0',
    'external_dependencies': {'python': ['dotenv']},
}
