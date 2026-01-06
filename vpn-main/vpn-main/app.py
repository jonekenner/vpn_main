"""
Main Flask application for VPN/V2Ray subscription service
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from functools import wraps
from datetime import datetime, timedelta
import io
import json
import base64
import qrcode
import os
import uuid as uuid_module
from werkzeug.utils import secure_filename
from models import db
from auth import register_user, authenticate_user, is_admin
from admin import (
    create_plan, update_plan, delete_plan, get_all_plans,
    get_all_users, toggle_user_status, generate_v2ray_config,
    assign_subscription, get_all_subscriptions,
    get_pending_payments, get_all_payments, approve_payment, reject_payment,
    get_user_payments, save_vless_config,
    create_server, update_server, delete_server, get_all_servers, toggle_server_status
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production!

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Decorators
def login_required(f):
    """Require user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Require user to be admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not is_admin(session.get('email', '')):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Public Routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/pricing')
def pricing():
    """Pricing page"""
    plans = get_all_plans()
    return render_template('pricing.html', plans=plans)


@app.route('/servers')
def servers():
    """Server locations page"""
    # Fetch servers from database
    server_list = get_all_servers()
    # Convert Row objects to dicts and filter only active servers
    servers_data = [dict(s) for s in server_list if s['is_active']]
    return render_template('servers.html', servers=servers_data)


@app.route('/faq')
def faq():
    """FAQ page"""
    faqs = [
        {
            'question': 'What is V2Ray?',
            'answer': 'V2Ray is a platform for building proxies to help you bypass internet restrictions and protect your privacy.'
        },
        {
            'question': 'How do I use the V2Ray config?',
            'answer': 'Download the V2Ray config file from your dashboard and import it into a V2Ray client like V2RayN (Windows), V2RayNG (Android), or V2RayX (macOS).'
        },
        {
            'question': 'What payment methods do you accept?',
            'answer': 'We currently accept credit cards, PayPal, and cryptocurrency. More payment methods coming soon!'
        },
        {
            'question': 'Can I cancel my subscription?',
            'answer': 'Subscriptions are prepaid and will automatically expire at the end of the billing period. No cancellation needed.'
        },
        {
            'question': 'Is my data secure?',
            'answer': 'Yes, we use industry-standard encryption and do not log your internet activity. Your privacy is our priority.'
        },
        {
            'question': 'What happens when my subscription expires?',
            'answer': 'Your V2Ray config will stop working. You can renew your subscription at any time to continue using the service.'
        }
    ]
    return render_template('faq.html', faqs=faqs)


@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')


# Authentication Routes
@app.route('/auth')
def auth_page():
    """Combined login/register page"""
    message = session.pop('message', None)
    error = session.pop('error', None)
    return render_template('auth.html', message=message, error=error)


@app.route('/login', methods=['GET'])
def login_page():
    """Login page - redirects to auth page"""
    return redirect(url_for('auth_page') + '#login')


@app.route('/register', methods=['GET'])
def register_page():
    """Register page - redirects to auth page"""
    return redirect(url_for('auth_page') + '#register')


@app.route('/register', methods=['POST'])
def register():
    """User registration"""
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Validate password confirmation
    if password != confirm_password:
        session['error'] = "Passwords do not match"
        return redirect(url_for('auth_page') + '#register')
    
    success, message = register_user(email, password)
    if success:
        session['message'] = message
        return redirect(url_for('auth_page') + '#login')
    else:
        session['error'] = message
        return redirect(url_for('auth_page') + '#register')


@app.route('/login', methods=['POST'])
def login():
    """User login"""
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    
    user, error = authenticate_user(email, password)
    if user:
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['is_admin'] = is_admin(email)
        
        if session['is_admin']:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    else:
        session['error'] = error
        return redirect(url_for('auth_page') + '#login')


@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    return redirect(url_for('index'))


