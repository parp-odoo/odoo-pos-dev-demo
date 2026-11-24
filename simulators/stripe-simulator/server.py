#!/usr/bin/env python3
"""Stripe Terminal simulator.

A dependency-free mock of the parts of the Stripe REST API used by card-present
(Terminal) integrations, plus a drop-in replacement for the Stripe Terminal JS
SDK (https://js.stripe.com/terminal/v1/) served at ``/terminal/v1/``.

    python3 server.py --port 8099

State is saved to state.json (see --state-file) and shared between the REST API (called by your
backend) and the JS SDK simulator (running in the browser), so a PaymentIntent
created server-side can be collected, processed, captured and refunded exactly
like with the real service.
"""

import argparse
import json
import re
import secrets
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

STATIC_DIR = Path(__file__).resolve().parent / "static"

# test card number -> (test payment method, brand, network, funding, outcome)
# outcome: None = success, otherwise (error code, decline_code, message)
TEST_CARDS = {
    "4242424242424242": ("visa", "visa", "visa", "credit", None),
    "4000056655665556": ("visa_debit", "visa", "visa", "debit", None),
    "5555555555554444": ("mastercard", "mastercard", "mastercard", "credit", None),
    "5200828282828210": ("mastercard_debit", "mastercard", "mastercard", "debit", None),
    "5105105105105100": ("mastercard_prepaid", "mastercard", "mastercard", "prepaid", None),
    "378282246310005": ("amex", "amex", "amex", "credit", None),
    "371449635398431": ("amex2", "amex", "amex", "credit", None),
    "6011111111111117": ("discover", "discover", "discover", "credit", None),
    "6011000990139424": ("discover2", "discover", "discover", "credit", None),
    "3056930009020004": ("diners", "diners", "diners", "credit", None),
    "36227206271667": ("diners_14digits", "diners", "diners", "credit", None),
    "3566002020360505": ("jcb", "jcb", "jcb", "credit", None),
    "6200000000000005": ("unionpay", "unionpay", "unionpay", "credit", None),
    "4506445006931933": ("interac", "interac", "interac", "debit", None),
    "6280000360000978": ("eftpos_au_debit", "eftpos_au", "eftpos_au", "debit", None),
    "4000050360000001": ("eftpos_au_visa_debit", "visa", "eftpos_au", "debit", None),
    "5555050360000080": ("eftpos_au_mastercard_debit", "mastercard", "eftpos_au", "debit", None),
    "4000002500001001": ("cartes_bancaires_visa_debit", "visa", "cartes_bancaires", "debit", None),
    "5555552500001001": ("cartes_bancaires_mastercard_debit", "mastercard", "cartes_bancaires", "debit", None),
    "4711009900000316877": ("girocard_debit", "girocard", "girocard", "debit", None),
    "4001007020000002": ("offline_pin_cvm", "visa", "visa", "credit", None),
    "4000008260000075": ("offline_pin_sca_retry", "visa", "visa", "credit", None),
    "4001000360000005": ("online_pin_cvm", "visa", "visa", "credit", None),
    "4000002760000008": ("online_pin_sca_retry", "visa", "visa", "credit", None),
    "4000000000000002": ("charge_declined", "visa", "visa", "credit",
                         ("card_declined", "generic_decline", "Your card was declined.")),
    "4000000000009995": ("charge_declined_insufficient_funds", "visa", "visa", "credit",
                         ("card_declined", "insufficient_funds", "Your card has insufficient funds.")),
    "4000000000009987": ("charge_declined_lost_card", "visa", "visa", "credit",
                         ("card_declined", "lost_card", "Your card was declined.")),
    "4000000000009979": ("charge_declined_stolen_card", "visa", "visa", "credit",
                         ("card_declined", "stolen_card", "Your card was declined.")),
    "4000000000000069": ("charge_declined_expired_card", "visa", "visa", "credit",
                         ("expired_card", None, "Your card has expired.")),
    "4000000000000119": ("charge_declined_processing_error", "visa", "visa", "credit",
                         ("processing_error", None, "An error occurred while processing your card. Try again in a little bit.")),
    "4000000000005126": ("refund_fail", "visa", "visa", "credit", None),
}
CARD_BY_METHOD = {v[0]: k for k, v in TEST_CARDS.items()}
CVM = {
    "offline_pin_cvm": "offline_pin", "offline_pin_sca_retry": "offline_pin",
    "online_pin_cvm": "online_pin", "online_pin_sca_retry": "online_pin",
}
OVERCAPTURE_BRANDS = {"visa", "mastercard", "amex", "discover"}

