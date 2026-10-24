# Odoo POS Extra Demo Data

Developer demo addons for Point of Sale. Use the repository branch matching
Odoo: `18.0`, `19.0`, `saas-19.1` through `saas-19.4`, `20.0`, or `master`.

## Setup

1. Install `requirements.txt` in the Python environment running Odoo.
2. Copy `.env.example` to `.env` and supply the credentials for the integrations you use.
3. Add this repository's `addons` directory to Odoo's addons path.
4. Install the relevant demo addons with demo data enabled. The addons also
   auto-install when their dependencies are installed.

Demo XML is loaded only in demo databases. Existing XML ids are preserved.
Demo loaders reuse localized POS configurations and preparation displays.

## Addons

| Addon | Demo setup |
| --- | --- |
| `pos_extra_demo` | Receipt printers and demo online payments; fast payment where supported. |
| `pos_restaurant_extra_demo` | Restaurant/bar preparation printers, mobile self-ordering, kiosk and preparation display links. |
| `pos_l10n_in_extra_demo` | Indian furniture shop, restaurant and kiosk, preparation display, Razorpay and Pine Labs terminals. |
| `pos_up_extra_demo` | US UrbanPiper stores/providers, optional webhook URL and a quick-order debug button. |
| `pos_up_in_extra_demo` | UrbanPiper credentials/providers for the Indian restaurant. |


UrbanPiper setup is skipped when the store identifier or credentials are missing.
An absent `NGROK_URL` leaves the existing base URL unchanged. Quick demo orders
require an open POS session and a configured product and delivery provider.

These integrations are for development demo databases.
