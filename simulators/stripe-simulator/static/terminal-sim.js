/*
 * Stripe Terminal JS SDK simulator.
 *
 * Drop-in replacement for https://js.stripe.com/terminal/v1/ that talks to the
 * simulator server (server.py) instead of Stripe. It exposes the same global
 * `StripeTerminal.create(...)` API and renders a "virtual reader" panel on the
 * page so you can present test cards, pick tips or cancel as the customer.
 *
 * The server base URL is derived from this script's URL (".../terminal/v1/"
 * stripped), or forced with `window.STRIPE_SIMULATOR_URL` before loading.
 */
(function () {
    "use strict";

    const scriptSrc = document.currentScript && document.currentScript.src;
    let BASE_URL = (
        window.STRIPE_SIMULATOR_URL ||
        (scriptSrc ? scriptSrc.replace(/\/terminal\/v1(\/.*)?$/, "") : "")
    ).replace(/\/$/, "");

    const SIMULATED_DEFAULT_CARD = "4242424242424242";
    const INTERAC_DEFAULT_CARD = "4506445006931933";
    const ZERO_DECIMAL = new Set([
        "bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg", "rwf", "ugx", "vnd", "vuv", "xaf", "xof", "xpf",
    ]);
    const STORAGE_KEY = "stripe-terminal-simulator";
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const err = (code, message, extra = {}) => ({ error: { code, message, ...extra } });

    const prefs = loadPrefs();
    // All terminals created on the page (the POS creates one per Stripe payment method).
    const terminals = new Set();

    function loadPrefs() {
        try {
            return { autoPresent: false, card: SIMULATED_DEFAULT_CARD, latency: 400, collapsed: false, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
        } catch {
            return { autoPresent: false, card: SIMULATED_DEFAULT_CARD, latency: 400, collapsed: false };
        }
    }

    function savePrefs() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
        } catch {
            /* storage unavailable: keep in memory only */
        }
    }

    async function api(method, path, body, keepalive = false) {
        let response;
        try {
            response = await fetch(BASE_URL + path, {
                method,
                headers: body ? { "Content-Type": "application/json" } : {},
                body: body ? JSON.stringify(body) : undefined,
                credentials: "include",
                keepalive,
            });
        } catch (e) {
            return err("network_error", `Could not reach the Stripe simulator at ${BASE_URL || location.origin}: ${e.message}`);
        }
        let data;
        try {
            data = await response.json();
        } catch {
            return err("network_error", `Invalid response from the Stripe simulator (HTTP ${response.status}).`);
        }
        if (!response.ok) {
            const { code = "reader_error", message = `HTTP ${response.status}`, ...extra } = data.error || {};
            delete extra.type;
            return err(code, message, extra);
        }
        return { data };
    }

    function formatAmount(amount, currency = "usd") {
        const value = ZERO_DECIMAL.has(currency.toLowerCase()) ? amount : amount / 100;
        try {
            return new Intl.NumberFormat(undefined, { style: "currency", currency: currency.toUpperCase() }).format(value);
        } catch {
            return `${value} ${currency.toUpperCase()}`;
        }
    }

    // ---------------------------------------------------------------------
    // Virtual reader panel
    // ---------------------------------------------------------------------

    const CSS = `
#ssim-panel{position:fixed;right:16px;bottom:16px;z-index:2147483000;width:300px;font:13px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#1a1f36;background:#fff;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.28);overflow:hidden;user-select:none}
#ssim-panel *{box-sizing:border-box}
#ssim-panel .ssim-head{display:flex;align-items:center;gap:8px;padding:8px 12px;background:#635bff;color:#fff;cursor:move}
#ssim-panel .ssim-head b{flex:1;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#ssim-panel .ssim-dot{width:8px;height:8px;border-radius:50%;background:#ff6b6b;flex:none}
#ssim-panel .ssim-dot.on{background:#3ce08f}
#ssim-panel .ssim-dot.busy{background:#ffd166}
#ssim-panel .ssim-toggle{background:none;border:0;color:#fff;font-size:16px;cursor:pointer;padding:0 2px}
#ssim-panel .ssim-screen{margin:12px;min-height:150px;border-radius:10px;background:#0a2540;color:#fff;padding:14px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;gap:8px}
#ssim-panel .ssim-screen .ssim-amount{font-size:26px;font-weight:700}
#ssim-panel .ssim-screen .ssim-sub{opacity:.75}
#ssim-panel .ssim-screen.ok{background:#0e7a4d}
#ssim-panel .ssim-screen.ko{background:#b3261e}
#ssim-panel .ssim-cart{width:100%;text-align:left;font-size:12px}
#ssim-panel .ssim-cart div{display:flex;justify-content:space-between;gap:8px}
#ssim-panel .ssim-cart .ssim-total{border-top:1px solid rgba(255,255,255,.3);margin-top:4px;padding-top:4px;font-weight:700}
#ssim-panel .ssim-btns{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;width:100%}
#ssim-panel button.ssim-btn{border:0;border-radius:6px;padding:6px 10px;font:inherit;font-weight:600;cursor:pointer;background:#fff;color:#0a2540}
#ssim-panel button.ssim-btn.primary{background:#635bff;color:#fff}
#ssim-panel button.ssim-btn.danger{background:#ff6b6b;color:#fff}
#ssim-panel .ssim-controls{padding:0 12px 12px;display:grid;gap:6px}
#ssim-panel .ssim-controls label{display:flex;align-items:center;gap:6px}
#ssim-panel select,#ssim-panel input[type=number]{width:100%;font:inherit;padding:4px;border:1px solid #c4c9d4;border-radius:6px;background:#fff;color:#1a1f36}
#ssim-panel .ssim-row{display:flex;gap:6px}
#ssim-panel .ssim-row > *{flex:1}
#ssim-panel .ssim-link{background:none;border:1px solid #c4c9d4;border-radius:6px;padding:4px;font:inherit;cursor:pointer;color:#1a1f36}
#ssim-panel.collapsed .ssim-body{display:none}
`;

    class ReaderPanel {
        constructor() {
            this.cards = [];
            this.waiter = null;
            this.build();
            this.loadCards();
        }

        build() {
            if (!document.getElementById("ssim-style")) {
                const style = document.createElement("style");
                style.id = "ssim-style";
                style.textContent = CSS;
                (document.head || document.documentElement).appendChild(style);
            }
            const root = document.createElement("div");
            root.id = "ssim-panel";
            root.className = prefs.collapsed ? "collapsed" : "";
            root.innerHTML = `
<div class="ssim-head"><span class="ssim-dot"></span><b>Stripe reader simulator</b><button class="ssim-toggle" title="Collapse">▾</button></div>
<div class="ssim-body">
  <div class="ssim-screen"></div>
  <div class="ssim-controls">
    <label title="Card presented when the customer taps">Card <select class="ssim-card"></select></label>
    <label><input type="checkbox" class="ssim-auto"> Auto-present card (no interaction)</label>
    <div class="ssim-row">
      <button class="ssim-link ssim-unplug" title="Trigger onUnexpectedReaderDisconnect">Unplug reader</button>
      <button class="ssim-link ssim-dash" title="Open the simulator dashboard">Dashboard</button>
    </div>
  </div>
</div>`;
            this.root = root;
            this.dot = root.querySelector(".ssim-dot");
            this.title = root.querySelector(".ssim-head b");
            this.screen = root.querySelector(".ssim-screen");
            this.cardSelect = root.querySelector(".ssim-card");
            this.autoBox = root.querySelector(".ssim-auto");
            this.autoBox.checked = prefs.autoPresent;
            this.autoBox.addEventListener("change", () => {
                prefs.autoPresent = this.autoBox.checked;
                savePrefs();
                if (prefs.autoPresent && this.waiter && this.waiter.kind === "card") {
                    this.waiter.resolve({ card: this.selectedCard() });
                }
            });
            this.cardSelect.addEventListener("change", () => {
                prefs.card = this.cardSelect.value;
                savePrefs();
            });
            root.querySelector(".ssim-toggle").addEventListener("click", () => {
                prefs.collapsed = !prefs.collapsed;
                root.classList.toggle("collapsed", prefs.collapsed);
                savePrefs();
            });
            root.querySelector(".ssim-unplug").addEventListener("click", () => {
                const connected = [...terminals].find((t) => t._reader);
                if (connected) {
                    connected._simulateUnplug();
                }
            });
            root.querySelector(".ssim-dash").addEventListener("click", () => window.open((BASE_URL || "") + "/", "_blank"));
            this.makeDraggable(root.querySelector(".ssim-head"));
            const mount = () => document.body.appendChild(root);
            document.body ? mount() : document.addEventListener("DOMContentLoaded", mount);
            this.idle(null);
        }

        makeDraggable(handle) {
            let start = null;
            handle.addEventListener("pointerdown", (ev) => {
                if (ev.target.closest("button")) {
                    return;
                }
                const rect = this.root.getBoundingClientRect();
                start = { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
                handle.setPointerCapture(ev.pointerId);
            });
            handle.addEventListener("pointermove", (ev) => {
                if (!start) {
                    return;
                }
                const x = Math.min(Math.max(0, ev.clientX - start.x), innerWidth - this.root.offsetWidth);
                const y = Math.min(Math.max(0, ev.clientY - start.y), innerHeight - 40);
                Object.assign(this.root.style, { left: x + "px", top: y + "px", right: "auto", bottom: "auto" });
            });
            handle.addEventListener("pointerup", () => (start = null));
        }

        async loadCards() {
            const res = await api("GET", "/sim/state");
            this.cards = res.data ? res.data.test_cards : [{ number: SIMULATED_DEFAULT_CARD, test_payment_method: "visa", outcome: "success" }];
            this.cardSelect.replaceChildren(
                ...this.cards.map((c) => {
                    const opt = document.createElement("option");
                    opt.value = c.number;
                    opt.textContent = `${c.test_payment_method} ••${c.number.slice(-4)}${c.outcome === "success" ? "" : " → " + c.outcome}`;
                    return opt;
                })
            );
            this.cardSelect.value = this.cards.some((c) => c.number === prefs.card) ? prefs.card : SIMULATED_DEFAULT_CARD;
            if (!res.data) {
                this.message("Simulator server unreachable", BASE_URL || location.origin, "ko");
            }
        }

        selectedCard() {
            return this.cardSelect.value || prefs.card || SIMULATED_DEFAULT_CARD;
        }

        setStatus(reader, busy) {
            this.dot.className = "ssim-dot" + (reader ? (busy ? " busy" : " on") : "");
            this.title.textContent = reader ? reader.label || reader.serial_number : "Stripe reader simulator";
            this.title.title = reader ? `${reader.serial_number} (${reader.device_type})` : "Not connected";
        }

        el(tag, cls, text) {
            const node = document.createElement(tag);
            if (cls) {
                node.className = cls;
            }
            if (text !== undefined) {
                node.textContent = text;
            }
            return node;
        }

        button(label, cls, onClick) {
            const btn = this.el("button", "ssim-btn " + (cls || ""), label);
            btn.addEventListener("click", onClick);
            return btn;
        }

        render(variant, ...children) {
            this.screen.className = "ssim-screen" + (variant ? " " + variant : "");
            this.screen.replaceChildren(...children.filter(Boolean));
        }

        idle(reader, cart) {
            if (cart) {
                const list = this.el("div", "ssim-cart");
                for (const item of cart.line_items || []) {
                    const row = this.el("div");
                    row.append(this.el("span", "", `${item.quantity} × ${item.description}`), this.el("span", "", formatAmount(item.amount * item.quantity, cart.currency)));
                    list.append(row);
                }
                if (cart.tax) {
                    const row = this.el("div");
                    row.append(this.el("span", "", "Tax"), this.el("span", "", formatAmount(cart.tax, cart.currency)));
                    list.append(row);
                }
                const total = this.el("div", "ssim-total");
                total.append(this.el("span", "", "Total"), this.el("span", "", formatAmount(cart.total, cart.currency)));
                list.append(total);
                return this.render("", list);
            }
            this.render("", this.el("div", "ssim-amount", reader ? "Welcome" : "Not connected"), this.el("div", "ssim-sub", reader ? "Ready" : "Call connectReader()"));
        }

        message(title, sub, variant) {
            this.render(variant, this.el("div", "ssim-amount", title), sub ? this.el("div", "ssim-sub", sub) : null);
        }

        /** Resolve with {card} when a card is presented, {cancel:true} when the customer cancels. */
        waitForCard({ amount, currency, label, allowCancel, auto }) {
            this.cancelWait();
            return new Promise((resolve) => {
                this.waiter = { kind: "card", resolve: (v) => ((this.waiter = null), resolve(v)) };
                if (auto || prefs.autoPresent) {
                    this.message(formatAmount(amount, currency), "Presenting card…");
                    setTimeout(() => this.waiter && this.waiter.resolve({ card: auto || this.selectedCard() }), prefs.latency);
                    return;
                }
                this.render(
                    "",
                    this.el("div", "ssim-sub", label),
                    this.el("div", "ssim-amount", formatAmount(amount, currency)),
                    this.el("div", "ssim-sub", "Tap, insert or swipe"),
                    this.btns(
                        this.button("Present card", "primary ssim-present", () => this.waiter && this.waiter.resolve({ card: this.selectedCard() })),
                        allowCancel && this.button("Cancel", "danger ssim-customer-cancel", () => this.waiter && this.waiter.resolve({ cancel: true }))
                    )
                );
            });
        }

        /** Resolve with the tip amount (minor units) chosen on the reader. */
        waitForTip({ amount, eligible, currency, auto }) {
            this.cancelWait();
            return new Promise((resolve) => {
                this.waiter = { kind: "tip", resolve: (v) => ((this.waiter = null), resolve(v)) };
                if (auto !== undefined) {
                    return this.waiter.resolve({ tip: auto });
                }
                const options = [10, 15, 20].map((pct) => {
                    const tip = Math.round((eligible * pct) / 100);
                    return this.button(`${pct}% · ${formatAmount(tip, currency)}`, "primary ssim-tip", () => this.waiter && this.waiter.resolve({ tip }));
                });
                const custom = this.el("input");
                custom.type = "number";
                custom.min = "0";
                custom.step = ZERO_DECIMAL.has(currency) ? "1" : "0.01";
                custom.placeholder = "Custom tip";
                this.render(
                    "",
                    this.el("div", "ssim-sub", "Add a tip?"),
                    this.el("div", "ssim-amount", formatAmount(amount, currency)),
                    this.btns(...options),
                    this.btns(
                        custom,
                        this.button("OK", "ssim-tip-custom", () => {
                            const value = parseFloat(custom.value) || 0;
                            this.waiter && this.waiter.resolve({ tip: Math.round(ZERO_DECIMAL.has(currency) ? value : value * 100) });
                        }),
                        this.button("No tip", "ssim-no-tip", () => this.waiter && this.waiter.resolve({ tip: 0 }))
                    )
                );
            });
        }

        btns(...children) {
            const box = this.el("div", "ssim-btns");
            box.append(...children.filter(Boolean));
            return box;
        }

        cancelWait() {
            if (this.waiter) {
                this.waiter.resolve({ cancel: true, byPos: true });
            }
        }
    }

    let panel = null;
    const getPanel = () => (panel = panel || new ReaderPanel());

    // ---------------------------------------------------------------------
    // Terminal
    // ---------------------------------------------------------------------

    const ConnectionStatus = { CONNECTING: "connecting", CONNECTED: "connected", NOT_CONNECTED: "not_connected" };
    const PaymentStatus = { NOT_READY: "not_ready", READY: "ready", WAITING_FOR_INPUT: "waiting_for_input", PROCESSING: "processing" };

    class Terminal {
        constructor(options = {}) {
            if (typeof options.onFetchConnectionToken !== "function") {
                throw new Error("StripeTerminal.create: onFetchConnectionToken must be a function.");
            }
            if (typeof options.onUnexpectedReaderDisconnect !== "function") {
                throw new Error("StripeTerminal.create: onUnexpectedReaderDisconnect must be a function.");
            }
            this._options = options;
            this._session = "sess_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
            this._token = null;
            this._reader = null;
            this._connectionStatus = ConnectionStatus.NOT_CONNECTED;
            this._paymentStatus = PaymentStatus.NOT_READY;
            this._simulatorConfiguration = {};
            this._pending = null; // {kind, stage: 'waiting'|'running'|'done', cancel}
            this._refund = null;
            this._panel = getPanel();
            terminals.add(this);
            addEventListener("pagehide", () => this._release());
        }

        // --- status ------------------------------------------------------

        getConnectionStatus() {
            return this._connectionStatus;
        }

        getPaymentStatus() {
            return this._paymentStatus;
        }

        getConnectedReader() {
            return this._reader || undefined;
        }

        _setConnectionStatus(status) {
            if (status !== this._connectionStatus) {
                this._connectionStatus = status;
                this._options.onConnectionStatusChange && this._options.onConnectionStatusChange({ status });
            }
        }

        _setPaymentStatus(status) {
            if (status !== this._paymentStatus) {
                this._paymentStatus = status;
                this._options.onPaymentStatusChange && this._options.onPaymentStatusChange({ status });
                this._panel.setStatus(this._reader, status === PaymentStatus.WAITING_FOR_INPUT || status === PaymentStatus.PROCESSING);
            }
        }

        _requireReader() {
            if (this._connectionStatus !== ConnectionStatus.CONNECTED) {
                return err("no_established_connection", "No reader is connected. Connect to a reader before trying again.");
            }
            return null;
        }

        _requireIdle() {
            return (
                this._requireReader() ||
                (this._pending && this._pending.stage !== "done"
                    ? err("command_already_in_progress", `Could not execute the command because a ${this._pending.kind} command is already in progress.`)
                    : null)
            );
        }

        get _isSimulatedReader() {
            return !!this._reader && this._reader.device_type.startsWith("simulated");
        }

        // --- credentials -------------------------------------------------

        async _ensureToken() {
            if (this._token) {
                return null;
            }
            let token;
            try {
                token = await this._options.onFetchConnectionToken();
            } catch (e) {
                return err("failed_fetch_connection_token", `onFetchConnectionToken failed: ${e && e.message ? e.message : e}`);
            }
            if (!token || typeof token !== "string") {
                return err("failed_fetch_connection_token", "onFetchConnectionToken must resolve to a connection token secret (string).");
            }
            this._token = token;
            return null;
        }

        async clearCachedCredentials() {
            this._token = null;
            return {};
        }

        // --- discovery / connection -------------------------------------

        async discoverReaders(options = {}) {
            const tokenError = await this._ensureToken();
            if (tokenError) {
                return tokenError;
            }
            await sleep(prefs.latency);
            const res = await api("POST", "/sim/discover", { simulated: !!options.simulated, location: options.location });
            return res.error ? res : { discoveredReaders: res.data.discoveredReaders };
        }

        async connectReader(reader, connectOptions = {}) {
            if (this._connectionStatus === ConnectionStatus.CONNECTED) {
                return err("already_connected", "Already connected to a reader. Disconnect before connecting to another one.");
            }
            if (!reader || !reader.id) {
                return err("reader_error", "connectReader expects a Reader object returned by discoverReaders().");
            }
            this._setConnectionStatus(ConnectionStatus.CONNECTING);
            const tokenError = await this._ensureToken();
            if (tokenError) {
                this._setConnectionStatus(ConnectionStatus.NOT_CONNECTED);
                return tokenError;
            }
            await sleep(prefs.latency);
            const res = await api("POST", `/sim/readers/${encodeURIComponent(reader.id)}/connect`, { session: this._session });
            if (res.error) {
                this._setConnectionStatus(ConnectionStatus.NOT_CONNECTED);
                return res;
            }
            this._reader = res.data;
            this._setConnectionStatus(ConnectionStatus.CONNECTED);
            this._setPaymentStatus(PaymentStatus.READY);
            this._panel.setStatus(this._reader, false);
            this._panel.idle(this._reader);
            return { reader: this._reader };
        }

        async disconnectReader() {
            const notConnected = this._requireReader();
            if (notConnected) {
                return notConnected;
            }
            this._abortPending("canceled", "The command was canceled because the reader disconnected.");
            await this._release();
            this._resetConnection();
            return {};
        }

        async _release() {
            if (this._reader) {
                await api("POST", `/sim/readers/${encodeURIComponent(this._reader.id)}/disconnect`, { session: this._session }, true);
            }
        }

        _resetConnection() {
            this._reader = null;
            this._pending = null;
            this._refund = null;
            this._setPaymentStatus(PaymentStatus.NOT_READY);
            this._setConnectionStatus(ConnectionStatus.NOT_CONNECTED);
            this._panel.setStatus(null);
            this._panel.idle(null);
        }

        async _simulateUnplug() {
            if (!this._reader) {
                return;
            }
            await this._release();
            this._unexpectedDisconnect();
        }

        _unexpectedDisconnect() {
            const error = { code: "reader_disconnected", message: "The reader disconnected unexpectedly." };
            this._abortPending(error.code, error.message);
            this._resetConnection();
            this._panel.message("Disconnected", "Reader unplugged", "ko");
            this._options.onUnexpectedReaderDisconnect({ error });
        }

        _abortPending(code, message) {
            if (this._pending && this._pending.stage !== "done") {
                this._pending.cancel(code, message);
            }
            this._panel.cancelWait();
        }

        // --- cancellable command helper ---------------------------------

        /**
         * Run `body(pending)` as a cancellable command of type `kind`.
         * The command resolves with an {error} response as soon as it is cancelled.
         */
        async _command(kind, body) {
            let cancel;
            const cancelled = new Promise((resolve) => (cancel = (code, message) => resolve(err(code, message))));
            const pending = { kind, stage: "waiting", cancel: null };
            pending.cancel = (code = "canceled", message = "The command was canceled.") => {
                pending.stage = "done";
                cancel(code, message);
            };
            this._pending = pending;
            try {
                return await Promise.race([body(pending), cancelled]);
            } finally {
                pending.stage = "done";
                if (this._pending === pending) {
                    this._pending = null;
                }
                if (this._reader) {
                    this._setPaymentStatus(PaymentStatus.READY);
                }
            }
        }

        _cancelCommand(kind, noActiveCode) {
            const pending = this._pending;
            if (!pending || pending.kind !== kind) {
                return err(noActiveCode, `There is no active ${kind} attempt to cancel.`);
            }
            if (pending.stage === "running") {
                return err("cancelable_already_completed", "The command has already completed and cannot be canceled.");
            }
            if (pending.stage === "done") {
                return err("cancelable_already_canceled", "The command has already been canceled.");
            }
            pending.cancel("canceled", "The command was canceled by the POS.");
            this._panel.cancelWait();
            this._panel.message("Canceled", "", "ko");
            setTimeout(() => this._reader && !this._pending && this._panel.idle(this._reader), 1500);
            return {};
        }

        // --- reader display ---------------------------------------------

        async setReaderDisplay(displayInfo) {
            const busy = this._requireIdle();
            if (busy) {
                return busy;
            }
            if (!displayInfo || displayInfo.type !== "cart" || !displayInfo.cart) {
                return err("invalid_parameter", "setReaderDisplay only supports { type: 'cart', cart: {...} }.");
            }
            this._panel.idle(this._reader, displayInfo.cart);
            return {};
        }

        async clearReaderDisplay() {
            const busy = this._requireIdle();
            if (busy) {
                return busy;
            }
            this._panel.idle(this._reader);
            return {};
        }

        // --- payments ---------------------------------------------------

        async collectPaymentMethod(request, options = {}) {
            const busy = this._requireIdle();
            if (busy) {
                return busy;
            }
            const clientSecret = typeof request === "string" ? request : request && request.client_secret;
            const piId = clientSecret && clientSecret.split("_secret_")[0];
            if (!piId || piId === clientSecret) {
                return err("invalid_parameter", "collectPaymentMethod expects a PaymentIntent client secret.");
            }
            // The docs show both nestings; accept options.config_override and top-level keys.
            const config = { ...options, ...(options.config_override || {}) };
            const allowCancel = !!(config.enable_customer_cancellation || (this._options.readerBehavior || {}).allowCustomerCancel);

            return this._command("collectPaymentMethod", async (pending) => {
                const fetched = await api("GET", `/v1/payment_intents/${encodeURIComponent(piId)}`);
                if (fetched.error) {
                    return fetched;
                }
                let pi = fetched.data;
                if (pi.client_secret !== clientSecret) {
                    return err("invalid_parameter", "The client_secret does not match the PaymentIntent.");
                }
                if (pending.stage === "done") {
                    return err("canceled", "The command was canceled.");
                }
                this._setPaymentStatus(PaymentStatus.WAITING_FOR_INPUT);

                const sim = this._simulatorConfiguration;
                const automatic = prefs.autoPresent || (this._isSimulatedReader && sim.tipAmount != null);
                let tip = 0;
                const eligible = config.tipping && config.tipping.eligible_amount !== undefined ? config.tipping.eligible_amount : pi.amount;
                if (!config.skip_tipping && eligible > 0) {
                    const chosen = await this._panel.waitForTip({
                        amount: pi.amount,
                        eligible,
                        currency: pi.currency,
                        auto: automatic ? Number(sim.tipAmount) || 0 : undefined,
                    });
                    if (chosen.cancel) {
                        return err("canceled", "The command was canceled.");
                    }
                    tip = chosen.tip;
                }
                const presented = await this._panel.waitForCard({
                    amount: pi.amount + tip,
                    currency: pi.currency,
                    label: tip ? `incl. ${formatAmount(tip, pi.currency)} tip` : this._reader.label,
                    allowCancel,
                    auto: this._isSimulatedReader ? this._simulatedCard() : null,
                });
                if (presented.cancel) {
                    return err("canceled", presented.byPos ? "The command was canceled by the POS." : "The customer canceled the payment on the reader.");
                }
                pending.stage = "running";
                this._panel.message(formatAmount(pi.amount + tip, pi.currency), "Card read", "");
                const collected = await api("POST", `/sim/payment_intents/${encodeURIComponent(piId)}/collect`, {
                    client_secret: clientSecret,
                    card: presented.card,
                    tip,
                    options, // as passed by the POS (e.g. config_override.skip_tipping); logged only
                });
                if (collected.error) {
                    this._panel.message("Error", collected.error.message, "ko");
                    return collected;
                }
                pi = collected.data;
                return { paymentIntent: pi };
            });
        }

        _simulatedCard() {
            const sim = this._simulatorConfiguration;
            if (sim.testCardNumber) {
                return String(sim.testCardNumber);
            }
            if (sim.testPaymentMethod) {
                const match = this._panel.cards.find((c) => c.test_payment_method === sim.testPaymentMethod);
                return match ? match.number : sim.testPaymentMethod;
            }
            if (sim.paymentMethodType === "interac_present") {
                return INTERAC_DEFAULT_CARD;
            }
            return null; // wait for "Present card" (or Auto-present)
        }

        async cancelCollectPaymentMethod() {
            return this._cancelCommand("collectPaymentMethod", "no_active_collect_payment_method_attempt");
        }

        async processPayment(paymentIntent, options = {}) {
            const busy = this._requireIdle();
            if (busy) {
                return busy;
            }
            if (!paymentIntent || !paymentIntent.id) {
                return err("invalid_parameter", "processPayment expects the PaymentIntent returned by collectPaymentMethod.");
            }
            return this._command("processPayment", async (pending) => {
                this._setPaymentStatus(PaymentStatus.PROCESSING);
                this._panel.message(formatAmount(paymentIntent.amount, paymentIntent.currency), "Processing…");
                await sleep(prefs.latency * 2);
                if (pending.stage === "done") {
                    return err("canceled", "The command was canceled.");
                }
                pending.stage = "running";
                const res = await api("POST", `/sim/payment_intents/${encodeURIComponent(paymentIntent.id)}/confirm`, {});
                this._simulatorConfiguration = {};
                if (res.error) {
                    this._panel.message("Declined", res.error.decline_code || res.error.message, "ko");
                } else {
                    this._panel.message("Approved", formatAmount(res.data.amount, res.data.currency), "ok");
                }
                setTimeout(() => this._reader && !this._pending && this._panel.idle(this._reader), 2500);
                return res.error ? res : { paymentIntent: res.data };
            });
        }

        async cancelProcessPayment() {
            return this._cancelCommand("processPayment", "no_active_process_payment_attempt");
        }

        // --- refunds ----------------------------------------------------

        async collectRefundPaymentMethod(chargeId, amount, currency, options = {}, config = {}) {
            const busy = this._requireIdle();
            if (busy) {
                return busy;
            }
            if (!chargeId || !(amount > 0) || !currency) {
                return err("invalid_parameter", "collectRefundPaymentMethod(charge_id, amount, currency) requires all three parameters.");
            }
            return this._command("collectRefundPaymentMethod", async () => {
                this._setPaymentStatus(PaymentStatus.WAITING_FOR_INPUT);
                const presented = await this._panel.waitForCard({
                    amount,
                    currency,
                    label: "Refund",
                    allowCancel: !!config.enable_customer_cancellation,
                    auto: this._isSimulatedReader ? this._simulatedCard() : null,
                });
                if (presented.cancel) {
                    return err("canceled", "The refund was canceled.");
                }
                this._refund = { chargeId, amount, currency, options };
                this._panel.message("Card read", "Call processRefund()");
                return {};
            });
        }

        async cancelCollectRefundPaymentMethod() {
            return this._cancelCommand("collectRefundPaymentMethod", "no_active_collect_refund_payment_method_attempt");
        }

        async processRefund() {
            const busy = this._requireIdle();
            if (busy) {
                return busy;
            }
            if (!this._refund) {
                return err("invalid_parameter", "processRefund must be called after a successful collectRefundPaymentMethod.");
            }
            const refund = this._refund;
            return this._command("processRefund", async (pending) => {
                this._setPaymentStatus(PaymentStatus.PROCESSING);
                await sleep(prefs.latency);
                if (pending.stage === "done") {
                    return err("canceled", "The refund was canceled.");
                }
                pending.stage = "running";
                const res = await api("POST", `/sim/charges/${encodeURIComponent(refund.chargeId)}/refund`, { amount: refund.amount });
                this._refund = null;
                this._panel.message(res.error ? "Refund failed" : "Refunded", res.error ? res.error.message : formatAmount(refund.amount, refund.currency), res.error ? "ko" : "ok");
                setTimeout(() => this._reader && !this._pending && this._panel.idle(this._reader), 2500);
                return res.error ? res : { refund: res.data };
            });
        }

        async cancelProcessRefund() {
            return this._cancelCommand("processRefund", "no_active_process_refund_attempt");
        }

        // --- collect inputs ---------------------------------------------

        async collectInputs(params = {}) {
            const busy = this._requireIdle();
            if (busy) {
                return busy;
            }
            const result = this._simulatorConfiguration.collectInputsResult || { resultType: "succeeded", skipBehavior: "none" };
            return this._command("collectInputs", async () => {
                this._setPaymentStatus(PaymentStatus.WAITING_FOR_INPUT);
                this._panel.message("Collecting inputs", `${(params.inputs || []).length} input(s)`);
                await sleep(prefs.latency * 2);
                if (result.resultType === "timeout") {
                    return err("collect_inputs_timed_out", "The customer did not complete the form in time.");
                }
                const skipped = result.skipBehavior === "all";
                return (params.inputs || []).map((input) => ({
                    formType: input.formType,
                    skipped: skipped && !input.required,
                    customFields: input.customFields || {},
                    ...(skipped && !input.required ? {} : this._fakeInput(input)),
                }));
            });
        }

        _fakeInput(input) {
            switch (input.formType) {
                case "email": return { email: "customer@example.com" };
                case "phone": return { phone: "+15555550100" };
                case "numeric": return { numericString: "1234" };
                case "text": return { text: "Simulated text" };
                case "selection": return { selection: ((input.selectionButtons || [])[0] || {}).text || null };
                case "signature": return { signatureSvg: "<svg xmlns='http://www.w3.org/2000/svg'/>" };
                default: return {};
            }
        }

        async cancelCollectInputs() {
            return this._cancelCommand("collectInputs", "no_active_collect_inputs_attempt");
        }

        // --- unsupported by the simulator --------------------------------

        async collectSetupIntentPaymentMethod() {
            return err("unsupported_operation", "SetupIntents are not supported by the Stripe simulator.");
        }

        async cancelCollectSetupIntentPaymentMethod() {
            return err("no_active_collect_setup_intent_payment_method_attempt", "No SetupIntent collection in progress.");
        }

        async confirmSetupIntent() {
            return err("unsupported_operation", "SetupIntents are not supported by the Stripe simulator.");
        }

        async cancelConfirmSetupIntent() {
            return err("no_active_confirm_setup_intent_attempt", "No SetupIntent confirmation in progress.");
        }

        async readReusableCard() {
            return err("unsupported_operation", "readReusableCard is not supported by the Stripe simulator.");
        }

        async cancelReadReusableCard() {
            return err("no_active_read_reusable_card_attempt", "No readReusableCard in progress.");
        }

        async print() {
            const notConnected = this._requireReader();
            if (notConnected) {
                return notConnected;
            }
            return /v660p/.test(this._reader.device_type) ? {} : err("printer_absent", "This reader has no printer.");
        }

        // --- simulator configuration ------------------------------------

        setSimulatorConfiguration(configuration) {
            if (this._isSimulatedReader) {
                this._simulatorConfiguration = { ...(configuration || {}) };
            }
        }

        getSimulatorConfiguration() {
            return { ...this._simulatorConfiguration };
        }

        overrideBaseURL(url) {
            BASE_URL = String(url || "").replace(/\/$/, "");
        }
    }

    window.StripeTerminal = {
        create: (options) => new Terminal(options),
        ConnectionStatus,
        PaymentStatus,
    };

    // Helpers for automated tests (tours, Hoot, Playwright…).
    window.StripeTerminalSimulator = {
        get baseUrl() {
            return BASE_URL;
        },
        setAutoPresent(value, card) {
            prefs.autoPresent = !!value;
            if (card) {
                prefs.card = String(card);
            }
            const p = getPanel();
            p.autoBox.checked = prefs.autoPresent;
            if (card) {
                p.cardSelect.value = prefs.card;
            }
            savePrefs();
        },
        setLatency(ms) {
            prefs.latency = Math.max(0, Number(ms) || 0);
            savePrefs();
        },
        presentCard(card) {
            const p = getPanel();
            if (p.waiter && p.waiter.kind === "card") {
                p.waiter.resolve({ card: String(card || p.selectedCard()) });
                return true;
            }
            return false;
        },
        chooseTip(amount) {
            const p = getPanel();
            if (p.waiter && p.waiter.kind === "tip") {
                p.waiter.resolve({ tip: Math.round(Number(amount) || 0) });
                return true;
            }
            return false;
        },
        customerCancel() {
            const p = getPanel();
            if (p.waiter) {
                p.waiter.resolve({ cancel: true });
                return true;
            }
            return false;
        },
    };
})();
