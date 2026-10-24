from datetime import datetime, timedelta
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.pos_urban_piper.controllers.main import PosUrbanPiperController


class UrbanPiperTestOrderWizard(models.TransientModel):
    _name = 'pos.urbanpiper.test.order.wizard'
    _description = 'Urbanpiper test order wizard'

    product_id = fields.Many2one(
        'product.template',
        required=True,
        string='Product',
        help='Test order product',
        domain="[('available_in_pos', '=', True)]"
    )
    quantity = fields.Integer(
        string='Quantity',
        default=1,
        required=True,
        help='Test order quantity',
    )
    discount_amount = fields.Integer(
        string="Fixed Discount Amount",
        default=0,
        help='Fixed discount value for test order.'
    )
    packaging_charge = fields.Integer(
        string='Packaging Charge',
        help='Packaging charge for test order.'
    )
    delivery_charge = fields.Integer(
        string='Delivery Charge',
        help='Delivery charges for test order.'
    )
    delivery_instruction = fields.Char(
        string='Delivery Instructions',
        help='Instructions for test order.'
    )
    delivery_provider_id = fields.Many2one(
        'pos.delivery.provider',
        required=True,
        string='Delivery Provider',
        help='Responsible delivery provider for test order, e.g., UberEats, Zomato.'
    )

    @api.constrains('quantity', 'discount_amount', 'packaging_charge', 'delivery_charge')
    def _check_demo_order_amounts(self):
        for wizard in self:
            if wizard.quantity <= 0:
                raise ValidationError(_('The demo order quantity must be positive.'))
            if min(wizard.discount_amount, wizard.packaging_charge, wizard.delivery_charge) < 0:
                raise ValidationError(_('Demo order amounts cannot be negative.'))

    @api.private
    def test_order_json(self, data):
        taxes = data['product_id'].taxes_id.compute_all(
            data['product_id'].list_price, data['product_id'].currency_id, data['quantity']
        )
        unit_price = data['product_id'].taxes_id.compute_all(
            data['product_id'].list_price, data['product_id'].currency_id, 1
        )['total_excluded']
        price_with_tax = taxes['total_included']
        price_without_tax = taxes['total_excluded']
        now = datetime.now()
        pickup_time = int((now + timedelta(minutes=25)).timestamp() * 1000)
        payload = {
            "customer": {
                "username": "meet_jivani",
                "name": "Meet Jivani",
                "id": 1111111,
                "phone": "+919999999999",
                "address": {
                    "is_guest_mode": False,
                    "city": "Gujarat",
                    "pin": "380007",
                    "line_1": "401 & 402, Floor 4, IT Tower 3",
                    "line_2": "InfoCity Gate, 1, Gandhinagar,",
                    "sub_locality": "Test Area"
                },
                "email": "test_user@email.com"
            },
            "order": {
                "next_states": ["Acknowledged", "Food Ready", "Dispatched", "Completed", "Cancelled"],
                "items": [{
                    "food_type": data['product_id'].urbanpiper_meal_type,
                    "total": price_without_tax,
                    "id": 1111111,
                    "title": data['product_id'].name,
                    "total_with_tax": price_with_tax,
                    "discounts": [],
                    "tags": [],
                    "price": unit_price,
                    "discount": 0.0,
                    "merchant_id": f'{data["product_id"].id}-XXXXX',
                    "instructions": "",
                    "charges": [],
                    "extras": {},
                    "image_url": None,
                    "total_charge": 0.0,
                    "is_recommended": False,
                    "quantity": data['quantity']
                }],
                "details": {
                    "coupon": "",
                    "total_taxes": price_with_tax - price_without_tax,
                    "merchant_ref_id": None,
                    "order_level_total_charges": 0,
                    "id": data['delivery_identifier'],
                    "payable_amount": price_with_tax,
                    "total_external_discount": 0.0,
                    "order_total": price_with_tax,
                    "expected_pickup_time": pickup_time,
                    "state": "Placed",
                    "discount": 0.0,
                    "channel": data['delivery_provider_id'].technical_name,
                    "delivery_datetime": pickup_time,
                    "item_level_total_charges": 0,
                    "item_taxes": 0.0,
                    "modified_to": None,
                    "item_level_total_taxes": price_with_tax - price_without_tax,
                    "order_state": "Placed",
                    "instructions": "Test order instructions",
                    "created": int(now.timestamp() * 1000),
                    "charges": [],
                    "country": "India",
                    "biz_name": "Odoo_IN",
                    "taxes": [],
                    "prep_time": {
                        "max": 85.0,
                        "adjustable": True,
                        "estimated": 25.0,
                        "min": 0.0
                    },
                    "ext_platforms": [{
                        "kind": "food_aggregator",
                        "name": data['delivery_provider_id'].technical_name,
                        "delivery_type": "partner",
                        "extras": {
                            "order_otp": "4175",
                            "deliver_asap": True,
                            "is_delivery_charge_discounted": False,
                            "can_reject_order": True,
                        },
                        "platform_store_id": "6546563516",
                        "id": "MNHLAW3L"
                    }],
                    "order_level_total_taxes": 0,
                    "order_subtotal": price_without_tax,
                },
                "payment": [{
                    "amount": price_with_tax,
                    "option": "payment_gateway",
                    "srvr_trx_id": None
                }],
                "store": {
                    "city": "Gandhinagar",
                    "name": "Odoo India",
                    "merchant_ref_id": data['config_id'].urbanpiper_store_identifier,
                    "address": "401 & 402, Floor 4, IT Tower 3 InfoCity Gate, 1, Gandhinagar, Gujarat 382007",
                    "id": 11111
                },
                "next_state": "Acknowledged",
                "urban_piper_test": True,
            }
        }
        payload['order']['details']['charges'] = [{
            'taxes': [{
                'rate': None,
                'liability_on': 'aggregator',
                'value': amount * 0.15,
                'title': 'VAT',
            }],
            'value': amount,
            'title': title,
        } for title, amount in (
            ('Packaging Charge', data['packaging_charge']),
            ('Delivery Charge', data['delivery_charge']),
        ) if amount > 0]
        discounts = []
        if data['discount_amount'] > 0:
            discounts.append({
                'is_merchant_discount': True,
                'code': 'CRICKET',
                'value': data['discount_amount'],
                'title': 'Merchant Discount'
            })
        payload['order']['details']['ext_platforms'][0]['discounts'] = discounts
        if data['delivery_instruction']:
            payload['order']['details']['instructions'] = data['delivery_instruction']
        return payload

    def make_test_order(self, delivery_identifier=False):
        self.ensure_one()
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_('Only Point of Sale users can place demo orders.'))
        config_id = self.env['pos.config'].browse(self.env.context.get('config_id')).exists()
        config_id.ensure_one()
        config_id.check_access('read')
        if config_id.company_id not in self.env.companies:
            raise AccessError(_('The Point of Sale belongs to another company.'))
        if self.delivery_provider_id not in config_id.urbanpiper_delivery_provider_ids:
            raise ValidationError(_('Select a configured delivery provider.'))
        self.product_id.check_access('read')
        if not self.product_id.available_in_pos or (
            self.product_id.company_id and self.product_id.company_id != config_id.company_id
        ):
            raise ValidationError(_('Select a Point of Sale product from the same company.'))
        msg = ''
        if not config_id.current_session_id:
            msg += _('Please start a POS session first.\n')
        if not config_id.urbanpiper_store_identifier:
            msg += _('POS ID is required to place test order.\n')
        if msg:
            return self._display_notification(msg, 'danger')
        data = {
            'config_id': config_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'discount_amount': self.discount_amount,
            'packaging_charge': self.packaging_charge,
            'delivery_charge': self.delivery_charge,
            'delivery_instruction': self.delivery_instruction,
            'delivery_provider_id': self.delivery_provider_id,
            'delivery_identifier': delivery_identifier or str(uuid.uuid4())
        }
        order_json = self.test_order_json(data)
        UpController = PosUrbanPiperController()
        UpController._create_order(order_json)
        return self._display_notification(_('Test order generated successfully.'))

    def _display_notification(self, message, notification_type='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Urban Piper'),
                'message': message,
                'type': notification_type,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},  # force a form reload
            }
        }
