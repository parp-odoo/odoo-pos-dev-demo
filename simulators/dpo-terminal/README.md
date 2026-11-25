# DPO Pay terminal simulator

Offline stand-in for the DPO Pay (Network International N-Genius push) API used by `pos_dpopay`.

| Part | What it replaces |
|---|---|
| `server.py` | `api(-dev).network.global`: token generation/refresh, `start-transaction`, `get-status`, `get-result`, `cancel-transaction` |
| `static/index.html` (served at `/`) | The physical terminal: present a card, decline, cancel, keep the card inserted, go offline |
| `pos_dpopay_simulator` (in `../../addons/`) | Odoo addon that sends the `pos_dpopay` traffic to the simulator |

Only the Python 3.9+ standard library is needed. Terminals, transactions, scenarios and the request log are saved
to `state.json` next to `server.py` (`--state-file ""` keeps them in memory only; **Reset state** clears them).

## Run

```bash
python3 server.py --port 8000          # --auto: outcome chosen by the amount (see below); --quiet: no request log on stdout
```

Open http://localhost:8000/ for the dashboard (or `/pos_dpopay_simulator/` on the Odoo server when the addon is installed).

## Use it with Odoo POS

1. Start the server.
2. Add `odoo-pos-dev-demo/addons` to `addons_path` (already in `odoo-dev.conf`).
3. Install **POS DPO Pay Simulator** (`pos_dpopay_simulator`). Development databases only.
   Install **PoS Payment Attempts** (`pos_payment_attempt`) as well to log the transactions.
4. If Odoo can't reach `http://localhost:8000` (Docker...), set the system parameter `pos_dpopay_simulator.url`.
5. Payment method: demo databases get a **DPO Simulator** method on every shop. Otherwise create a bank payment
   method with *Integration: Terminal*, provider *DPO Pay*, and any client id/secret, MID, TID and Chain-ID.
   The terminal shows up on the dashboard on the first call; its TID is the method's TID.

Credentials are not checked unless `client_id`/`client_secret` are set in the state settings.

## Terminal panel (manual mode)

While a transaction waits, the terminal shows the amount and these buttons:
**Approve (card)**, **Approve (Mobile Money)**, **Decline**, **Insufficient funds**, **Cancel on terminal**, **Terminal error**.
- **Online** off: every call to this terminal answers `403 Terminal not ready`.
- **Card inserted**: the POS can't cancel (`400 Cannot cancel: the card is being processed`).
- A second transaction while one is pending answers `400 Terminal is busy`.

## Failure scenarios

| Scenario | Effect |
|---|---|
| Expired token on next N calls | `401 999912`; `pos_dpopay` regenerates the token and retries |
| Invalid Chain-ID | `403 999911` on every call |
| HTTP 500 on next N calls | Server error |
| Drop connection on next N calls | The socket is closed with no answer |
| get-result fails on next N calls | Approved on the terminal, but the result can't be fetched |
| Refuse cancel-transaction | Cancels from the POS fail |
| Delay every response | Slow network/terminal |

## Auto mode amounts

Turn on **Auto mode** (or `--auto`). The transaction ends after *Polls before outcome* status polls, depending on the
amount's last two digits:

| Amount | Outcome |
|---|---|
| `x.00` | Approved (card; Mobile Money if the method is in Mobile Money mode) |
| `x.07` | Approved (Mobile Money) |
| `x.01` | Declined |
| `x.06` | Insufficient funds |
| `x.02` | Customer cancels on the terminal |
| `x.08` | Terminal error |
| `x.03` | Never completes: the POS cancels after 3 minutes |
| `x.04` | Terminal goes offline during the payment |
| `x.05` | Approved, but `get-result` fails once |

## Test matrix (with `pos_payment_attempt`)

Transactions are listed in *Point of Sale › Orders › Terminal Transactions*, one line per DPO `sourceId`.

| Flow | How | POS | Line state |
|---|---|---|---|
| Approved | Approve | Line done, order validated | `success` |
| Declined | Decline / Insufficient funds | Error dialog, line **Retry** | `failed` + reason |
| Customer cancels | Cancel on terminal | Error dialog, line **Retry** | `failed` ("Cancelled by customer") |
| Cashier cancels | Cancel on the payment line | Line **Retry** | `cancelled` |
| Cancel refused | Card inserted, then cancel | Error, still waiting | stays `processing` |
| No answer | Do nothing for 3 minutes (`x.03`) | POS cancels, line **Retry** | `timeout` |
| Terminal offline | Online off, then pay | "Terminal not ready" | no line (the readiness check fails first) |
| Token expired | Expired token = 1 | Nothing visible | unchanged (token refreshed) |
| Result lost | get-result fails = 1, approve | Error, line **Retry** | stays `processing` |
| Connection lost | Drop connection = 3 while waiting | Line **Force done** offered | last known state (forcing happens in the POS only) |
| Retry after failure | Decline, then Retry + Approve | Line done | two lines: `failed`, `success` |
