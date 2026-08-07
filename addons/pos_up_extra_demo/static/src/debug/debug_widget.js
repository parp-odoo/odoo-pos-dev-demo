import { DebugWidget } from "@point_of_sale/app/utils/debug/debug_widget";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(DebugWidget.prototype, {
    placeUrbanPiperQuickTestOrder() {
        const urbanpiperStore = this.pos.config.urbanpiper_store_id;
        const providerIds = urbanpiperStore.delivery_provider_ids.map((provider) => provider.id);;
        const products = this.pos.productsToDisplay;
        this.pos.data.call(
            "pos.config",
            "action_quick_urbanpiper_test_order",
            [
                urbanpiperStore.id,
                products[Math.floor(Math.random() * products.length)].id,
                providerIds[Math.floor(Math.random() * providerIds.length)],
            ]
        );
        if (this.state.isOpen) {
            this.toggleWidget?.();
        }
    },
});
