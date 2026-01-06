# VPN/V2Ray Subscription Service

A modern, full-featured subscription-based VPN/V2Ray service website built with Flask and SQLite3.

## Features

### Public Website
- **Home Page**: Beautiful landing page explaining VPN/V2Ray benefits
- **Pricing Page**: Display subscription plans with clear pricing
- **Server Locations**: Show available server locations worldwide
- **FAQ Page**: Answer common questions
- **Contact Page**: Contact form and support information

### User Features
- **Registration & Login**: Secure user authentication with bcrypt password hashing
- **User Dashboard**: 
  - View active subscription status
  - See expiry date and remaining days
  - Access V2Ray configuration
  - Download config file
  - View QR code for easy mobile setup
- **Subscription Management**: Subscribe to plans (7, 30, or 90 days)

### Admin Panel
- **Plan Management**: Create, edit, and delete subscription plans
- **User Management**: View all users, enable/disable accounts
- **Subscription Management**: Assign subscriptions to users
- **V2Ray Config Generation**: Generate UUID-based V2Ray configurations
- **Comprehensive Dashboard**: View all users, plans, and subscriptions

## Tech Stack

- **Frontend**: HTML, Tailwind CSS, JavaScript
- **Backend**: Python Flask
- **Database**: SQLite3
- **Authentication**: Session-based login
- **Security**: bcrypt password hashing, SQL injection protection

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Download the Project

```bash
cd vpn_web
```

### Step 2: Create Virtual Environment (Recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

### Step 5: Access the Application

- **Home**: http://localhost:5000
- **Admin Login**: 
  - Email: `admin@vpnservice.com`
  - Password: `admin123`

## Project Structure

```
vpn_web/
├── app.py                 # Main Flask application
├── models.py              # Database models and initialization
├── auth.py                # Authentication utilities
├── admin.py               # Admin panel utilities
├── database.db            # SQLite database (created automatically)
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── templates/             # HTML templates
│   ├── base.html          # Base template
│   ├── index.html         # Home page
│   ├── pricing.html       # Pricing page
│   ├── servers.html       # Server locations
│   ├── faq.html           # FAQ page
│   ├── contact.html       # Contact page
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── dashboard.html     # User dashboard
│   └── admin/
│       └── dashboard.html # Admin dashboard
└── static/                # Static files (CSS, JS, images)
    ├── css/
    └── js/
```

## Database Schema

### Users Table
- `id`: Primary key
- `email`: Unique email address
- `password_hash`: Bcrypt hashed password
- `is_active`: Account status (1 = active, 0 = disabled)
- `created_at`: Account creation timestamp

### Plans Table
- `id`: Primary key
- `name`: Plan name (e.g., "30 Days Plan")
- `price`: Plan price in USD
- `duration_days`: Subscription duration in days
- `is_active`: Plan status

### Subscriptions Table
- `id`: Primary key
- `user_id`: Foreign key to users table
- `plan_id`: Foreign key to plans table
- `start_date`: Subscription start date
- `end_date`: Subscription end date
- `status`: Subscription status ('active' or 'expired')

### V2Ray Configs Table
- `id`: Primary key
- `user_id`: Foreign key to users table
- `uuid`: Unique V2Ray UUID
- `server`: Server address
- `port`: Server port
- `protocol`: Protocol type (default: 'vmess')

## Security Features

- **Password Hashing**: All passwords are hashed using bcrypt
- **SQL Injection Protection**: Parameterized queries prevent SQL injection
- **Session Management**: Secure session handling with Flask sessions
- **Input Validation**: Email and password validation on registration
- **CSRF Protection**: Flask's built-in CSRF protection (can be enhanced with Flask-WTF)

## Usage Guide

### For Users

1. **Register**: Create an account with your email and password
2. **Login**: Access your dashboard
3. **Subscribe**: Choose a plan from the pricing page
4. **Get Config**: Download your V2Ray config or scan QR code
5. **Use V2Ray**: Import config into V2Ray client (V2RayN, V2RayNG, etc.)

### For Admins

1. **Login**: Use admin credentials to access admin panel
2. **Manage Plans**: Create, edit, or delete subscription plans
3. **Manage Users**: View users, enable/disable accounts, assign subscriptions
4. **Generate Configs**: Generate V2Ray configurations for users
5. **View Subscriptions**: Monitor all active and expired subscriptions

## V2Ray Client Setup

### Windows
1. Download [V2RayN](https://github.com/2dust/v2rayN)
2. Import the downloaded config file
3. Connect to the server

### Android
1. Download [V2RayNG](https://github.com/2dust/v2rayNG)
2. Scan the QR code from your dashboard
3. Connect to the server

### macOS
1. Download [V2RayX](https://github.com/Cenmrev/V2RayX)
2. Import the downloaded config file
3. Connect to the server

## Customization

### Change Server Address

Edit the `generate_v2ray_config` function in `admin.py`:

```python
def generate_v2ray_config(user_id, server='your-server.com', port=443):
```

### Change Admin Credentials

The default admin is created in `models.py`. To change it:
1. Delete the existing admin user from the database
2. Modify the admin creation code in `models.py`
3. Reinitialize the database

### Add Payment Gateway

Replace the dummy payment in `app.py` route `/subscribe/<int:plan_id>` with your payment gateway integration (Stripe, PayPal, etc.)

## Production Deployment

### Security Checklist

1. **Change Secret Key**: Update `app.secret_key` in `app.py`
2. **Use Environment Variables**: Store sensitive data in environment variables
3. **Enable HTTPS**: Use SSL/TLS certificates
4. **Database Security**: Use PostgreSQL or MySQL for production
5. **Rate Limiting**: Add rate limiting to prevent abuse
6. **CSRF Tokens**: Implement Flask-WTF for CSRF protection
7. **Input Sanitization**: Add additional input validation

### Deployment Options

- **Heroku**: Easy deployment with Git
- **DigitalOcean**: VPS deployment
- **AWS**: EC2 or Elastic Beanstalk
- **Docker**: Containerize the application

## Troubleshooting

### Database Issues
- Delete `database.db` and restart the app to recreate the database
- Check file permissions for database file

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (3.8+)

### Port Already in Use
- Change port in `app.py`: `app.run(port=5001)`

## License

This project is provided as-is for educational and development purposes.

## Support

For issues or questions, please check the FAQ page or contact support through the contact form.

---

**Note**: This is a development/demo application. For production use, implement additional security measures, use a production-grade database, and integrate a real payment gateway.