DEFAULT_READERS = [
    ("SIMULATOR", "Simulated reader", "simulated_wisepos_e"),
    ("WSC513105011295", "Counter 1 (WisePOS E)", "bbpos_wisepos_e"),
    ("STRM26138003393", "Counter 2 (S700)", "stripe_s700"),
]


class StripeError(Exception):
    def __init__(self, status, message, code=None, type_="invalid_request_error", **extra):
        super().__init__(message)
        self.status = status
        self.body = {"error": {"type": type_, "message": message, **({"code": code} if code else {}), **extra}}


def _id(prefix):
    return f"{prefix}_sim{secrets.token_hex(10)}"


def parse_form(body):
    """Decode Stripe-style form encoding (``a[b][c]=v``, ``a[]=v``) to nested dicts/lists."""
    result = {}
    for key, value in parse_qsl(body, keep_blank_values=True):
        match = re.fullmatch(r"([^\[]+)((?:\[[^\]]*\])*)", key)
        if not match:
            continue
        *path, last = [match.group(1), *re.findall(r"\[([^\]]*)\]", match.group(2))]
        is_list = last == "" and path
        if is_list:
            *path, last = path
        node = result
        for part in path:
            node = node.setdefault(part, {})
        if is_list:
            node.setdefault(last, []).append(value)
        else:
            node[last] = value
    return result


class State:
    PERSISTED = ("payment_intents", "charges", "refunds", "readers", "mcc")

    def __init__(self, mcc, path=None):
        self.lock = threading.RLock()
        self.path = Path(path) if path else None
        self.default_mcc = mcc
        self.reset(save=False)
        if self.path and self.path.exists():
            self.load()

    def reset(self, save=True):
        with self.lock:
            self.payment_intents = {}
            self.charges = {}
            self.refunds = {}
            self.readers = {}
            self.log = []
            self.mcc = self.default_mcc
            for serial, label, device_type in DEFAULT_READERS:
                self.add_reader(serial, label, device_type)
            if save:
                self.save()

    def load(self):
        data = json.loads(self.path.read_text())
        for key in self.PERSISTED:
            if key in data:
                setattr(self, key, data[key])
        for reader in self.readers.values():
            reader["_session"] = None

    def save(self):
        if not self.path:
            return
        readers = {k: {**r, "_session": None} for k, r in self.readers.items()}
        data = {key: getattr(self, key) for key in self.PERSISTED} | {"readers": readers}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        os.replace(tmp, self.path)

    def add_reader(self, serial, label=None, device_type="bbpos_wisepos_e"):
        reader = {
            "id": _id("tmr"),
            "object": "terminal.reader",
            "action": None,
            "device_sw_version": "2.37.2.0",
            "device_type": device_type,
            "ip_address": "0.0.0.0" if device_type.startswith("simulated") else "192.168.1.%d" % (len(self.readers) + 10),
            "label": label or serial,
            "last_seen_at": int(time.time() * 1000),
            "livemode": False,
            "location": "tml_simulator",
            "metadata": {},
            "serial_number": serial,
            "status": "online",
            # simulator-only bookkeeping, stripped from API output
            "_session": None,
        }
        self.readers[reader["id"]] = reader
        return reader

    def record(self, entry):
        self.log.append({"at": time.time(), **entry})
        del self.log[:-200]


def public(obj):
    return {k: v for k, v in obj.items() if not k.startswith("_")}


def ok(data, status=HTTPStatus.OK):
    return status, data


