import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { cookie } from "@web/core/browser/cookie";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        if (!cookie.get("pos_color_scheme")) {
            cookie.set("pos_color_scheme", "dark");
        }
    },
});
