#!/usr/bin/env python3
"""DPO Pay (Network International N-Genius push API) terminal simulator.

A dependency-free mock of the API used by Odoo's ``pos_dpopay``:

    GET  /v1/tokenkc/generate | /v1/tokenkc/refresh            (Basic auth)
    POST /ngenius-webapi/payments/push/v1/tid:<TID>/mid:<MID>/start-transaction
                                                         .../get-status
                                                         .../get-result
                                                         .../cancel-transaction

plus a dashboard at ``/`` that plays the role of the physical terminal: present a card,
decline, cancel on the terminal, keep the card inserted, take the terminal offline, and
inject API failures (expired token, HTTP 500, slow or dropped responses...).

    python3 server.py --port 8000            # --auto: outcomes driven by the amount's cents

State is saved to state.json (see --state-file) and survives restarts.
"""

import argparse
import base64
import json
import random
import secrets
import socket
import threading
import time
from copy import deepcopy
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import re

STATIC_DIR = Path(__file__).resolve().parent / "static"
PUSH_PATH = re.compile(r"^/ngenius-webapi/payments/push/v1/tid:(?P<tid>[^/]+)/mid:(?P<mid>[^/]+)/(?P<endpoint>[\w-]+)$")
PUSH_ENDPOINTS = {"start-transaction", "get-status", "get-result", "cancel-transaction"}
IDLE_TEXT = "NO TXN / SYSTEM IDLE"
MAX_LOG = 300

# Outcomes a transaction can end with; the dashboard buttons and the auto mode use these keys.
OUTCOMES = {
    "approve_card": {"label": "Approve (card)", "status": "approved", "mode": "card"},
    "approve_momo": {"label": "Approve (Mobile Money)", "status": "approved", "mode": "momo"},
    "decline": {"label": "Decline", "status": "declined", "code": "05", "text": "05 - Do not honour"},
    "insufficient_funds": {"label": "Insufficient funds", "status": "declined", "code": "51", "text": "51 - Insufficient funds"},
    "cancel_terminal": {"label": "Cancel on terminal", "status": "cancelled", "code": "C1", "text": "Cancelled by customer"},
    "error": {"label": "Terminal error", "status": "failed", "code": "96", "text": "96 - System malfunction"},
}

# Auto mode: last two digits of the amount in minor units (e.g. 10.01 -> "01").
MAGIC_CENTS = {
    "00": ("approve_card", "Approve after N polls (card)"),
    "07": ("approve_momo", "Approve after N polls (Mobile Money)"),
    "01": ("decline", "Decline"),
    "06": ("insufficient_funds", "Insufficient funds"),
    "02": ("cancel_terminal", "Customer cancels on the terminal"),
    "08": ("error", "Terminal error"),
    "03": (None, "Never completes (POS times out after 3 min)"),
    "04": ("offline", "Terminal goes offline during the payment"),
    "05": ("result_fails", "Approved, but get-result fails once"),
}

DEFAULT_SETTINGS = {
    "auto_mode": False,
    "polls_to_complete": 2,
    "client_id": "",          # empty: any credentials are accepted
    "client_secret": "",
    "token_ttl": 3600,
}

DEFAULT_SCENARIOS = {
    "token_expired_next": 0,    # next N push calls answer 401 999912 (the backend refreshes the token)
    "invalid_chain_id": False,  # every push call answers 403 999911
    "http_500_next": 0,         # next N push calls answer HTTP 500
    "drop_connection_next": 0,  # next N push calls close the socket without answering
    "result_fails_next": 0,     # next N get-result calls answer HTTP 500
    "cancel_refused": False,    # cancel-transaction is refused
    "slow_ms": 0,               # delay before every push call answers
}


class ApiError(Exception):
    def __init__(self, status, code, message, extra=None):
        super().__init__(message)
        self.status = status
        self.payload = {
            "error_code": str(code),
            "errorCode": str(code),
            "resultCode": str(code),
            "errorMessage": message,
            "resultDescription": message,
            **(extra or {}),
        }


class DropConnection(Exception):
    pass


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


