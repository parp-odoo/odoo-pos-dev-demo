/* global StripeTerminal */

import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { PaymentStripe } from "@pos_stripe/app/payment_stripe";

patch(PaymentStripe.prototype, {
    async createStripeTerminal() {
        try {
            await loadJS("/pos_stripe_simulator/terminal/v1/");
            this.terminal = StripeTerminal.create({
                onFetchConnectionToken: this.stripeFetchConnectionToken.bind(this),
                onUnexpectedReaderDisconnect: this.stripeUnexpectedDisconnect.bind(this),
            });
            return true;
        } catch (error) {
            this._showError(String(error), _t("Stripe simulator unavailable"));
            this.terminal = false;
            return false;
        }
    },
});
