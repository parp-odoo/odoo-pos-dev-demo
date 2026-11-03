# Odoo POS Virtual Printer

This extension makes the **Virtual Printer** link in the POS, self-order and
preparation display debug menus open `https://pos.stva.ovh/printer/test-p`
beside the current app in Chrome's native split view. Clicking it again while
that pair is open keeps the existing pair. The app keeps the active view.

## Requirements

Chrome **155 or later** is required for the extension's
[`chrome.tabs.createSplit` API](https://developer.chrome.com/docs/extensions/reference/api/tabs#method-createSplit).
Earlier Chrome versions may support manual split view, but do not expose this
extension API. The extension does not use an iframe or resize browser windows.

## Install

1. Upgrade `pos_extra_demo` and `pos_restaurant_extra_demo` in the demo database.
2. Open `chrome://extensions` in Chrome and enable **Developer mode**.
3. Choose **Load unpacked** and select this `virtual_printer_extension` folder.
4. Reload the app tab, open its debug menu, and click **Virtual Printer**.

Self-order (mobile and kiosk) and preparation display show a red debug button
in the bottom-right corner when developer mode is enabled. Add `debug=1` to
the page's query parameters, retaining any existing access token, display ID
and other parameters. Self-order requires `pos_restaurant_extra_demo`;
preparation display also requires `pos_restaurant_extra_demo`. Reload the extension after
updating it to enable these additional pages.

If POS opens native split view but self-order or preparation display opens a
regular tab, Chrome is still using the earlier POS-only content script
registration. Click **Reload** on **Odoo POS Virtual Printer** in
`chrome://extensions`, then reload both app pages. The shared debug menu
prevents an ordinary left-click from opening a separate tab when the extension
has not intercepted it, and displays these reload instructions instead.

The default site access covers POS, self-order and preparation display pages
on `localhost` and `127.0.0.1`, on any port. For another Odoo host, add its app URL patterns to
`content_scripts[0].matches` in `manifest.json`, then reload the extension and
the app. For example, add `https://your-odoo.example/pos/ui*`,
`https://your-odoo.example/pos-self/*` and
`https://your-odoo.example/pos_preparation_display/web*`.

The printer host permission lets the extension identify an already paired
printer tab. No access to all browser tabs' URLs is requested. Requests can
only open the fixed demo printer URL, and are triggered by a real click on
the POS printer link. An existing split with a different page is left intact;
separate it using Chrome's split-view controls before opening the printer.

Without the extension, the POS link opens the printer in a regular new tab.
Right-click and choose **Open link in split view** to use native split view
manually. Modifier clicks retain the browser's standard link behavior.
