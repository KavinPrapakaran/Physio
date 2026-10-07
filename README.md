# REE Forma Clinic Management Software

A secure, professional physiotherapy clinic management system built with Python and Flask for local development in VS Code.

## Features
- Secure session login with role-based permissions
- Patient registration and profile management
- Appointment scheduling and prevention of double booking
- Physiotherapy assessments and PDF export
- Treatment record management
- Package tracking with session consumption
- Billing and payment tracking
- Notification and WhatsApp-ready integration
- Reports and audit logs
- SQLite by default, with MySQL-compatible environment override

## Quick start
1. Create a virtual environment:
   python -m venv .venv
2. Activate it:
   .venv\Scripts\activate
3. Install dependencies:
   pip install -r requirements.txt
4. Copy environment file:
   copy .env.example .env
5. Run the app:
   python backend/app.py
6. Open http://localhost:5000

## Default admin account
- Username: admin
- Password: admin123

## Important notes
- This app is configured for localhost development without paid services.
- WhatsApp integration is modular and disabled by default unless configured in `.env`.
- The application uses SQLite for local development; set `DATABASE_URL` to a MySQL DSN for external database use.
