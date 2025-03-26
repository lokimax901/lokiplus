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
        # Try a simple query to check connection
        supabase.table('accounts').select('id').limit(1).execute()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503

@app.route('/health/database')
def database_health():
    """Get database health status"""
    try:
        # Try a simple query to check connection
        supabase.table('accounts').select('id').limit(1).execute()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503

@app.route('/health/live')
def live_status():
    """Get live status of all services"""
    try:
        # Check database connection
        supabase.table('accounts').select('id').limit(1).execute()
        
        status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': {
                    'status': 'healthy'
                },
                'application': {
                    'status': 'healthy'
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
        raise

def get_db():
    """Get database connection"""
    return supabase.client.postgrest.client()

@app.route('/')
def index():
    """Render the main page with accounts and clients"""
    try:
        # Try to connect to Supabase and fetch data
        accounts_response = supabase.table('accounts').select('*').execute()
        clients_response = supabase.table('clients').select('*').execute()
        
        # Get client count for each account
        for account in accounts_response.data:
            # Count clients linked to this account
            count_result = supabase.table('account_clients').select(
                'id', count='exact'
            ).eq('account_id', account['id']).execute()
            account['client_count'] = count_result.count or 0
            
            # Format the created_at date
            if account.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(account['created_at'].replace('Z', '+00:00'))
                    account['created_at'] = created_at.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    logger.warning(f"Error formatting date: {e}")
                    account['created_at'] = account['created_at']
        
        return render_template('index.html', 
                             accounts=accounts_response.data, 
                             clients=clients_response.data,
                             db_error=None,
                             error=None)
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        if 'connection' in str(e).lower() or 'network' in str(e).lower():
            return render_template('index.html', 
                                 accounts=[], 
                                 clients=[], 
                                 db_error=True,
                                 error=None)
        else:
            return render_template('index.html', 
                                 accounts=[], 
                                 clients=[], 
                                 db_error=None,
                                 error=str(e))

@app.route('/add_account', methods=['POST'])
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
            return jsonify({
                'success': False,
                'error': 'Client not found'
            }), 404

    except Exception as e:
        logger.error(f"Error renewing client: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_account', methods=['POST'])
@limiter.limit("5 per minute")
def delete_account():
    """Delete an account and all its client associations"""
    try:
        account_id = request.form.get('account_id')
        if not account_id:
            flash('Account ID is required', 'danger')
            return redirect(url_for('index'))

        # Delete account (cascade will handle client associations)
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
def get_clients():
    """Get all clients with optional JSON response"""
    try:
        # Fetch clients from Supabase
        clients_response = supabase.table('clients').select('*').execute()
        clients = clients_response.data

        # If request wants JSON response
        if request.headers.get('Accept') == 'application/json':
            return jsonify(clients)

        # Otherwise render template
        return render_template('clients.html', clients=clients)

    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e)}), 500
        flash('Error fetching clients', 'danger')
        return render_template('clients.html', clients=[], error=str(e))

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found', 'status_code': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    error_context = {
        'error': 'Internal server error',
        'status_code': 500,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.error(f"Internal server error: {error}")
    return jsonify(error_context), 500

@app.errorhandler(Exception)
def handle_db_error(error):
    """Handle database and other errors"""
    logger.error(f"Application error: {error}")
    
    # Check if it's a database-related error
    if 'database' in str(error).lower() or 'supabase' in str(error).lower():
        error_context = {
            'error': 'Database connection error',
            'status_code': 503,
            'timestamp': datetime.now().isoformat(),
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
    app.run(debug=True) 