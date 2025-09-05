# Odoo POS Extra Demo Data
This repository provides extra demo data for Odoo Point of Sale modules.<br/>
The goal is to save developers valuable time during testing by avoiding repetitive configuration.<br/>
(Because let’s be honest — testing is the fun part! 😄)

## 🚀 Setup Instructions
1. Clone this repository:

    ```bash
    git clone https://github.com/parp-odoo/odoo-pos-extra-demo-dev.git
    ```

2. Install requirements:

    ```bash
    pip install -r requirements.txt
    ```

3. Add your credentials to the .`env` file (see `.env.example` for reference).

4. Add this directory to your Odoo addons path when running the server.
That’s it — you’re good to go!

## 📦 Module Information

### Point of Sale Exta Demo
- Creates demo printers and links them to all POS configurations for receipt printing.
- Creates a demo online payment method and adds it to all POS configurations.

### Restaurant Exta Demo
- Adds demo printers to configurations (restaurant, bar, and kiosk) as both receipt and preparation printers.
- Enables Presets in kiosk
- Enables **QR + Ordering** self-ordering mode in restaurant POS.
- Adds kiosk in Kitchen Display.

### POS India localisation Exta Demo
- Creates IN Furniture Shop, IN Restaurant (with mobile self-order), and IN Kiosk configs under the Indian company.
- add RazorPay and PineLab payment methods to those config as well.
- create prep display for resto and kiosk

### POS Urban Piper Exta Demo
- Enables UrbanPiper settings for Furniture Shop and Restaurant (UK/US).
- Configures ngrok URL in system parameters and disables UrbanPiper production mode.
- Populates credentials for UrbanPiper settings.

### POS Urban IN Piper Exta Demo
- Enables UrbanPiper settings for IN Furniture Shop.
- Configures ngrok URL in system parameters and disables UrbanPiper production mode.
- Populates credentials for UrbanPiper settings for IN company.


## ⚠️ Disclaimer
This repository is provided as-is.<br/>
If you encounter issues, don’t blame me — just ping me instead. 😉
