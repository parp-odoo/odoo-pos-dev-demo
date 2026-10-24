{
    'name': 'POS India UrbanPiper Extra Demo',
    'category': 'Sales/Point of Sale',
    'sequence': 69,
    'summary': 'Configure UrbanPiper for the Indian demo restaurant.',
    'description': 'Configure UrbanPiper for the Indian demo restaurant.',
    'depends': ['l10n_in_pos_urban_piper', 'pos_restaurant', 'pos_l10n_in_extra_demo'],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_in_pos_urban_piper'],
    'author': 'Parthkumar Patel (PARP)',
    'license': 'LGPL-3',
    'version': '1.1.0',
}
