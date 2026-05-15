import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { cookie } from "@web/core/browser/cookie";
import { browser } from "@web/core/browser/browser";

patch(Navbar.prototype, {
    setup() {
        super.setup();
        const posColorScheme = cookie.get("pos_color_scheme")
        if (!posColorScheme) {
            cookie.set("pos_color_scheme", "dark");
            // location.reload();
        }
    },
});
