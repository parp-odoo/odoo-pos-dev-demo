import { DebugWidget } from "@point_of_sale/app/utils/debug/debug_widget";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(DebugWidget.prototype, {
    placeUrbanPiperTestOrder() {
        super.placeUrbanPiperTestOrder?.();
        if (this.state.isOpen) {
            this.toggleWidget?.();
        }
    },
    placeUrbanPiperQuickTestOrder() {
        const providrs = this.pos.deliveryProviders || this.pos.config.urbanpiper_delivery_provider_ids;
        const products = this.pos.productsToDisplay;
        this.pos.data.call(
            "pos.config",
            "action_quick_urbanpiper_test_order",
            [
                this.pos.store?.id || this.pos.config.id,
                products[Math.floor(Math.random() * products.length)].id,
                providrs[Math.floor(Math.random() * providrs.length)].id,
            ]
        );
        if (this.state.isOpen) {
            this.toggleWidget?.();
        }
    },
});
