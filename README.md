
# MedRush Working Website

Included:
- Responsive storefront
- Medicine search and categories
- Cart and quantity controls
- Checkout and order summary
- PAN-India address and pincode collection
- Prescription upload for prescription medicines
- COD and UPI-on-confirmation
- Order tracking
- Admin dashboard and status updates
- SQLite database

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open:
- Website: http://127.0.0.1:5000
- Admin: http://127.0.0.1:5000/admin

## Before a live commercial launch

Add admin login, OTP authentication, private cloud prescription storage, PostgreSQL, Razorpay, WhatsApp/SMS notifications, courier integration, backups, HTTPS, legal pages, consent records, pharmacy onboarding and compliance review.
