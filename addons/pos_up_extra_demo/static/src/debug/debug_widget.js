import { DebugWidget } from "@point_of_sale/app/debug/debug_widget";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(DebugWidget.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    showUrbanPiperTestOrderBtn() {
        return Boolean(this.pos.config.urbanpiper_delivery_provider_ids.length);
    },
    placeUrbanPiperQuickTestOrder() {
        const providrs = this.pos.config.urbanpiper_delivery_provider_ids;
        const products = this.pos.models["product.product"].getAll();;
        this.pos.data.call(
            "pos.config",
            "action_quick_urbanpiper_test_order",
            [
                this.pos.store?.id || this.pos.config.id,
                products[Math.floor(Math.random() * products.length)].id,
                providrs[Math.floor(Math.random() * providrs.length)].id,
            ]
        );
        this.toggleWidget();
    },
});
