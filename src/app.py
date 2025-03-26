from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
import bcrypt
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import re
from config import Config, supabase
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from route_manager import route_manager
from health_checker import health_checker
from flask_cors import CORS
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://lokiplus.netlify.app",
            "http://localhost:5173",
            "http://localhost:4173",
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Helper functions and decorators
def validate_json_request(*required_fields):
    """Decorator to validate JSON request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': 'Missing required fields',
                    'missing_fields': missing_fields
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_db_health():
    """Check database health and connection"""
    try:
        # Try a simple query to check connection
        supabase.table('accounts').select('id').limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_checker.check_database(force=True)
        return False

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def validate_email(email):
    """Validate email format"""
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

# Health check endpoints
@app.route('/health')
def health_check():
    """Health check endpoint for Render."""
    try:
        is_healthy = check_db_health()
        return jsonify({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected' if is_healthy else 'disconnected'
        }), 200 if is_healthy else 503
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@app.route('/health/database')
def database_health():
    """Get database health status"""
    force_check = request.args.get('force', '').lower() == 'true'
    return jsonify(health_checker.check_database(force=force_check))

@app.route('/health/routes')
def route_health():
    """Get route health status"""
    return jsonify(route_manager.generate_report())

@app.route('/health/recommendations')
def health_recommendations():
    """Get health improvement recommendations"""
    return jsonify({
        'recommendations': health_checker.get_recommendations()
    })

@app.route('/health/live')
def live_status():
    """Get live status of all services"""
    try:
        # Check database connection
        db_health = health_checker.check_database()
        
        # Check application health
        app_health = health_checker.check_application()
        
        # Get route statistics
        route_stats = route_manager.generate_report()
        
        status = {
            'status': 'healthy' if all(h['status'] == 'healthy' for h in [db_health, app_health]) else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': {
                    'status': db_health['status'],
                    'latency': db_health.get('latency', 'N/A')
                },
                'application': {
                    'status': app_health['status'],
                    'uptime': app_health.get('uptime', 'N/A')
                },
                'routes': {
                    'total': len(route_stats['routes']),
                    'healthy': sum(1 for r in route_stats['routes'].values() if r['status'] == 'healthy')
                }
            }
        }
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error checking live status: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

def check_db_connection():
    """Check database connection and handle errors"""
    try:
        supabase.table('accounts').select('id').limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        health_checker.check_database(force=True)  # Force update health status
        raise

def get_db():
    """Get database connection"""
    return supabase.client.postgrest.client()

@app.route('/')
@route_manager.monitor()
def index():
    """Render the main page with accounts and clients"""
    try:
        # Fetch accounts from Supabase
        accounts_response = supabase.table('accounts').select('*').execute()
        accounts = accounts_response.data

        # Fetch clients from Supabase
        clients_response = supabase.table('clients').select('*').execute()
        clients = clients_response.data
        
        return render_template('index.html', accounts=accounts, clients=clients)
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        flash('Error fetching data. Please try again later.', 'danger')
        return render_template('index.html', accounts=[], clients=[], error=str(e))

@app.route('/add_account', methods=['POST'])
@route_manager.monitor(name='add_account')
def add_account():
    """Add a new account"""
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required', 'danger')
            return redirect(url_for('index'))
            
        if not validate_email(email):
            flash('Invalid email format', 'danger')
            return redirect(url_for('index'))
            
        if not validate_password(password):
            flash('Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one number', 'danger')
            return redirect(url_for('index'))
            
        # Hash the password
        hashed_password = hash_password(password)
        
        # Check if account already exists
        existing = supabase.table('accounts').select('id').eq('email', email).execute()
        if existing.data:
            flash('An account with this email already exists', 'danger')
            return redirect(url_for('index'))
            
        # Insert new account
        new_account = {
            'email': email,
            'password': hashed_password,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        result = supabase.table('accounts').insert(new_account).execute()
        
        if result.data:
            flash(f'Account {email} created successfully', 'success')
        else:
            flash('Error creating account', 'danger')
            
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error adding account: {e}")
        flash('Error adding account', 'danger')
        return redirect(url_for('index'))

@app.route('/update_status', methods=['POST'])
@limiter.limit("10 per minute")
@route_manager.monitor(name='update_status')
def update_status():
    """Update account status"""
    try:
        account_id = request.form.get('account_id')
        new_status = request.form.get('status')
        
        if not account_id or not new_status:
            flash('Account ID and status are required', 'danger')
            return redirect(url_for('index'))
        
        result = supabase.table('accounts').update({
            'status': new_status,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', account_id).execute()
        
        if result.data:
            flash('Status updated successfully', 'success')
        else:
            flash('Error updating status', 'danger')
        
    except Exception as e:
        logger.error(f"Error updating status: {e}")
        flash('Error updating status', 'danger')
    
    return redirect(url_for('index'))

@app.route('/check_client', methods=['POST'])
@route_manager.monitor(name='check_client')
@validate_json_request('email')
def check_client():
    """Check if a client with the given email already exists"""
    try:
        data = request.get_json()
        email = data['email']
        
        result = supabase.table('clients').select('*').eq('email', email).execute()
        
        if result.data:
            client = result.data[0]
            return jsonify({
                'exists': True,
                'client': {
                    'id': client['id'],
                    'name': client['name'],
                    'email': client['email'],
                    'renewal_date': client['renewal_date']
                }
            })
        return jsonify({'exists': False})
        
    except Exception as e:
        logger.error(f"Error checking client: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/add_client', methods=['POST'])
@route_manager.monitor(name='add_client')
def add_client():
    """Add a new client"""
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        account_id = request.form.get('account_id')
        renewal_date = request.form.get('renewal_date')
        
        if not all([name, email, account_id, renewal_date]):
            flash('All fields are required', 'danger')
            return redirect(url_for('index'))
            
        if not validate_email(email):
            flash('Invalid email format', 'danger')
            return redirect(url_for('index'))
            
        # Check if client already exists
        existing = supabase.table('clients').select('id').eq('email', email).execute()
        if existing.data:
            flash('A client with this email already exists', 'danger')
            return redirect(url_for('index'))
            
        # Insert new client
        new_client = {
            'name': name,
            'email': email,
            'renewal_date': renewal_date,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        client_result = supabase.table('clients').insert(new_client).execute()
        
        if client_result.data:
            # Create account-client relationship
            client_id = client_result.data[0]['id']
            relation = {
                'account_id': account_id,
                'client_id': client_id,
                'created_at': datetime.utcnow().isoformat()
            }
            relation_result = supabase.table('account_clients').insert(relation).execute()
            
            if relation_result.data:
                flash(f'Client {name} added successfully', 'success')
            else:
                # Rollback client creation if relation fails
                supabase.table('clients').delete().eq('id', client_id).execute()
                flash('Error linking client to account', 'danger')
        else:
            flash('Error adding client', 'danger')
            
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error adding client: {e}")
        flash('Error adding client', 'danger')
        return redirect(url_for('index'))

@app.route('/link_client', methods=['POST'])
@limiter.limit("5 per minute")
@route_manager.monitor(name='link_client')
@validate_json_request('client_id', 'account_id')
def link_client():
    """Link a client to an account"""
    try:
        data = request.get_json()
        client_id = data['client_id']
        account_id = data['account_id']
        
        # Check if account already has 5 clients
        count_result = supabase.table('account_clients').select(
            'id', count='exact'
        ).eq('account_id', account_id).execute()
        
        if count_result.count >= 5:
            return jsonify({
                'success': False,
                'error': 'Account already has maximum number of clients (5)'
            }), 400
        
        # Check if client is already linked to this account
        existing = supabase.table('account_clients').select('id').match({
            'client_id': client_id,
            'account_id': account_id
        }).execute()
        
        if existing.data:
            return jsonify({
                'success': False,
                'error': 'Client is already linked to this account'
            }), 400
        
        # Link client to account
        result = supabase.table('account_clients').insert({
            'client_id': client_id,
            'account_id': account_id,
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        if result.data:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to link client'}), 500
        
    except Exception as e:
        logger.error(f"Error linking client: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/unlink_client', methods=['POST'])
@limiter.limit("5 per minute")
@route_manager.monitor(name='unlink_client')
@validate_json_request('client_id', 'account_id')
def unlink_client():
    """Unlink a client from an account"""
    try:
        data = request.get_json()
        client_id = data['client_id']
        account_id = data['account_id']
        
        result = supabase.table('account_clients').delete().match({
            'client_id': client_id,
            'account_id': account_id
        }).execute()
        
        if result.data:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'error': 'Client is not linked to this account'
            }), 404
        
    except Exception as e:
        logger.error(f"Error unlinking client: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/account_clients/<int:account_id>')
@route_manager.monitor(name='get_account_clients')
def get_account_clients(account_id):
    """Get all clients linked to an account"""
    try:
        # First check if the account exists
        account = supabase.table('accounts').select('id').eq('id', account_id).execute()
        if not account.data:
            return {'error': 'Account not found'}, 404
        
        # Get all clients linked to this account through the account_clients table
        relations = supabase.table('account_clients').select(
            'client_id'
        ).eq('account_id', account_id).execute()
        
        if not relations.data:
            return {'clients': []}
        
        client_ids = [r['client_id'] for r in relations.data]
        clients_result = supabase.table('clients').select('*').in_('id', client_ids).execute()
        
        clients = []
        for client in clients_result.data:
            clients.append({
                'id': client['id'],
                'name': client['name'],
                'email': client['email'],
                'renewal_date': client['renewal_date']
            })
        
        return {'clients': clients}
        
    except Exception as e:
        logger.error(f"Error fetching account clients: {e}")
        return {'error': str(e)}, 500

@app.route('/renew_client', methods=['POST'])
@route_manager.monitor(name='renew_client')
@validate_json_request('client_id', 'renewal_date')
def renew_client():
    """Renew a client's subscription"""
    try:
        data = request.get_json()
        client_id = data['client_id']
        new_renewal_date = data['renewal_date']
            
        # Update client renewal date
        result = supabase.table('clients').update({
            'renewal_date': new_renewal_date,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', client_id).execute()
        
        if result.data:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update renewal date'}), 500
            
    except Exception as e:
        error_msg = f"Error renewing client: {str(e)}"
        logger.error(f"Renew client error: {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/delete_account', methods=['POST'])
@limiter.limit("5 per minute")
@route_manager.monitor(name='delete_account')
def delete_account():
    """Delete an account and all its client associations"""
    try:
        account_id = request.form.get('account_id')
        
        if not account_id:
            flash('Account ID is required', 'danger')
            return redirect(url_for('index'))
        
        # Delete account-client relationships first
        supabase.table('account_clients').delete().eq('account_id', account_id).execute()
        
        # Delete the account
        result = supabase.table('accounts').delete().eq('id', account_id).execute()
        
        if result.data:
            flash('Account deleted successfully', 'success')
        else:
            flash('Account not found', 'danger')
        
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        flash('Error deleting account', 'danger')
    
    return redirect(url_for('index'))

@app.route('/clients')
@route_manager.monitor(name='get_clients')
def get_clients():
    """Get all clients with optional JSON response"""
    try:
        want_json = request.args.get('format') == 'json'
        
        # Fetch clients with their associated accounts
        clients_response = supabase.table('clients').select(
            '*',
            count='exact'
        ).execute()
        
        if not clients_response.data:
            if want_json:
                return jsonify({
                    'status': 'success',
                    'count': 0,
                    'clients': []
                })
            else:
                return render_template('clients.html', clients=[])
                
        # Format client data
        formatted_clients = []
        for client in clients_response.data:
            # Get associated accounts for each client
            relations = supabase.table('account_clients').select(
                'account_id'
            ).eq('client_id', client['id']).execute()
            
            account_ids = [r['account_id'] for r in relations.data]
            accounts = []
            if account_ids:
                accounts_response = supabase.table('accounts').select(
                    'email'
                ).in_('id', account_ids).execute()
                accounts = [a['email'] for a in accounts_response.data]
            
            formatted_clients.append({
                'id': client['id'],
                'name': client['name'],
                'email': client['email'],
                'status': client['status'],
                'renewal_date': client['renewal_date'],
                'accounts': accounts
            })
            
        if want_json:
            return jsonify({
                'status': 'success',
                'count': len(formatted_clients),
                'clients': formatted_clients
            })
        else:
            return render_template('clients.html', clients=formatted_clients)
            
    except Exception as e:
        logger.error(f"Error in get_clients: {e}")
        if want_json:
            return jsonify({
                'status': 'error',
                'message': 'Internal server error',
                'error': str(e)
            }), 500
        else:
            flash('Error fetching clients. Please try again later.', 'danger')
            return render_template('clients.html', clients=[])

# Error handlers
@app.errorhandler(404)
@route_manager.monitor(description="404 Not Found handler")
def not_found_error(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found', 'status_code': 404}), 404

@app.errorhandler(500)
@route_manager.monitor(description="500 Internal Server Error handler")
def internal_error(error):
    """Handle 500 errors"""
    # Check database health when a server error occurs
    db_status = health_checker.check_database(force=True)
    
    error_context = {
        'error': 'Internal server error',
        'status_code': 500,
        'timestamp': datetime.now().isoformat(),
        'db_status': db_status['status']
    }
    
    logger.error(f"Internal server error: {error}")
    return jsonify(error_context), 500

# Remove psycopg2 error handler and replace with general database error handler
@app.errorhandler(Exception)
def handle_db_error(error):
    """Handle database and other errors"""
    logger.error(f"Application error: {error}")
    db_status = health_checker.check_database(force=True)
    
    # Check if it's a database-related error
    if 'database' in str(error).lower() or 'supabase' in str(error).lower():
        error_context = {
            'error': 'Database connection error',
            'status_code': 503,
            'timestamp': datetime.now().isoformat(),
            'db_status': db_status['status'],
            'retry_after': 60  # Suggest retry after 1 minute
        }
        
        response = jsonify(error_context)
        response.status_code = 503
        response.headers['Retry-After'] = '60'
        return response
    
    # For other errors, return 500
    return jsonify({
        'error': str(error),
        'status_code': 500,
        'timestamp': datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    # Check application health before starting
    with app.app_context():
        initial_health = health_checker.check_application()
        if initial_health['status'] != 'healthy':
            logger.warning("Application started with unhealthy status")
            logger.warning(f"Health check results: {initial_health}")
    
    app.run(debug=True) 