const PRINTER_URL = "https://pos.stva.ovh/printer/test-p";
const APP_PATHS = [
    /^\/pos\/(?:ui|web)(\/|$)/,
    /^\/pos-self\/\d+(\/|$)/,
    /^\/pos_preparation_display\/web(\/|$)/,
];

async function openVirtualPrinter(posTabId) {
    if (typeof chrome.tabs.createSplit !== "function") {
        throw new Error("Automatic split view requires Chrome 155 or later.");
    }
    const posTab = await chrome.tabs.get(posTabId);
    if (posTab.splitViewId >= 0) {
        const tabs = await chrome.tabs.query({ windowId: posTab.windowId });
        const printer = tabs.find((tab) =>
            tab.id !== posTab.id && tab.splitViewId === posTab.splitViewId &&
            (tab.url === PRINTER_URL || tab.pendingUrl === PRINTER_URL)
        );
        if (!printer) {
            throw new Error("Separate the POS tab from its current split view, then try again.");
        }
        await chrome.tabs.update(posTab.id, { active: true });
        return;
    }

    const printer = await chrome.tabs.create({
        url: PRINTER_URL,
        windowId: posTab.windowId,
        index: posTab.index + 1,
        openerTabId: posTab.id,
        pinned: posTab.pinned,
        active: false,
    });
    try {
        if (posTab.groupId >= 0) {
            await chrome.tabs.group({ groupId: posTab.groupId, tabIds: [printer.id] });
            const currentPosTab = await chrome.tabs.get(posTab.id);
            await chrome.tabs.move(printer.id, { index: currentPosTab.index + 1 });
        }
        await chrome.tabs.createSplit([posTab.id, printer.id]);
    } catch (error) {
        // Remove only the tab we just created if pairing fails.
        await chrome.tabs.remove(printer.id).catch(() => {});
        throw error;
    }
    await chrome.tabs.update(posTab.id, { active: true });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (
        message?.type !== "pos-extra-demo:open-virtual-printer" ||
        sender.id !== chrome.runtime.id || sender.frameId !== 0 || !sender.tab
    ) {
        return;
    }
    const url = new URL(sender.url);
    if (
        !["http:", "https:"].includes(url.protocol) ||
        !APP_PATHS.some((pattern) => pattern.test(url.pathname))
    ) {
        return;
    }
    openVirtualPrinter(sender.tab.id).then(
        () => sendResponse({ ok: true }),
        (error) => sendResponse({ ok: false, error: error.message })
    );
    return true;
});