class State:
    def __init__(self, path, auto_mode):
        self.path = Path(path) if path else None
        self.lock = threading.RLock()
        self.data = self._load()
        if auto_mode:
            self.data["settings"]["auto_mode"] = True

    def _empty(self):
        return {
            "settings": deepcopy(DEFAULT_SETTINGS),
            "scenarios": deepcopy(DEFAULT_SCENARIOS),
            "terminals": {},
            "transactions": {},
            "tokens": {},
            "log": [],
            "receipt_no": 0,
        }

    def _load(self):
        data = self._empty()
        if self.path and self.path.exists() and self.path.stat().st_size:
            try:
                stored = json.loads(self.path.read_text())
                for key, value in stored.items():
                    if isinstance(value, dict) and isinstance(data.get(key), dict) and key in ("settings", "scenarios"):
                        data[key].update(value)
                    else:
                        data[key] = value
            except (OSError, ValueError) as error:
                print(f"Ignoring unreadable state file {self.path}: {error}")
        return data

    def save(self):
        if not self.path:
            return
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1))
        tmp.replace(self.path)

    def reset(self):
        with self.lock:
            settings = self.data["settings"]
            self.data = self._empty()
            self.data["settings"] = settings
            self.save()

    # ----- helpers -----------------------------------------------------------------------

    def terminal(self, tid, mid=None):
        terminals = self.data["terminals"]
        if tid not in terminals:
            terminals[tid] = {
                "tid": tid, "mid": mid or "", "online": True, "card_inserted": False,
                "current": None, "created": now_iso(),
            }
        elif mid:
            terminals[tid]["mid"] = mid
        return terminals[tid]

    def log(self, entry):
        self.data["log"].insert(0, entry)
        del self.data["log"][MAX_LOG:]

    def consume(self, key):
        scenarios = self.data["scenarios"]
        if scenarios.get(key, 0) > 0:
            scenarios[key] -= 1
            return True
        return False


# -------------------------------------------------------------------------------------------
# DPO Pay API
# -------------------------------------------------------------------------------------------

