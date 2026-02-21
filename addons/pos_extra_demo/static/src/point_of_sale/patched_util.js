import * as utils from "@point_of_sale/app/models/utils/order_change";
import { patch } from "@web/core/utils/patch";

patch(utils, {
    getOrderChanges(order, orderPreparationCategories, cancelled = false) {
        // console.log(">>>> Patched Call");
        const res = super.getOrderChanges(order, orderPreparationCategories, cancelled);
        // console.log("res : ", res);
        return res;
    },
});
