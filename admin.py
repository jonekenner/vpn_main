"""
Admin panel utilities
"""
from models import db
import uuid as uuid_module
from datetime import datetime, timedelta


def create_plan(name, price, duration_days):
    """Create a new subscription plan"""
    try:
        db.execute_query(
            'INSERT INTO plans (name, price, duration_days) VALUES (?, ?, ?)',
            (name, price, duration_days)
        )
        return True, "Plan created successfully"
    except Exception as e:
        return False, f"Failed to create plan: {str(e)}"


def update_plan(plan_id, name, price, duration_days):
    """Update an existing plan"""
    try:
        db.execute_query(
            'UPDATE plans SET name = ?, price = ?, duration_days = ? WHERE id = ?',
            (name, price, duration_days, plan_id)
        )
        return True, "Plan updated successfully"
    except Exception as e:
        return False, f"Failed to update plan: {str(e)}"


def delete_plan(plan_id):
    """Delete a plan"""
    try:
        db.execute_query('DELETE FROM plans WHERE id = ?', (plan_id,))
        return True, "Plan deleted successfully"
    except Exception as e:
        return False, f"Failed to delete plan: {str(e)}"


def get_all_plans():
    """Get all subscription plans"""
    return db.execute_query('SELECT * FROM plans ORDER BY duration_days')


def get_all_users():
    """Get all users with their subscription info"""
    query = '''
        SELECT u.id, u.email, u.is_active, u.created_at,
               s.status, s.end_date,
               p.name as plan_name
        FROM users u
        LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'active'
        LEFT JOIN plans p ON s.plan_id = p.id
        ORDER BY u.created_at DESC
    '''
    return db.execute_query(query)


