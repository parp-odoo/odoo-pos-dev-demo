import logging
import json

from odoo.http import request
from odoo.tools.json import scriptsafe as json

from odoo.addons.pos_urban_piper.controllers.main import PosUrbanPiperController
from ...pos_enterprise.models.data_validator import object_of, list_of

order_data_schema = object_of({
    'order': object_of({
        'items': list_of(object_of({
            'title': True,
            'price': True,
            'merchant_id': True,
            'quantity': True,
        })),
        'details': object_of({
            'order_subtotal': True,
            'total_taxes': True,
            'order_state': True,
            'channel': True,
            'id': True,
        }),
        'payment': True,
        'store': object_of({
            'merchant_ref_id': True,
        }),
    }),
    'customer': object_of({
        'name': True,
        'email': True,
        'phone': True,
        'address': True,
    }),
})

order_status_update_schema = object_of({
    'order_id': True,
    'new_state': True,
    'store_id': True,
})

rider_status_update_schema = object_of({
    'delivery_info': object_of({
        'current_state': True,
        'delivery_person_details': object_of({
            'name': True,
            'phone': True,
        }),
    }),
    'order_id': True,
    'store': object_of({
        'ref_id': True,
    }),
})

store_action_schema = object_of({
    'status': True,
    'platform': True,
    'action': True,
    'location_ref_id': True,
})


class PosUrbanPiperDemoExtra(PosUrbanPiperController):
    def webhook(self, event_type):
        data = request.get_json_data()
        if event_type == 'order_placed':
            self._handle_data(data, order_data_schema, self._create_order, event_type)
        elif event_type == 'order_status_update':
            self._handle_data(data, order_status_update_schema, self._order_status_update, event_type)
        elif event_type == 'rider_status_update':
            self._handle_data(data, rider_status_update_schema, self._rider_status_update, event_type)
        elif event_type == 'store_action':
            self._handle_data(data, store_action_schema, self._store_action, event_type)