# User Dashboard Routes
@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    user_id = session['user_id']
    
    # Get user's active subscription
    subscription = db.execute_one('''
        SELECT s.*, p.name as plan_name, p.price, p.duration_days
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.user_id = ? AND s.status = 'active'
        ORDER BY s.end_date DESC
        LIMIT 1
    ''', (user_id,))
    
    # Get V2Ray config (VLESS URL or traditional config)
    config_row = db.execute_one(
        'SELECT uuid, server, port, protocol, vless_url FROM v2ray_configs WHERE user_id = ?',
        (user_id,)
    )
    
    # Convert Row to dict for template use
    config = dict(config_row) if config_row else None
    
    # Calculate remaining days
    remaining_days = 0
    if subscription:
        end_date = datetime.fromisoformat(subscription['end_date'])
        remaining_days = max(0, (end_date - datetime.now()).days)
    
    # Get user's payment submissions
    user_payments = get_user_payments(user_id)
    pending_payments = [p for p in user_payments if p['status'] == 'pending']
    
    return render_template('dashboard.html', 
                         subscription=subscription,
                         config=config,
                         remaining_days=remaining_days,
                         pending_payments=pending_payments,
                         user_payments=user_payments)


def generate_vmess_url(config, email):
    """Generate proper VMESS URL with base64 encoding"""
    vmess_config = {
        "v": "2",
        "ps": f"VPN Service - {email}",
        "add": config['server'],
        "port": str(config['port']),
        "id": config['uuid'],
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "",
        "path": "/",
        "tls": "tls"
    }
    config_json = json.dumps(vmess_config)
    config_b64 = base64.b64encode(config_json.encode('utf-8')).decode('utf-8')
    return f"vmess://{config_b64}"


@app.route('/config/qr')
@login_required
def config_qr():
    """Generate QR code for V2Ray/VLESS config"""
    user_id = session['user_id']
    config_row = db.execute_one(
        'SELECT uuid, server, port, protocol, vless_url FROM v2ray_configs WHERE user_id = ?',
        (user_id,)
    )
    
    if not config_row:
        return "No config found", 404
    
    # Convert Row to dict
    config = dict(config_row)
    
    # Use VLESS URL if available, otherwise generate VMESS URL
    if config.get('vless_url'):
        url_to_encode = config['vless_url']
    else:
        url_to_encode = generate_vmess_url(config, session.get('email', 'User'))
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url_to_encode)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')


@app.route('/config/vmess')
@login_required
def get_vmess_url():
    """Get VMESS URL as text"""
    user_id = session['user_id']
    config_row = db.execute_one(
        'SELECT uuid, server, port, protocol FROM v2ray_configs WHERE user_id = ?',
        (user_id,)
    )
    
    if not config_row:
        return "No config found", 404
    
    # Convert Row to dict
    config = dict(config_row)
    vmess_url = generate_vmess_url(config, session.get('email', 'User'))
    return vmess_url


@app.route('/config/download')
@login_required
def download_config():
    """Download V2Ray config file"""
    user_id = session['user_id']
    config_row = db.execute_one(
        'SELECT uuid, server, port, protocol FROM v2ray_configs WHERE user_id = ?',
        (user_id,)
    )
    
    if not config_row:
        return "No config found", 404
    
    # Convert Row to dict
    config = dict(config_row)
    
    # Generate V2Ray config JSON
    config_json = {
        "v": "2",
        "ps": f"VPN Service - {session.get('email', 'User')}",
        "add": config['server'],
        "port": str(config['port']),
        "id": config['uuid'],
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "",
        "path": "/",
        "tls": "tls"
    }
    
    config_str = json.dumps(config_json, indent=2)
    
    return send_file(
        io.BytesIO(config_str.encode()),
        mimetype='application/json',
        as_attachment=True,
        download_name='v2ray-config.json'
    )


@app.route('/subscribe/<int:plan_id>')
@login_required
def subscribe(plan_id):
    """Show payment form for subscription"""
    user_id = session['user_id']
    
    # Check if plan exists
    plan = db.execute_one('SELECT * FROM plans WHERE id = ?', (plan_id,))
    if not plan:
        return "Plan not found", 404
    
    # Get bank details (you can store these in a config or database)
    bank_details = {
        'bank_name': 'Your Bank Name',
        'account_number': '1234567890',
        'account_holder': 'VPN Service',
        'swift_code': 'BANKCODE123'
    }
    
    return render_template('payment.html', plan=plan, bank_details=bank_details)