class Handler(BaseHTTPRequestHandler):
    server_version = "StripeSimulator/1.0"
    state: State = None

    # --- plumbing ---------------------------------------------------------

    def log_message(self, fmt, *args):
        if not self.server.quiet:
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin") or "*")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Stripe-Version, Idempotency-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _send(self, status, payload, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode() if length else ""
        if "json" in (self.headers.get("Content-Type") or ""):
            return json.loads(raw or "{}")
        return parse_form(raw)

    def _dispatch(self, method):
        url = urlsplit(self.path)
        path = url.path.rstrip("/") or "/"
        query = parse_form(url.query)
        try:
            if method == "GET" and path in ("/terminal/v1", "/terminal/v1/sdk.js"):
                return self._send(200, (STATIC_DIR / "terminal-sim.js").read_bytes(), "application/javascript; charset=utf-8")
            if method == "GET" and path in ("/", "/index.html"):
                return self._send(200, (STATIC_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
            body = self._read_body() if method == "POST" else {}
            loggable = path.startswith("/v1/") or method != "GET"
            for route_method, pattern, handler in ROUTES:
                if route_method != method:
                    continue
                match = re.fullmatch(pattern, path)
                if match:
                    with self.state.lock:
                        try:
                            status, data = handler(self.state, query if method == "GET" else body, *match.groups())
                        except StripeError as e:
                            if loggable:
                                self.state.record({"method": method, "path": path, "status": e.status,
                                                   "error": e.body["error"]["message"],
                                                   "request": query or body, "response": e.body})
                            raise
                        if loggable:
                            self.state.record({"method": method, "path": path, "status": int(status),
                                               "request": query or body, "response": data})
                        if method != "GET":
                            self.state.save()
                    return self._send(status, data)
            raise StripeError(404, f"Unrecognized request URL ({method}: {path}).")
        except StripeError as e:
            self._send(e.status, e.body)
        except Exception as e:  # noqa: BLE001
            self._send(500, {"error": {"type": "api_error", "message": f"Simulator error: {e!r}"}})


# --- helpers ----------------------------------------------------------------

def _get(collection, obj_id, kind):
    obj = collection.get(obj_id)
    if not obj:
        raise StripeError(404, f"No such {kind}: '{obj_id}'", code="resource_missing", param="id")
    return obj


def _int(value, param):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise StripeError(400, f"Invalid integer: {value}", code="parameter_invalid_integer", param=param) from None


def _intent_view(state, pi):
    view = public(pi)
    charges = [public(state.charges[c]) for c in pi["_charges"]]
    view["charges"] = {"object": "list", "data": charges, "has_more": False, "total_count": len(charges),
                       "url": f"/v1/charges?payment_intent={pi['id']}"}
    view["latest_charge"] = pi["_charges"][-1] if pi["_charges"] else None
    return view


def _capture_method(pi, network):
    cm = pi["capture_method"]
    if network == "interac":
        return "automatic"
    pref = pi["payment_method_options"].get("card_present", {}).get("capture_method")
    if pref == "manual_preferred" and network == "eftpos_au":
        return "automatic"
    return cm


# --- REST API (Stripe compatible) ------------------------------------------

def connection_token(state, body):
    return ok({"object": "terminal.connection_token", "secret": "pst_test_" + secrets.token_urlsafe(24),
               "location": body.get("location")})


def create_payment_intent(state, body):
    amount = _int(body.get("amount"), "amount")
    if amount < 1:
        raise StripeError(400, "This value must be greater than or equal to 1.", code="parameter_invalid_integer", param="amount")
    if not body.get("currency"):
        raise StripeError(400, "Missing required param: currency.", code="parameter_missing", param="currency")
    pi_id = _id("pi")
    pi = {
        "id": pi_id,
        "object": "payment_intent",
        "amount": amount,
        "amount_capturable": 0,
        "amount_received": 0,
        "amount_details": {"tip": {}},
        "capture_method": body.get("capture_method", "automatic"),
        "client_secret": f"{pi_id}_secret_{secrets.token_hex(12)}",
        "created": int(time.time()),
        "currency": body["currency"].lower(),
        "description": body.get("description"),
        "last_payment_error": None,
        "livemode": False,
        "metadata": body.get("metadata", {}),
        "payment_method": None,
        "payment_method_options": body.get("payment_method_options", {}),
        "payment_method_types": body.get("payment_method_types", ["card_present"]),
        "status": "requires_payment_method",
        "_charges": [],
        "_card": None,
        "_tip": 0,
    }
    state.payment_intents[pi_id] = pi
    return ok(_intent_view(state, pi))


def get_payment_intent(state, query, pi_id):
    pi = _get(state.payment_intents, pi_id, "payment_intent")
    return ok(_intent_view(state, pi))


def capture_payment_intent(state, body, pi_id):
    pi = _get(state.payment_intents, pi_id, "payment_intent")
    if pi["status"] != "requires_capture":
        raise StripeError(400, f"This PaymentIntent could not be captured because it has a status of {pi['status']}. "
                               "Only a PaymentIntent with one of the following statuses may be captured: requires_capture.",
                          code="payment_intent_unexpected_state", payment_intent=_intent_view(state, pi))
    charge = state.charges[pi["_charges"][-1]]
    to_capture = _int(body.get("amount_to_capture", pi["amount_capturable"]), "amount_to_capture")
    if to_capture > pi["amount_capturable"]:
        if not charge["payment_method_details"]["card_present"].get("overcapture_supported"):
            raise StripeError(400, "The amount_to_capture cannot be greater than the amount_capturable "
                                   "on this PaymentIntent (overcapture is not supported for this charge).",
                              code="amount_too_large", param="amount_to_capture")
        if to_capture > pi["amount_capturable"] * 1.2 + 0.5:
            raise StripeError(400, "Overcapture exceeds the maximum allowed amount (20%).",
                              code="amount_too_large", param="amount_to_capture")
    pi.update(status="succeeded", amount_received=to_capture, amount_capturable=0)
    charge.update(captured=True, amount_captured=to_capture, status="succeeded")
    return ok(_intent_view(state, pi))


def cancel_payment_intent(state, body, pi_id):
    pi = _get(state.payment_intents, pi_id, "payment_intent")
    if pi["status"] in ("succeeded", "canceled"):
        raise StripeError(400, f"You cannot cancel this PaymentIntent because it has a status of {pi['status']}.",
                          code="payment_intent_unexpected_state")
    pi.update(status="canceled", amount_capturable=0, cancellation_reason=body.get("cancellation_reason"),
              canceled_at=int(time.time()))
    for charge_id in pi["_charges"]:
        state.charges[charge_id].update(refunded=True, amount_refunded=state.charges[charge_id]["amount"])
    return ok(_intent_view(state, pi))


def get_charge(state, query, ch_id):
    return ok(public(_get(state.charges, ch_id, "charge")))


def create_refund(state, body):
    if body.get("payment_intent"):
        pi = _get(state.payment_intents, body["payment_intent"], "payment_intent")
        if not pi["_charges"]:
            raise StripeError(400, f"PaymentIntent {pi['id']} does not have a successful charge to refund.",
                              code="charge_not_refundable")
        charge = state.charges[pi["_charges"][-1]]
    elif body.get("charge"):
        charge = _get(state.charges, body["charge"], "charge")
    else:
        raise StripeError(400, "One of the following params should be provided for this request: payment_intent or charge.",
                          code="parameter_missing")
    if not charge["captured"]:
        raise StripeError(400, f"Charge {charge['id']} has not been captured; cancel the PaymentIntent instead.",
                          code="charge_not_refundable")
    available = charge["amount_captured"] - charge["amount_refunded"]
    amount = _int(body.get("amount", available), "amount")
    if amount > available:
        raise StripeError(400, f"Refund amount ({amount}) is greater than unrefunded amount on charge ({available})",
                          code="amount_too_large", param="amount")
    refund = {
        "id": _id("re"),
        "object": "refund",
        "amount": amount,
        "charge": charge["id"],
        "created": int(time.time()),
        "currency": charge["currency"],
        "metadata": body.get("metadata", {}),
        "payment_intent": charge["payment_intent"],
        "reason": body.get("reason"),
        "status": "succeeded",
        "failure_reason": None,
        "_fails": charge["_test_method"] == "refund_fail",
    }
    state.refunds[refund["id"]] = refund
    charge["amount_refunded"] += amount
    charge["refunded"] = charge["amount_refunded"] >= charge["amount_captured"]
    return ok(public(refund))


def get_refund(state, query, re_id):
    refund = _get(state.refunds, re_id, "refund")
    if refund["_fails"] and refund["status"] == "succeeded":
        refund.update(status="failed", failure_reason="expired_or_canceled_card")
        state.charges[refund["charge"]]["amount_refunded"] -= refund["amount"]
        state.charges[refund["charge"]]["refunded"] = False
    return ok(public(refund))


def list_readers(state, query):
    readers = list(state.readers.values())
    if query.get("serial_number"):
        readers = [r for r in readers if r["serial_number"] == query["serial_number"]]
    if query.get("device_type"):
        readers = [r for r in readers if r["device_type"] == query["device_type"]]
    if query.get("status"):
        readers = [r for r in readers if r["status"] == query["status"]]
    limit = _int(query.get("limit", 10), "limit")
    data = [public(r) for r in readers[:limit]]
    return ok({"object": "list", "data": data, "has_more": len(readers) > limit, "url": "/v1/terminal/readers"})


def get_reader(state, query, reader_id):
    return ok(public(_get(state.readers, reader_id, "terminal.reader")))


def get_account(state, query):
    return ok({"id": "acct_simulator", "object": "account", "country": "US", "default_currency": "usd",
               "charges_enabled": True, "business_profile": {"mcc": state.mcc or None, "name": "Stripe Simulator"}})


# --- simulator-only endpoints (used by the JS SDK simulator and dashboard) --

def sim_state(state, query):
    return ok({
        "readers": [public(r) | {"connected": bool(r["_session"])} for r in state.readers.values()],
        "payment_intents": [_intent_view(state, pi) for pi in reversed(state.payment_intents.values())],
        "refunds": [public(r) for r in reversed(state.refunds.values())],
        "log": list(reversed(state.log[-50:])),
        "test_cards": [{"number": n, "test_payment_method": v[0], "brand": v[1], "network": v[2],
                        "outcome": v[4][0] if v[4] else "success"} for n, v in TEST_CARDS.items()],
        "mcc": state.mcc,
    })


def sim_reset(state, body):
    state.reset()
    return ok({"ok": True})


def sim_add_reader(state, body):
    serial = body.get("serial_number")
    if not serial:
        raise StripeError(400, "Missing required param: serial_number.", code="parameter_missing")
    if any(r["serial_number"] == serial for r in state.readers.values()):
        raise StripeError(400, f"A reader with serial number {serial} already exists.", code="resource_already_exists")
    return ok(public(state.add_reader(serial, body.get("label"), body.get("device_type") or "bbpos_wisepos_e")))


def sim_update_reader(state, body, reader_id):
    reader = _get(state.readers, reader_id, "terminal.reader")
    if body.get("status") in ("online", "offline"):
        reader["status"] = body["status"]
        if body["status"] == "offline":
            reader["_session"] = None
    if body.get("label"):
        reader["label"] = body["label"]
    return ok(public(reader))


def sim_delete_reader(state, body, reader_id):
    _get(state.readers, reader_id, "terminal.reader")
    del state.readers[reader_id]
    return ok({"id": reader_id, "object": "terminal.reader", "deleted": True})


def sim_set_mcc(state, body):
    state.mcc = body.get("mcc") or None
    return ok({"mcc": state.mcc})


def sim_discover(state, body):
    simulated = str(body.get("simulated")).lower() in ("1", "true")
    readers = [r for r in state.readers.values()
               if r["device_type"].startswith("simulated") == simulated and r["status"] == "online"]
    return ok({"discoveredReaders": [public(r) for r in readers]})


def sim_connect(state, body, reader_id):
    reader = _get(state.readers, reader_id, "terminal.reader")
    if reader["status"] != "online":
        raise StripeError(400, "The reader is offline.", code="reader_error")
    reader.update(_session=body.get("session"), last_seen_at=int(time.time() * 1000))
    return ok(public(reader))


def sim_disconnect(state, body, reader_id):
    reader = _get(state.readers, reader_id, "terminal.reader")
    if reader["_session"] == body.get("session"):
        reader["_session"] = None
    return ok({})


def sim_collect(state, body, pi_id):
    """Attach a presented card (and optional on-reader tip) to the PaymentIntent."""
    pi = _get(state.payment_intents, pi_id, "payment_intent")
    if body.get("client_secret") != pi["client_secret"]:
        raise StripeError(400, "The client_secret provided does not match the client_secret associated with the PaymentIntent.",
                          code="payment_intent_invalid_parameter")
    if pi["status"] not in ("requires_payment_method", "requires_confirmation"):
        raise StripeError(400, f"This PaymentIntent's payment method could not be updated because it has a status of {pi['status']}.",
                          code="payment_intent_unexpected_state", payment_intent=_intent_view(state, pi))
    number = str(body.get("card") or "")
    if number not in TEST_CARDS:
        number = CARD_BY_METHOD.get(number, "")
    if not number:
        raise StripeError(400, f"Unknown test card: {body.get('card')}", code="invalid_number")
    method, brand, network, funding, _outcome = TEST_CARDS[number]
    pm_type = "interac_present" if network == "interac" else "card_present"
    if pm_type not in pi["payment_method_types"]:
        raise StripeError(400, f"The PaymentMethod type {pm_type} is not allowed on this PaymentIntent "
                               f"(allowed: {', '.join(pi['payment_method_types'])}).", code="payment_method_invalid_parameter")
    tip = _int(body.get("tip") or 0, "tip")
    pi.update(status="requires_confirmation", payment_method=_id("pm"), last_payment_error=None,
              _card=number, _tip=tip, amount_details={"tip": {"amount": tip} if tip else {}})
    return ok(_intent_view(state, pi))


def sim_confirm(state, body, pi_id):
    """processPayment: authorise (or decline) the collected card."""
    pi = _get(state.payment_intents, pi_id, "payment_intent")
    if pi["status"] != "requires_confirmation":
        raise StripeError(400, f"This PaymentIntent's status is {pi['status']}; it must be requires_confirmation to be processed.",
                          code="payment_intent_unexpected_state", payment_intent=_intent_view(state, pi))
    number = pi["_card"]
    method, brand, network, funding, outcome = TEST_CARDS[number]
    pm_type = "interac_present" if network == "interac" else "card_present"
    amount = pi["amount"] + pi["_tip"]
    capture = _capture_method(pi, network)
    details = {
        "brand": brand,
        "network": network,
        "last4": number[-4:],
        "exp_month": 12,
        "exp_year": time.gmtime().tm_year + 3,
        "funding": funding,
        "country": {"interac": "CA", "eftpos_au": "AU"}.get(network, "US"),
        "fingerprint": secrets.token_hex(8),
        "read_method": "contact_emv" if method in CVM else "contactless_emv",
        "cardholder_name": None,
        "emv_auth_data": secrets.token_hex(12).upper(),
        "generated_card": None,
        "receipt": {
            "account_type": "credit" if funding == "credit" else "checking",
            "application_cryptogram": secrets.token_hex(8).upper(),
            "application_preferred_name": brand.upper(),
            "authorization_code": None if outcome else "%06d" % secrets.randbelow(10**6),
            "authorization_response_code": "3035" if outcome else "3030",
            "cardholder_verification_method": CVM.get(method, "none"),
            "dedicated_file_name": "A0000000031010",
            "terminal_verification_results": "0000000000",
            "transaction_status_information": "0000",
        },
        "overcapture_supported": capture == "manual" and network in OVERCAPTURE_BRANDS and brand in OVERCAPTURE_BRANDS,
        "incremental_authorization_supported": False,
    }
    charge = {
        "id": _id("ch"),
        "object": "charge",
        "amount": amount,
        "amount_captured": 0,
        "amount_refunded": 0,
        "captured": False,
        "created": int(time.time()),
        "currency": pi["currency"],
        "failure_code": None,
        "failure_message": None,
        "livemode": False,
        "outcome": {"type": "authorized", "network_status": "approved_by_network", "seller_message": "Payment complete."},
        "paid": True,
        "payment_intent": pi["id"],
        "payment_method": pi["payment_method"],
        "payment_method_details": {"type": pm_type, pm_type: details},
        "refunded": False,
        "status": "succeeded",
        "_test_method": method,
    }
    state.charges[charge["id"]] = charge
    pi["_charges"].append(charge["id"])
    if outcome:
        code, decline_code, message = outcome
        charge.update(paid=False, status="failed", failure_code=code, failure_message=message,
                      outcome={"type": "issuer_declined", "network_status": "declined_by_network",
                               "reason": decline_code, "seller_message": "The bank did not return any further details with this decline."})
        error = {"type": "card_error", "code": code, "message": message, "charge": charge["id"],
                 **({"decline_code": decline_code} if decline_code else {})}
        pi.update(status="requires_payment_method", last_payment_error=error, payment_method=None)
        raise StripeError(402, message, code=code, type_="card_error", charge=charge["id"],
                          **({"decline_code": decline_code} if decline_code else {}),
                          payment_intent=_intent_view(state, pi))
    pi["amount"] = amount
    if capture == "automatic":
        charge.update(captured=True, amount_captured=amount)
        pi.update(status="succeeded", amount_received=amount, amount_capturable=0)
    else:
        pi.update(status="requires_capture", amount_capturable=amount)
    return ok(_intent_view(state, pi))


def sim_refund_card(state, body, ch_id):
    """Terminal SDK refund (collectRefundPaymentMethod + processRefund)."""
    charge = _get(state.charges, ch_id, "charge")
    return create_refund(state, {"charge": charge["id"], "amount": body.get("amount"), "metadata": body.get("metadata", {})})


ROUTES = [
    ("POST", r"/v1/terminal/connection_tokens", connection_token),
    ("POST", r"/v1/payment_intents", create_payment_intent),
    ("GET", r"/v1/payment_intents/([\w-]+)", get_payment_intent),
    ("POST", r"/v1/payment_intents/([\w-]+)/capture", capture_payment_intent),
    ("POST", r"/v1/payment_intents/([\w-]+)/cancel", cancel_payment_intent),
    ("GET", r"/v1/charges/([\w-]+)", get_charge),
    ("POST", r"/v1/refunds", create_refund),
    ("GET", r"/v1/refunds/([\w-]+)", get_refund),
    ("GET", r"/v1/terminal/readers", list_readers),
    ("GET", r"/v1/terminal/readers/([\w-]+)", get_reader),
    ("GET", r"/v1/account", get_account),
    ("GET", r"/sim/state", sim_state),
    ("POST", r"/sim/reset", sim_reset),
    ("POST", r"/sim/mcc", sim_set_mcc),
    ("POST", r"/sim/readers", sim_add_reader),
    ("POST", r"/sim/readers/([\w-]+)", sim_update_reader),
    ("DELETE", r"/sim/readers/([\w-]+)", sim_delete_reader),
    ("POST", r"/sim/discover", sim_discover),
    ("POST", r"/sim/readers/([\w-]+)/connect", sim_connect),
    ("POST", r"/sim/readers/([\w-]+)/disconnect", sim_disconnect),
    ("POST", r"/sim/payment_intents/([\w-]+)/collect", sim_collect),
    ("POST", r"/sim/payment_intents/([\w-]+)/confirm", sim_confirm),
    ("POST", r"/sim/charges/([\w-]+)/refund", sim_refund_card),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--mcc", default="5812", help="merchant category code returned by GET /v1/account (empty for none)")
    parser.add_argument("--quiet", action="store_true", help="don't log each request")
    parser.add_argument("--state-file", default=str(Path(__file__).resolve().parent / "state.json"),
                        help="where intents, refunds and readers are saved across restarts (empty: memory only)")
    args = parser.parse_args()

    Handler.state = State(args.mcc, args.state_file or None)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.quiet = args.quiet
    print(f"Stripe simulator on http://{args.host}:{args.port}")
    print(f"  dashboard   http://localhost:{args.port}/")
    print(f"  JS SDK      http://localhost:{args.port}/terminal/v1/")
    print(f"  REST API    http://localhost:{args.port}/v1/")
    print(f"  state       {args.state_file or 'memory only'}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
