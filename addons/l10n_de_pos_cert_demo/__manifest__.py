
{
    'name': 'PoS Germany Certification Extra Demo',
    'category': 'Accounting/Localizations/Point of Sale',
    'sequence': 69,
    'summary': 'Extra demo data for German PoS certification development',
    'description': """
This module provides additional demo data and configurations for German PoS
certification development:

- Use the local IAP endpoint for the German PoS certification service.
- Append the current day and month to the German demo company name.
- Register the German demo company with Fiskaly when the local IAP service is available.
- Add a German Furniture Shop and German Restaurant PoS configuration.
- Add preparation display and printer configurations.

""",
    'depends': ['l10n_de_pos_res_cert', 'pos_restaurant_extra_demo'],
    'data': [
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
    },
    'installable': True,
    'auto_install': ['l10n_de_pos_res_cert'],
    'author': 'Parthkumar Patel (PARP)',
    'license': 'LGPL-3',
}
