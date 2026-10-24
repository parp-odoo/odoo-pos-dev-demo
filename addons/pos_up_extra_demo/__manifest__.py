{
    'name': 'POS UrbanPiper Extra Demo',
    'category': 'Sales/Point of Sale',
    'sequence': 69,
    'summary': 'Configure UrbanPiper demo credentials and quick test orders.',
    'description': 'Configure UrbanPiper demo credentials and quick test orders.',
    'depends': ['pos_urban_piper', 'pos_restaurant_extra_demo'],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_up_extra_demo/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'author': 'Parthkumar Patel (PARP)',
    'license': 'LGPL-3',
    'version': '1.1.0',
}
