# FreshCart

FreshCart is an Indian online grocery application with INR pricing, user accounts, delivery profiles, cart checkout, UPI demo payments, and order tracking.

## Current Tech Stack

- Python 3.12
- Flask 3.1
- SQLite
- Jinja templates
- HTML, CSS, and vanilla JavaScript
- `qrcode` and Pillow for payment QR images
- pytest for testing
- Docker and Gunicorn for containerized runtime

## Workflow

1. The customer browses Indian grocery products and filters or searches the catalog.
2. Products are added to the cart and stock limits are checked.
3. The customer signs in or creates an account.
4. The saved name and delivery address are confirmed during checkout.
5. A UPI-style QR code is generated for the demo payment.
6. Payment is confirmed through the simulated payment flow.
7. The order is placed and appears in the Track orders view.

## Completed Features

- Indian grocery catalog with INR prices
- Product categories, search, stock labels, and cart quantity controls
- Signup, login, logout, and password hashing
- Profile details, saved address, and settings
- Delivery address confirmation
- Real server-generated demo UPI QR code
- Payment cancellation and separate payment confirmation dialog
- Order creation with stock reservation
- Dedicated navbar Track orders button
- Order history and order status
- `/health` endpoint
- pytest backend coverage
- Dockerfile and Gunicorn configuration

## Possible Additions

- Real payment gateway integration such as Razorpay or Stripe
- Product images and product detail pages
- Wishlist and repeat-order support
- Coupons, discounts, and loyalty points
- Delivery slot selection and live delivery updates
- Admin dashboard for products, stock, and orders
- PostgreSQL for production persistence
- Email or SMS order notifications
- Google Cloud deployment and monitoring

## Run Locally

```powershell
pip install -r requirements.txt
python app.py
```

Open `http://localhost:8080` and run tests with `python -m pytest -q`.