@app.route('/payment/submit/<int:plan_id>', methods=['POST'])
@login_required
def submit_payment(plan_id):
    """Submit payment with bank details and payment slip"""
    user_id = session['user_id']
    
    # Check if plan exists
    plan = db.execute_one('SELECT * FROM plans WHERE id = ?', (plan_id,))
    if not plan:
        return "Plan not found", 404
    
    # Get form data
    bank_name = request.form.get('bank_name', '').strip()
    transaction_id = request.form.get('transaction_id', '').strip()
    
    # Validate required fields
    if not bank_name:
        session['error'] = "Please fill in all required fields"
        return redirect(url_for('subscribe', plan_id=plan_id))
    
    # Handle file upload
    if 'payment_slip' not in request.files:
        session['error'] = "Please upload a payment slip"
        return redirect(url_for('subscribe', plan_id=plan_id))
    
    file = request.files['payment_slip']
    if file.filename == '':
        session['error'] = "Please select a payment slip file"
        return redirect(url_for('subscribe', plan_id=plan_id))
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{user_id}_{plan_id}_{uuid_module.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Save payment submission to database
        try:
            db.execute_query('''
                INSERT INTO payment_submissions 
                (user_id, plan_id, bank_name, account_number, transaction_id, payment_slip_filename, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, plan_id, bank_name, 'N/A', transaction_id, unique_filename, 'pending'))
            
            session['message'] = "Payment submitted successfully! Admin will review and activate your subscription soon."
            return redirect(url_for('dashboard'))
        except Exception as e:
            # Delete uploaded file if database insert fails
            if os.path.exists(filepath):
                os.remove(filepath)
            session['error'] = f"Failed to submit payment: {str(e)}"
            return redirect(url_for('subscribe', plan_id=plan_id))
    else:
        session['error'] = "Invalid file type. Please upload PNG, JPG, JPEG, PDF, or GIF"
        return redirect(url_for('subscribe', plan_id=plan_id))


# Admin Routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    users = get_all_users()
    plans = get_all_plans()
    subscriptions = get_all_subscriptions()
    
    return render_template('admin/dashboard.html',
                         users=users,
                         plans=plans,
                         subscriptions=subscriptions)


@app.route('/admin/plans/create', methods=['POST'])
@admin_required
def admin_create_plan():
    """Create a new plan"""
    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0))
    duration_days = int(request.form.get('duration_days', 0))
    
    success, message = create_plan(name, price, duration_days)
    session['admin_message'] = message
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/plans/update/<int:plan_id>', methods=['POST'])
@admin_required
def admin_update_plan(plan_id):
    """Update a plan"""
    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0))
    duration_days = int(request.form.get('duration_days', 0))
    
    success, message = update_plan(plan_id, name, price, duration_days)
    session['admin_message'] = message
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/plans/delete/<int:plan_id>')
@admin_required
def admin_delete_plan(plan_id):
    """Delete a plan"""
    success, message = delete_plan(plan_id)
    session['admin_message'] = message
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/toggle/<int:user_id>')
@admin_required
def admin_toggle_user(user_id):
    """Toggle user active status"""
    success, message = toggle_user_status(user_id)
    session['admin_message'] = message
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/assign/<int:user_id>', methods=['POST'])
@admin_required
def admin_assign_subscription(user_id):
    """Assign subscription to user"""
    plan_id = int(request.form.get('plan_id', 0))
    success, message = assign_subscription(user_id, plan_id)
    
    # Generate config if needed
    if success:
        generate_v2ray_config(user_id)
    
    session['admin_message'] = message
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/config/<int:user_id>')
@admin_required
def admin_generate_config(user_id):
    """Generate V2Ray config for user"""
    config = generate_v2ray_config(user_id)
    if config:
        session['admin_message'] = "V2Ray config generated successfully"
    else:
        session['admin_message'] = "Failed to generate config"
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/payments')
@admin_required
def admin_payments():
    """Admin payments page"""
    pending_payments = get_pending_payments()
    all_payments = get_all_payments()
    return render_template('admin/payments.html', 
                         pending_payments=pending_payments,
                         all_payments=all_payments)


@app.route('/admin/payments/approve/<int:payment_id>', methods=['GET', 'POST'])
@admin_required
def admin_approve_payment(payment_id):
    """Approve a payment submission with VLESS URL"""
    admin_id = session['user_id']
    
    if request.method == 'POST':
        vless_url = request.form.get('vless_url', '').strip()
        if not vless_url:
            session['admin_message'] = "Please provide a VLESS URL"
            return redirect(url_for('admin_payments'))
        
        success, message = approve_payment(payment_id, admin_id, vless_url)
        session['admin_message'] = message
    else:
        # GET request - show approval form
        payment = db.execute_one('''
            SELECT ps.*, u.email, p.name as plan_name
            FROM payment_submissions ps
            JOIN users u ON ps.user_id = u.id
            JOIN plans p ON ps.plan_id = p.id
            WHERE ps.id = ? AND ps.status = 'pending'
        ''', (payment_id,))
        
        if not payment:
            session['admin_message'] = "Payment not found or already processed"
            return redirect(url_for('admin_payments'))
        
        # Convert Row to dict for template
        payment = dict(payment)
        return render_template('admin/approve_payment.html', payment=payment)
    
    return redirect(url_for('admin_payments'))


@app.route('/admin/payments/reject/<int:payment_id>')
@admin_required
def admin_reject_payment(payment_id):
    """Reject a payment submission"""
    admin_id = session['user_id']
    success, message = reject_payment(payment_id, admin_id)
    session['admin_message'] = message
    return redirect(url_for('admin_payments'))


@app.route('/admin/payments/view/<filename>')
@admin_required
def admin_view_payment_slip(filename):
    """View payment slip image"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    return "File not found", 404


@app.route('/payments')
@login_required
def user_payments():
    """User payment history page"""
    user_id = session['user_id']
    payments = get_user_payments(user_id)
    return render_template('payments.html', payments=payments)


@app.route('/payments/view/<filename>')
@login_required
def user_view_payment_slip(filename):
    """View user's own payment slip"""
    user_id = session['user_id']
    
    # Verify the payment slip belongs to this user
    payment = db.execute_one(
        'SELECT user_id FROM payment_submissions WHERE payment_slip_filename = ?',
        (filename,)
    )
    
    if not payment or payment['user_id'] != user_id:
        return "Access denied", 403
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    return "File not found", 404


# Server Management Routes
@app.route('/admin/servers')
@admin_required
def admin_servers():
    """Admin server management page"""
    servers = get_all_servers()
    # Convert Row objects to dicts
    servers = [dict(server) for server in servers]
    return render_template('admin/servers.html', servers=servers)


@app.route('/admin/servers/create', methods=['POST'])
@admin_required
def admin_create_server():
    """Create a new server"""
    name = request.form.get('name', '').strip()
    country = request.form.get('country', '').strip()
    city = request.form.get('city', '').strip()
    status = request.form.get('status', 'online').strip()
    location_code = request.form.get('location_code', '').strip() or None
    
    if not name or not country or not city:
        session['admin_message'] = "Please fill in all required fields"
        return redirect(url_for('admin_servers'))
    
    success, message = create_server(name, country, city, status, location_code)
    session['admin_message'] = message
    return redirect(url_for('admin_servers'))


@app.route('/admin/servers/update/<int:server_id>', methods=['POST'])
@admin_required
def admin_update_server(server_id):
    """Update a server"""
    name = request.form.get('name', '').strip()
    country = request.form.get('country', '').strip()
    city = request.form.get('city', '').strip()
    status = request.form.get('status', 'online').strip()
    location_code = request.form.get('location_code', '').strip() or None
    
    if not name or not country or not city:
        session['admin_message'] = "Please fill in all required fields"
        return redirect(url_for('admin_servers'))
    
    success, message = update_server(server_id, name, country, city, status, location_code)
    session['admin_message'] = message
    return redirect(url_for('admin_servers'))


@app.route('/admin/servers/delete/<int:server_id>')
@admin_required
def admin_delete_server(server_id):
    """Delete a server"""
    success, message = delete_server(server_id)
    session['admin_message'] = message
    return redirect(url_for('admin_servers'))


@app.route('/admin/servers/toggle/<int:server_id>')
@admin_required
def admin_toggle_server(server_id):
    """Toggle server active status"""
    success, message = toggle_server_status(server_id)
    session['admin_message'] = message
    return redirect(url_for('admin_servers'))


# Background task to expire subscriptions
def expire_subscriptions():
    """Check and expire subscriptions that have passed their end date"""
    now = datetime.now().isoformat()
    result = db.execute_query(
        "UPDATE subscriptions SET status = 'expired' WHERE end_date < ? AND status = 'active'",
        (now,)
    )
    return result


@app.route('/cron/expire-subscriptions')
def cron_expire_subscriptions():
    """Cron endpoint to expire subscriptions (call this periodically)"""
    expire_subscriptions()
    return jsonify({"status": "success", "message": "Subscriptions checked and expired"})


if __name__ == '__main__':
    # Expire old subscriptions on startup
    expire_subscriptions()
    app.run(debug=True, host='0.0.0.0', port=80)

