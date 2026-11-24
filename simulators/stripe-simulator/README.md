# Stripe Terminal simulator

Offline stand-in for Stripe Terminal. It has three parts:

| Part | What it replaces |
|---|---|
| `server.py` | `api.stripe.com`: connection tokens, PaymentIntents (create, get, capture, cancel), charges, refunds, terminal readers, account |
| `static/terminal-sim.js` (served at `/terminal/v1/`) | `js.stripe.com/terminal/v1/`: the global `StripeTerminal.create(...)` and every method of the [JS SDK](https://docs.stripe.com/terminal/references/api/js-sdk) |
| `pos_stripe_simulator` (in `/home/odoo/odoo/odoo-pos-dev-demo/addons/`) | Odoo addon that sends the `pos_stripe` traffic to the simulator; see its README |

The server needs only Python 3.9 or later and has no dependencies. PaymentIntents, refunds, readers and the MCC are saved to `state.json` next to `server.py` and survive restarts (`--state-file ""` for memory only; **Reset state** on the dashboard clears them).

## Run

```bash
python3 server.py --port 8099          # --mcc "" means the account has no MCC; --quiet stops request logging
```

Open http://localhost:8099/ to get the dashboard. From there you can:
- see readers, PaymentIntents, refunds and the request log;
- add a reader, take one offline, delete it, or change the account MCC;
- use a **playground** that runs the simulated SDK against the simulator.

## Use it with Odoo POS

1. Start the server.
2. Add `/home/odoo/odoo/odoo-pos-dev-demo/addons` to `addons_path` (already done in `odoo-dev.conf`).
3. Install **POS Stripe Simulator** (`pos_stripe_simulator`). Development databases only.
4. If Odoo can't reach the simulator at `http://localhost:8099` (for example under Docker), set the system parameter `pos_stripe_simulator.url` to an address it can reach.
5. On the Stripe POS payment method, set **Stripe Serial Number** to one of these:
   - `SIMULATOR`: Stripe's simulated reader. Like the others it waits for **Present card** unless **Auto-present** is checked (or the page set a card with `setSimulatorConfiguration`).
   - `WSC513105011295` or `STRM26138003393`, or any reader you add on the dashboard: a "physical" reader. You present the card yourself in the reader panel.

The browser never contacts the simulator directly. It goes through `/pos_stripe_simulator/...` on the Odoo server.
- POS and kiosk users (including public users) can reach only the endpoints the SDK needs.
- Internal users can reach all of them.

Only calls made through `pos.payment.method._get_stripe_payment_provider()` go to the simulator. eCommerce Stripe is not affected.

## Reader panel

On any page that loads the SDK, a small draggable panel appears in the bottom-right corner. It acts as the reader screen:
- shows the cart (`setReaderDisplay`), the amount, a tip prompt (10, 15 or 20%, a custom amount, or no tip) and an approved or declined result;
- lets you choose which test card to present, including the decline, PIN, interac, eftpos and refund_fail cards;
- has a **Cancel** button for the customer, shown only when `enable_customer_cancellation` is set;
- has **Auto-present**, which presents the card without any interaction;
- has **Unplug reader**, which triggers `onUnexpectedReaderDisconnect`.

Automated tests (tours, Playwright) can drive it through `window.StripeTerminalSimulator`:

```js
StripeTerminalSimulator.setAutoPresent(true, "4000000000009995"); // auto-decline: insufficient_funds
StripeTerminalSimulator.setLatency(0);
StripeTerminalSimulator.presentCard("5555555555554444");
StripeTerminalSimulator.chooseTip(150);   // minor units
StripeTerminalSimulator.customerCancel();
```

## How faithful it is

- **Responses** use the SDK's shapes: `{discoveredReaders}`, `{reader}`, `{paymentIntent}`, `{refund}`, `{}` for cancels, and `{error: {code, message, decline_code?, payment_intent?}}` for errors.
- **Statuses**: connection status is `connecting`, `connected` or `not_connected`. Payment status is `not_ready`, `ready`, `waiting_for_input` or `processing`. The status-change callbacks receive `{status}`.
- **Errors** include `no_established_connection`, `already_connected`, `command_already_in_progress`, `canceled`, `no_active_collect_payment_method_attempt`, `cancelable_already_completed`, `failed_fetch_connection_token`, `network_error`, `card_declined` and `expired_card`.
- **Simulator configuration**: `setSimulatorConfiguration` (`testCardNumber`, `testPaymentMethod`, `tipAmount`, `paymentMethodType`, `collectInputsResult`) only takes effect on simulated readers. It resets after `processPayment`.
- **Declines** happen during `processPayment`, as on Stripe. The PaymentIntent goes back to `requires_payment_method`.
- **Capture**: interac is captured automatically. So is eftpos when the PaymentIntent uses `manual_preferred`. Every other charge stays `requires_capture`. Overcapture (up to 20%, for tips after payment) works only for Visa, Mastercard, Amex and Discover.
- **Tips** chosen on the reader are added to `amount`, and `amount_details.tip.amount` is set.
- **PaymentIntents** include both `charges` (as in API version 2019-05-16, which Odoo uses) and `latest_charge`.
- **Not simulated**: SetupIntents and `readReusableCard` return `unsupported_operation`. `print` works only on `*v660p` readers. `collectInputs` returns placeholder values.
- **Auth**: secret keys and connection tokens are accepted without being checked.

## Known side effect

`pos_stripe_simulator` patches `PaymentStripe.createStripeTerminal` in the POS bundles. While it is installed, `pos_stripe`'s own Hoot tests run against the patched method.
