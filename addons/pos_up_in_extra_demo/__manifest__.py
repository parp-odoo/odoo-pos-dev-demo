
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
    'depends': ['pos_up_extra_demo', 'pos_urban_piper_swiggy', 'pos_urban_piper_zomato'],
    'data': [
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
    },
    'installable': True,
    'auto_install': ['pos_up_extra_demo'],
    'author': 'Parthkumar Patel (PARP)',
    'license': 'LGPL-3',
}
