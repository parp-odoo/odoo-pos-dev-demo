import { reactive } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { PrepDisplay } from "@pos_enterprise/app/components/preparation_display/preparation_display";


patch(PrepDisplay.prototype, {
    setup() {
        super.setup();
        window.posmodel = reactive(this.prepDisplay);
    }
});
