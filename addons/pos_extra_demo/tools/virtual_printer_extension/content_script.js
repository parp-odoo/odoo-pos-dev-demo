let openingPrinter = false;

document.addEventListener("click", async (event) => {
    if (
        !event.isTrusted || event.defaultPrevented || event.button !== 0 ||
        event.ctrlKey || event.metaKey || event.shiftKey || event.altKey
    ) {
        return;
    }
    const link = event.target.closest("a[data-pos-virtual-printer]");
    if (link?.href !== "https://pos.stva.ovh/printer/test-p") {
        return;
    }
    event.preventDefault();
    if (openingPrinter) {
        return;
    }
    openingPrinter = true;
    try {
        const response = await chrome.runtime.sendMessage({
            type: "pos-extra-demo:open-virtual-printer",
        });
        if (!response?.ok) {
            throw new Error(response?.error || "The printer extension did not respond.");
        }
    } catch (error) {
        window.alert(`Could not open the virtual printer in split view. ${error.message}`);
    } finally {
        openingPrinter = false;
    }
}, true);
