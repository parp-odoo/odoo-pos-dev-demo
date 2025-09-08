
{
    'name': 'POS Urban Piper Exta Demo',
    'category': 'Sales/Point of Sale',
    'sequence': 69,
    'summary': 'Helper module for pos developer to save time for configurations',
    'description': """

This module adds Extra demo data and configurations as mensioned below:
- Enable Urban piper setting Furniture Shop and restaurant for UK-US
- add ngrok url in system parameter and diable urban piper production mode.
- Fillup credentials for urban piper settings
""",
    'depends': ['pos_restaurant_urban_piper', 'pos_urban_piper_ubereats'],
    'data': [
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
    },
    'installable': True,
    'auto_install': True,
    'author': 'Parthkumar Patel (PARP)',
    'license': 'LGPL-3',
}