class DpoApi:
    def __init__(self, state):
        self.state = state

    @property
    def data(self):
        return self.state.data

    # ----- auth ----------------------------------------------------------------------------

    def token(self, headers):
        auth = headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            raise ApiError(401, "999913", "Invalid Client ID or Client Secret")
        try:
            client_id, _, client_secret = base64.b64decode(auth[6:]).decode().partition(":")
        except ValueError:
            raise ApiError(401, "999913", "Invalid Client ID or Client Secret") from None
        settings = self.data["settings"]
        if settings["client_id"] and (client_id, client_secret) != (settings["client_id"], settings["client_secret"]):
            raise ApiError(401, "999913", "Invalid Client ID or Client Secret")
        token = "sim_" + secrets.token_urlsafe(24)
        self.data["tokens"] = {t: exp for t, exp in self.data["tokens"].items() if exp > time.time()}
        self.data["tokens"][token] = time.time() + settings["token_ttl"]
        return {"access_token": token, "token_type": "Bearer", "expires_in": settings["token_ttl"], "scope": "payments"}

    def _check_push_auth(self, headers):
        auth = headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else ""
        if self.state.consume("token_expired_next"):
            self.data["tokens"].pop(token, None)
            raise ApiError(401, "999912", "Token expired")
        if self.data["tokens"].get(token, 0) < time.time():
            raise ApiError(401, "999913", "Token expired or invalid")
        if not headers.get("Chain-ID") or self.data["scenarios"]["invalid_chain_id"]:
            raise ApiError(403, "999911", "Invalid Chain ID")

    # ----- push endpoints -----------------------------------------------------------------

    def push(self, tid, mid, endpoint, headers, payload):
        if endpoint not in PUSH_ENDPOINTS:
            raise ApiError(404, "404", "Invalid endpoint")
        scenarios = self.data["scenarios"]
        if self.state.consume("drop_connection_next"):
            raise DropConnection()
        if self.state.consume("http_500_next"):
            raise ApiError(500, "500", "Internal Server Error")
        self._check_push_auth(headers)
        terminal = self.state.terminal(tid, mid)
        if not terminal["online"]:
            raise ApiError(403, "403", "Terminal not ready")
        source_id = payload.get("sourceId") or payload.get("sourceid")
        return getattr(self, "_" + endpoint.replace("-", "_"))(terminal, source_id, payload, scenarios)

    def _transaction(self, source_id):
        txn = self.data["transactions"].get(source_id or "")
        if not txn:
            raise ApiError(404, "404", "Transaction not found")
        return txn

    def _start_transaction(self, terminal, source_id, payload, scenarios):
        if not source_id:
            raise ApiError(400, "400", "sourceId is required")
        if source_id in self.data["transactions"]:
            raise ApiError(400, "400", "Duplicate sourceId")
        current = self.data["transactions"].get(terminal["current"] or "")
        if current and current["status"] == "pending":
            raise ApiError(400, "400", "Terminal is busy with another transaction")
        amount = str(payload.get("amount", "0"))
        txn = {
            "sourceId": source_id,
            "tid": terminal["tid"],
            "mid": terminal["mid"],
            "amount": amount,
            "currency": str(payload.get("currency", "")),
            "type": payload.get("transactionType", "pushPaymentSale"),
            "status": "pending",
            "outcome": None,
            "polls": 0,
            "auto": None,
            "created": now_iso(),
            "updated": now_iso(),
            "history": [[now_iso(), "started"]],
        }
        if self.data["settings"]["auto_mode"]:
            txn["auto"] = MAGIC_CENTS.get(amount[-2:].rjust(2, "0"), MAGIC_CENTS["00"])[0]
            if txn["auto"] == "approve_card" and txn["type"] == "pushPaymentDpoMomoSale":
                txn["auto"] = "approve_momo"
        self.data["transactions"][source_id] = txn
        terminal["current"] = source_id
        return {
            "success": True,
            "complete": False,
            "inProgress": True,
            "sourceid": source_id,
            "resultCode": "00",
            "resultCodeDescription": "The service request is processed successfully.",
            "displayText": "PRESENT CARD",
            "type": txn["type"],
        }

    def _get_status(self, terminal, source_id, payload, scenarios):
        if not source_id:
            current = self.data["transactions"].get(terminal["current"] or "")
            busy = current and current["status"] == "pending"
            return {
                "success": True,
                "complete": not busy,
                "inProgress": bool(busy),
                "offline": False,
                "displayText": "PRESENT CARD" if busy else IDLE_TEXT,
            }
        txn = self._transaction(source_id)
        if txn["status"] == "pending":
            txn["polls"] += 1
            if txn["auto"] and txn["polls"] >= self.data["settings"]["polls_to_complete"]:
                self._apply_auto(terminal, txn)
        return self._status_payload(txn)

    def _apply_auto(self, terminal, txn):
        action = txn["auto"]
        if action == "offline":
            txn["auto"] = None
            terminal["online"] = False
            txn["history"].append([now_iso(), "terminal went offline"])
        elif action == "result_fails":
            self.data["scenarios"]["result_fails_next"] += 1
            self.finish(txn, "approve_card")
        elif action in OUTCOMES:
            self.finish(txn, action)

    def finish(self, txn, outcome_key):
        """End a pending transaction the way the terminal would (dashboard and auto mode)."""
        if txn["status"] != "pending":
            raise ApiError(400, "400", f"Transaction is already {txn['status']}")
        outcome = OUTCOMES[outcome_key]
        txn["status"] = outcome["status"]
        txn["outcome"] = outcome_key
        txn["updated"] = now_iso()
        txn["history"].append([now_iso(), outcome["label"]])
        if outcome["status"] == "approved":
            self.data["receipt_no"] += 1
            txn["receiptNo"] = f"{self.data['receipt_no']:06d}"
            txn["authCode"] = f"{random.randint(0, 999999):06d}"
            txn["rrn"] = f"{random.randint(0, 999999999999):012d}"
        terminal = self.data["terminals"].get(txn["tid"])
        if terminal and terminal["current"] == txn["sourceId"]:
            terminal["current"] = None
            terminal["card_inserted"] = False

    def _status_payload(self, txn):
        status = txn["status"]
        payload = {
            "sourceid": txn["sourceId"],
            "type": txn["type"],
            "amount": txn["amount"],
            "currency": txn["currency"],
            "complete": status != "pending",
            "inProgress": status == "pending",
            "success": status in ("pending", "approved"),
            "declined": status == "declined",
            "offline": False,
            "cardInserted": False,
        }
        if status == "pending":
            payload.update(displayText="PRESENT CARD", resultCode="00",
                           resultCodeDescription="The service request is processed successfully.")
        elif status == "approved":
            payload.update(displayText="TRANSACTION COMPLETE", resultCode="00", resultCodeDescription="00 - Approved",
                           result="success")
        else:
            outcome = OUTCOMES.get(txn["outcome"]) or {"code": "C0", "text": "Transaction cancelled"}
            payload.update(displayText=outcome["text"].upper(), resultCode=outcome["code"],
                           resultCodeDescription=outcome["text"], result="failure")
        return payload

    def _get_result(self, terminal, source_id, payload, scenarios):
        txn = self._transaction(source_id)
        if self.state.consume("result_fails_next"):
            raise ApiError(500, "500", "Unable to retrieve the transaction result")
        if txn["status"] == "pending":
            raise ApiError(400, "400", "Transaction in progress")
        result = self._status_payload(txn)
        if txn["status"] != "approved":
            return result
        tx_time = datetime.fromisoformat(txn["updated"])
        result.update({
            "MID": txn["mid"],
            "TID": txn["tid"],
            "ReceiptNo": txn["receiptNo"],
            "TransactionDate": tx_time.strftime("%d/%m/%Y"),
            "TransactionTime": tx_time.strftime("%H:%M"),
            "currencyDecimalPlaces": "2",
            "cashback": "0",
            "tipAmount": "0",
            "cvm": "NONE",
            "signatureRequired": False,
            "Acquirer Name": "DPO PAY",
            "rrn": txn["rrn"],
            "custReceipt": self._receipt(txn, "CUSTOMER COPY"),
            "merchReceipt": self._receipt(txn, "MERCHANT COPY"),
        })
        if txn["outcome"] == "approve_momo":
            result["dataMap"] = {
                "Source": "Mobile Money",
                "MNO": "M-Pesa",
                "Phone Number": "********1132",
                "Transaction Ref": "MP" + txn["rrn"][-8:],
            }
        else:
            result.update({
                "authCode": txn["authCode"],
                "cardType": "VISA",
                "Label": "Visa Debit",
                "panMasked": "4069 04** **** 2831",
                "CardHolderName": "JOHN DOE",
                "cardReadMode": "CTLS",
                "AID": "A0000000031010",
            })
        return result

    def _receipt(self, txn, copy_label):
        return [
            {"style": "body bold-text medium-text small-text split", "text": "DPO Simulator"},
            {"style": "body small-text small-text split", "textLeft": "Merchant ID (MID):", "textRight": txn["mid"]},
            {"style": "body small-text small-text split", "textLeft": "Terminal ID (TID):", "textRight": txn["tid"]},
            {"style": "body small-text small-text split", "textLeft": "Receipt No:", "textRight": txn["receiptNo"]},
            {"style": "body bold-text medium-text small-text split", "text": "Approved"},
            {"style": "body small-text small-text split", "text": copy_label},
        ]

    def _cancel_transaction(self, terminal, source_id, payload, scenarios):
        txn = self._transaction(source_id)
        if txn["status"] != "pending":
            raise ApiError(400, "400", f"Transaction already {txn['status']}")
        if scenarios["cancel_refused"] or terminal["card_inserted"]:
            raise ApiError(400, "400", "Cannot cancel: the card is being processed")
        txn["status"] = "cancelled"
        txn["outcome"] = None
        txn["updated"] = now_iso()
        txn["history"].append([now_iso(), "cancelled by the POS"])
        terminal["current"] = None
        return {
            "success": True,
            "responseCode": "00",
            "resultCode": "00",
            "sourceid": source_id,
            "resultDescription": "Transaction cancelled successfully",
        }


