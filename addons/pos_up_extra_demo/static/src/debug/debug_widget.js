import { DebugWidget } from "@point_of_sale/app/utils/debug/debug_widget";
import { patch } from "@web/core/utils/patch";

patch(DebugWidget.prototype, {
    async placeUrbanPiperQuickTestOrder() {
        const target = this.pos.config;
        const providers = this.pos.config.urbanpiper_delivery_provider_ids ?? [];
        const products = this.pos.productsToDisplay.filter((product) => product.available_in_pos);
        if (!target || !providers.length || !products.length) {
            return;
        }
        const product = products[Math.floor(Math.random() * products.length)];
        const provider = providers[Math.floor(Math.random() * providers.length)];
        await this.pos.data.call("pos.config", "action_quick_urbanpiper_test_order", [
            target.id,
            product.id,
            provider.id,
        ]);
        this.toggleWidget?.();
    },
});
