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
| `pos_hr_extra_demo` | Employee login on the main company's demo configurations, with employees named after each supported role. |
| `l10n_de_pos_cert_demo` | German furniture shop and restaurant, Fiskaly registration via local IAP, preparation display and printers. |

UrbanPiper setup is skipped when the store identifier or credentials are missing.
An absent `NGROK_URL` leaves the existing base URL unchanged. Quick demo orders
require an open POS session and a configured product and delivery provider.

## Employee login

Mitchell Admin (`hr.employee_admin`) keeps administrator access through the existing
Odoo user. Additional employees have no backend user and receive their role from
the POS configuration. Each role is assigned to a separate employee. Odoo also
includes employees linked to existing POS manager users automatically.

| Employee | PIN | Barcode |
| --- | --- | --- |
| Supervised | `4444` | `POSSUPERVISED` |
| Restrictive | `3333` | `POSRESTRICTIVE` |
| Cashier | `1111` | `POSCASHIER` |
| Manager | `2222` | `POSMANAGER` |

18.0 supports Cashier and Manager; 19.0 through saas-19.4 also support Minimal.
20.0 and master support Supervised, Restrictive, Cashier and Manager.

These credentials and integrations are for development demo databases.
