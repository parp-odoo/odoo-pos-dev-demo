import { DebugWidget } from "@point_of_sale/app/debug/debug_widget";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";

patch(DebugWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },
    showUrbanPiperTestOrderBtn() {
        return Boolean(this.pos.config.urbanpiper_delivery_provider_ids.length);
    },
    async placeUrbanPiperQuickTestOrder() {
        const target = this.pos.config;
        const providers = this.pos.config.urbanpiper_delivery_provider_ids ?? [];
        const products = this.pos.models["product.product"].getAll().filter(
            (product) => product.available_in_pos && product.product_tmpl_id
        );
        if (!target || !providers.length || !products.length) {
            return;
        }
        const product = products[Math.floor(Math.random() * products.length)];
        const provider = providers[Math.floor(Math.random() * providers.length)];
        await this.pos.data.call("pos.config", "action_quick_urbanpiper_test_order", [
            target.id,
            product.product_tmpl_id.id,
            provider.id,
        ]);
        this.toggleWidget?.();
    },
});
