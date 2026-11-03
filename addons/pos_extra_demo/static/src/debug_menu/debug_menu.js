import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class DebugMenu extends Component {
    static template = "pos_extra_demo.DebugMenu";
    static props = {};

    setup() {
        this.isDebug = Boolean(this.env.debug);
        this.notification = useService("notification");
        this.state = useState({ isOpen: false });
    }

    toggleMenu() {
        this.state.isOpen = !this.state.isOpen;
    }

    openVirtualPrinter(event) {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
            return;
        }
        // The extension handles the click during capture, before Owl's handler.
        const handledByExtension = event.defaultPrevented;
        event.preventDefault();
        if (!handledByExtension) {
            this.notification.add(
                _t("Reload the Odoo POS Virtual Printer extension in Chrome, then reload this page to enable split view."),
                { type: "warning", sticky: true }
            );
            return;
        }
        this.state.isOpen = false;
    }
}

registry.category("main_components").add("pos_extra_demo.DebugMenu", {
    Component: DebugMenu,
});
