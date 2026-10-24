{
    'name': 'POS Germany Certification Extra Demo',
    'category': 'Accounting/Localizations/Point of Sale',
    'sequence': 69,
    'summary': 'Configure German POS certification, shops, displays and printers.',
    'description': 'Configure German POS certification, shops, displays and printers.',
    'depends': ['l10n_de_pos_res_cert', 'pos_restaurant_extra_demo'],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_de_pos_res_cert'],
    'author': 'Parthkumar Patel (PARP)',
    'license': 'LGPL-3',
    'version': '1.1.0',
}
