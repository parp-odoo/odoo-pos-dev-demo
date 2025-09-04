
{
    'name': 'POS Urban IN Piper Exta Demo',
    'category': 'Sales/Point of Sale',
    'sequence': 69,
    'summary': 'Helper module for pos developer to save time for configurations',
    'description': """

This module adds Extra demo data and configurations as mensioned below:
- Enable Urban piper setting IN Furniture Shop
- add ngrok url in system parameter and diable urban piper production mode.
- Fillup credentials for urban piper settings
""",
    'depends': ['l10n_in_pos_urban_piper'],
    'data': [
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
    },
    'installable': True,
    'auto_install': ['l10n_in_pos_urban_piper'],
    'author': 'Parthkumar Patel (PARP)',
    'license': 'OPL-3',
}
