import { DebugWidget } from "@point_of_sale/app/utils/debug/debug_widget";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(DebugWidget.prototype, {
    placeUrbanPiperTestOrder() {
        super.placeUrbanPiperTestOrder?.();
        this.toggleWidget?.();
    },
    placeUrbanPiperQuickTestOrder() {
        this.pos.data.call(
            "pos.config",
            "action_quick_urbanpiper_test_order",
            [
                this.pos.store?.id || this.pos.config.id,
                this.pos.productsToDisplay[0].id,
                this.pos.deliveryProviders?.[0].id || this.pos.config.urbanpiper_delivery_provider_ids?.[0].id,
            ]
        );
        this.toggleWidget?.()
    },
});