# -------------------------------------------------------------------------------------------
# Dashboard API (/sim/...)
# -------------------------------------------------------------------------------------------

def sim_route(state, api, method, path, body):
    data = state.data
    if method == "GET" and path == "/sim/state":
        return {
            **{key: data[key] for key in ("settings", "scenarios", "terminals", "log")},
            "transactions": sorted(data["transactions"].values(), key=lambda t: t["created"], reverse=True)[:100],
            "outcomes": {key: value["label"] for key, value in OUTCOMES.items()},
            "magic_cents": {cents: label for cents, (_key, label) in MAGIC_CENTS.items()},
        }
    if method != "POST":
        raise ApiError(405, "405", "Method not allowed")
    if path == "/sim/reset":
        state.reset()
        return {"ok": True}
    if path == "/sim/settings":
        for key, value in body.items():
            if key in DEFAULT_SETTINGS:
                data["settings"][key] = type(DEFAULT_SETTINGS[key])(value)
        return data["settings"]
    if path == "/sim/scenarios":
        for key, value in body.items():
            if key in DEFAULT_SCENARIOS:
                data["scenarios"][key] = type(DEFAULT_SCENARIOS[key])(value)
        return data["scenarios"]
    if match := re.fullmatch(r"/sim/terminals/([^/]+)", path):
        terminal = state.terminal(match[1], body.get("mid"))
        for key in ("online", "card_inserted"):
            if key in body:
                terminal[key] = bool(body[key])
        return terminal
    if match := re.fullmatch(r"/sim/terminals/([^/]+)/delete", path):
        data["terminals"].pop(match[1], None)
        return {"ok": True}
    if match := re.fullmatch(r"/sim/transactions/([^/]+)/(\w+)", path):
        txn = api._transaction(match[1])
        if match[2] not in OUTCOMES:
            raise ApiError(400, "400", "Unknown outcome")
        api.finish(txn, match[2])
        return txn
    raise ApiError(404, "404", "Not found")