def toggle_user_status(user_id):
    """Enable or disable a user"""
    user = db.execute_one('SELECT is_active FROM users WHERE id = ?', (user_id,))
    if not user:
        return False, "User not found"
    
    new_status = 0 if user['is_active'] else 1
    db.execute_query('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
    return True, "User status updated"


def generate_v2ray_config(user_id, server='vpn.example.com', port=443):
    """Generate a V2Ray config for a user"""
    # Check if user already has a config
    existing = db.execute_one('SELECT id FROM v2ray_configs WHERE user_id = ?', (user_id,))
    
    if existing:
        config = db.execute_one(
            'SELECT uuid, server, port, protocol FROM v2ray_configs WHERE user_id = ?',
            (user_id,)
        )
        return dict(config)
    
    # Generate new UUID and config
    new_uuid = str(uuid_module.uuid4())
    try:
        db.execute_query(
            'INSERT INTO v2ray_configs (user_id, uuid, server, port, protocol) VALUES (?, ?, ?, ?, ?)',
            (user_id, new_uuid, server, port, 'vmess')
        )
        return {'uuid': new_uuid, 'server': server, 'port': port, 'protocol': 'vmess'}
    except Exception as e:
        return None


def assign_subscription(user_id, plan_id):
    """Assign a subscription to a user"""
    plan = db.execute_one('SELECT duration_days FROM plans WHERE id = ?', (plan_id,))
    if not plan:
        return False, "Plan not found"
    
    start_date = datetime.now()
    end_date = start_date + timedelta(days=plan['duration_days'])
    
    # Deactivate existing subscriptions
    db.execute_query(
        'UPDATE subscriptions SET status = ? WHERE user_id = ? AND status = ?',
        ('expired', user_id, 'active')
    )
    
    # Create new subscription
    try:
        db.execute_query(
            'INSERT INTO subscriptions (user_id, plan_id, start_date, end_date, status) VALUES (?, ?, ?, ?, ?)',
            (user_id, plan_id, start_date.isoformat(), end_date.isoformat(), 'active')
        )
        return True, "Subscription assigned successfully"
    except Exception as e:
        return False, f"Failed to assign subscription: {str(e)}"


def get_all_subscriptions():
    """Get all subscriptions"""
    query = '''
        SELECT s.id, s.start_date, s.end_date, s.status,
               u.email, u.id as user_id,
               p.name as plan_name, p.price
        FROM subscriptions s
        JOIN users u ON s.user_id = u.id
        JOIN plans p ON s.plan_id = p.id
        ORDER BY s.start_date DESC
    '''
    return db.execute_query(query)


def get_pending_payments():
    """Get all pending payment submissions"""
    query = '''
        SELECT ps.id, ps.bank_name, ps.account_number, ps.transaction_id,
               ps.payment_slip_filename, ps.submitted_at, ps.status,
               u.email, u.id as user_id,
               p.name as plan_name, p.price, p.id as plan_id
        FROM payment_submissions ps
        JOIN users u ON ps.user_id = u.id
        JOIN plans p ON ps.plan_id = p.id
        WHERE ps.status = 'pending'
        ORDER BY ps.submitted_at DESC
    '''
    return db.execute_query(query)


def get_all_payments():
    """Get all payment submissions"""
    query = '''
        SELECT ps.id, ps.bank_name, ps.account_number, ps.transaction_id,
               ps.payment_slip_filename, ps.submitted_at, ps.status, ps.reviewed_at,
               u.email, u.id as user_id,
               p.name as plan_name, p.price, p.id as plan_id
        FROM payment_submissions ps
        JOIN users u ON ps.user_id = u.id
        JOIN plans p ON ps.plan_id = p.id
        ORDER BY ps.submitted_at DESC
    '''
    return db.execute_query(query)


def save_vless_config(user_id, vless_url):
    """Save VLESS URL for a user"""
    # Check if user already has a config
    existing = db.execute_one('SELECT id FROM v2ray_configs WHERE user_id = ?', (user_id,))
    
    if existing:
        # Update existing config
        db.execute_query(
            'UPDATE v2ray_configs SET vless_url = ? WHERE user_id = ?',
            (vless_url, user_id)
        )
    else:
        # Create new config with VLESS URL
        db.execute_query(
            'INSERT INTO v2ray_configs (user_id, vless_url, protocol) VALUES (?, ?, ?)',
            (user_id, vless_url, 'vless')
        )
    return True


def approve_payment(payment_id, admin_id, vless_url=None):
    """Approve a payment and assign subscription"""
    # Get payment details
    payment = db.execute_one('''
        SELECT user_id, plan_id FROM payment_submissions WHERE id = ? AND status = 'pending'
    ''', (payment_id,))
    
    if not payment:
        return False, "Payment not found or already processed"
    
    user_id = payment['user_id']
    plan_id = payment['plan_id']
    
    # Assign subscription
    success, message = assign_subscription(user_id, plan_id)
    if not success:
        return False, message
    
    # Save VLESS URL if provided
    if vless_url and vless_url.strip():
        save_vless_config(user_id, vless_url.strip())
    
    # Update payment status
    now = datetime.now().isoformat()
    db.execute_query('''
        UPDATE payment_submissions 
        SET status = 'approved', reviewed_at = ?, reviewed_by = ?
        WHERE id = ?
    ''', (now, admin_id, payment_id))
    
    return True, "Payment approved and subscription activated"


def reject_payment(payment_id, admin_id):
    """Reject a payment submission"""
    payment = db.execute_one('SELECT id FROM payment_submissions WHERE id = ? AND status = ?', 
                            (payment_id, 'pending'))
    if not payment:
        return False, "Payment not found or already processed"
    
    now = datetime.now().isoformat()
    db.execute_query('''
        UPDATE payment_submissions 
        SET status = 'rejected', reviewed_at = ?, reviewed_by = ?
        WHERE id = ?
    ''', (now, admin_id, payment_id))
    
    return True, "Payment rejected"


def get_user_payments(user_id):
    """Get all payment submissions for a specific user"""
    query = '''
        SELECT ps.id, ps.bank_name, ps.account_number, ps.transaction_id,
               ps.payment_slip_filename, ps.submitted_at, ps.status, ps.reviewed_at,
               p.name as plan_name, p.price, p.id as plan_id
        FROM payment_submissions ps
        JOIN plans p ON ps.plan_id = p.id
        WHERE ps.user_id = ?
        ORDER BY ps.submitted_at DESC
    '''
    return db.execute_query(query, (user_id,))


# Server Management Functions
def create_server(name, country, city, status='online', location_code=None):
    """Create a new server"""
    try:
        db.execute_query(
            'INSERT INTO servers (name, country, city, status, location_code) VALUES (?, ?, ?, ?, ?)',
            (name, country, city, status, location_code)
        )
        return True, "Server created successfully"
    except Exception as e:
        return False, f"Failed to create server: {str(e)}"


def update_server(server_id, name, country, city, status, location_code=None):
    """Update an existing server"""
    try:
        db.execute_query(
            'UPDATE servers SET name = ?, country = ?, city = ?, status = ?, location_code = ? WHERE id = ?',
            (name, country, city, status, location_code, server_id)
        )
        return True, "Server updated successfully"
    except Exception as e:
        return False, f"Failed to update server: {str(e)}"


def delete_server(server_id):
    """Delete a server"""
    try:
        db.execute_query('DELETE FROM servers WHERE id = ?', (server_id,))
        return True, "Server deleted successfully"
    except Exception as e:
        return False, f"Failed to delete server: {str(e)}"


def get_all_servers():
    """Get all servers"""
    return db.execute_query('SELECT * FROM servers ORDER BY country, city')


def toggle_server_status(server_id):
    """Toggle server active status"""
    server = db.execute_one('SELECT is_active FROM servers WHERE id = ?', (server_id,))
    if not server:
        return False, "Server not found"
    
    new_status = 0 if server['is_active'] else 1
    db.execute_query('UPDATE servers SET is_active = ? WHERE id = ?', (new_status, server_id))
    return True, "Server status updated"