class Handler(BaseHTTPRequestHandler):
    server_version = "DpoSimulator/1.0"
    state = None
    api = None
    quiet = False

    def log_message(self, fmt, *args):
        if not self.quiet:
            super().log_message(fmt, *args)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, name):
        file = (STATIC_DIR / name).resolve()
        if STATIC_DIR not in file.parents or not file.is_file():
            return self._send_json(404, {"errorMessage": "Not found"})
        content_type = {"html": "text/html", "js": "text/javascript", "css": "text/css"}.get(file.suffix[1:], "application/octet-stream")
        body = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            body = json.loads(raw)
        except ValueError:
            raise ApiError(400, "400", "Invalid JSON body") from None
        return body if isinstance(body, dict) else {}

    def _dispatch(self, method):
        path = urlsplit(self.path).path
        if method == "GET" and path in ("/", "/index.html"):
            return self._send_static("index.html")
        if method == "GET" and path.startswith("/static/"):
            return self._send_static(path[len("/static/"):])

        state, api = self.state, self.api
        started = time.time()
        status, response, body = 200, None, {}
        push = PUSH_PATH.match(path)
        try:
            body = self._read_json() if method == "POST" else {}
            if push and state.data["scenarios"]["slow_ms"]:
                time.sleep(state.data["scenarios"]["slow_ms"] / 1000)
            with state.lock:
                try:
                    if method == "GET" and path in ("/v1/tokenkc/generate", "/v1/tokenkc/refresh"):
                        response = api.token(self.headers)
                    elif method == "POST" and push:
                        response = api.push(push["tid"], push["mid"], push["endpoint"], self.headers, body)
                    elif path.startswith("/sim/"):
                        response = sim_route(state, api, method, path, body)
                    else:
                        raise ApiError(404, "404", "Not found")
                finally:
                    if not path.startswith("/sim/state"):
                        state.save()
        except ApiError as error:
            status, response = error.status, error.payload
        except DropConnection:
            status, response = 0, {"note": "connection dropped"}
        except Exception as error:  # noqa: BLE001 - report simulator bugs to the caller
            status, response = 500, {"errorMessage": f"Simulator error: {error!r}"}
        finally:
            if (push or path.startswith("/v1/")) and state:
                with state.lock:
                    state.log({
                        "time": now_iso(),
                        "method": method,
                        "path": path,
                        "endpoint": push["endpoint"] if push else path.rsplit("/", 1)[-1],
                        "tid": push["tid"] if push else "",
                        "request": body,
                        "status": status,
                        "response": response,
                        "ms": int((time.time() - started) * 1000),
                    })
                    state.save()
        if status == 0:
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.close_connection = True
            return
        self._send_json(status, response)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--state-file", default=str(Path(__file__).resolve().parent / "state.json"),
                        help='where to persist the state ("" keeps it in memory only)')
    parser.add_argument("--auto", action="store_true", help="start with auto mode on (outcome from the amount's cents)")
    parser.add_argument("--quiet", action="store_true", help="don't log every request")
    args = parser.parse_args()

    state = State(args.state_file, args.auto)
    Handler.state = state
    Handler.api = DpoApi(state)
    Handler.quiet = args.quiet
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"DPO Pay simulator on http://localhost:{args.port}/ (auto mode: {state.data['settings']['auto_mode']})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
