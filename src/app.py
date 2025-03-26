from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
import psycopg2
import bcrypt
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import re
from config import Config, supabase
from db import DatabasePool
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from route_manager import route_manager
from health_checker import health_checker
from flask_cors import CORS

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

# Health check endpoints
@app.route('/health')
def health_check():
    """Health check endpoint for Render."""
    try:
        # Check database connection
        supabase.table('accounts').select('id').limit(1).execute()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        }), 200
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
        conn = get_db()
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection error: {e}")
        health_checker.check_database(force=True)  # Force update health status
        raise
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        health_checker.check_database(force=True)  # Force update health status
        raise

def get_db():
    """Get database connection from pool"""
    try:
        conn = psycopg2.connect(
            dbname=Config.DB_CONFIG['database'],
            user=Config.DB_CONFIG['user'],
            password=Config.DB_CONFIG['password'],
            host=Config.DB_CONFIG['host'],
            port=Config.DB_CONFIG['port']
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def verify_table_structure(cur, table_name):
    """Verify that a table has the expected structure"""
    # Get table columns
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    columns = cur.fetchall()
    
    # Get table indexes
    cur.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = %s
    """, (table_name,))
    indexes = cur.fetchall()
    
    return {
        'columns': columns,
        'indexes': indexes
    }

def init_db():
    """Initialize the database and create tables if they don't exist"""
    conn = None
    try:
        # First connect to default postgres database to create our database if it doesn't exist
        conn = psycopg2.connect(
            dbname='postgres',
            user=Config.DB_CONFIG['user'],
            password=Config.DB_CONFIG['password'],
            host=Config.DB_CONFIG['host'],
            port=Config.DB_CONFIG['port']
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create database if it doesn't exist
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{Config.DB_CONFIG['database']}'")
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {Config.DB_CONFIG['database']}")
            logger.info(f"Created database {Config.DB_CONFIG['database']}")
        
        cur.close()
        conn.close()
        
        # Now connect to our database and create/validate the tables
        conn = psycopg2.connect(**Config.DB_CONFIG)
        conn.autocommit = False  # Disable autocommit for transaction control
        cur = conn.cursor()
        
        # Begin transaction
        cur.execute("BEGIN")
        
        try:
            # Read and execute schema.sql
            schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
                # Execute the entire schema as one statement
                cur.execute(schema_sql)
            
            # Verify tables exist
            tables = ['clients', 'accounts', 'client_accounts']
            for table in tables:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table,))
                if not cur.fetchone()[0]:
                    raise Exception(f"Table {table} was not created properly")
                
                # Verify columns for each table
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
                columns = cur.fetchall()
                logger.info(f"Table {table} columns: {[col[0] for col in columns]}")
            
            # Commit transaction if everything is successful
            conn.commit()
            logger.info("Database schema initialized and verified successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during schema initialization: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

@app.route('/')
@route_manager.monitor(
    route='/',
    description="Main page displaying accounts and clients"
)
def index():
    """Display all accounts"""
    conn = None
    try:
        conn = check_db_connection()
        cur = conn.cursor()
        
        # Get all accounts with their client counts
        cur.execute('''
            SELECT a.id, a.email, a.password, a.status, 
                   a.created_at AT TIME ZONE 'UTC',
                   a.updated_at AT TIME ZONE 'UTC',
                   (SELECT COUNT(*) FROM client_accounts WHERE account_id = a.id) as client_count
            FROM accounts a 
            ORDER BY a.created_at DESC
        ''')
        accounts = cur.fetchall()
        
        # Get all clients
        cur.execute('SELECT * FROM clients ORDER BY name')
        clients = cur.fetchall()
        
        return render_template('index.html', accounts=accounts, clients=clients)
    except psycopg2.OperationalError:
        flash('Database connection error. Please try again later.', 'danger')
        return render_template('index.html', accounts=[], clients=[], db_error=True)
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        flash('Error fetching data. Please try again later.', 'danger')
        return render_template('index.html', accounts=[], clients=[], error=str(e))
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()

@app.route('/add_account', methods=['POST'])
@limiter.limit("5 per minute")
@route_manager.monitor(
    route='/add_account',
    required_params={
        'POST': {
            'email': str,
            'password': str,
            'status': str
        }
    },
    description="Add a new account"
)
def add_account():
    """Add a new account"""
    conn = None
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        status = request.form.get('status', 'active')
        
        if not email or not password:
            flash('Email and password are required', 'danger')
            return redirect(url_for('index'))
        
        # Validate email format
        if not validate_email(email):
            flash('Invalid email format', 'danger')
            return redirect(url_for('index'))
        
        # Validate password strength
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message, 'danger')
            return redirect(url_for('index'))
        
        conn = get_db()
        cur = conn.cursor()
        
        # Check if email already exists
        cur.execute('SELECT id FROM accounts WHERE email = %s', (email,))
        if cur.fetchone():
            flash('Email already exists', 'danger')
            return redirect(url_for('index'))
        
        # Hash password and insert account
        hashed_password = hash_password(password)
        cur.execute(
            'INSERT INTO accounts (email, password, status) VALUES (%s, %s, %s)',
            (email, hashed_password, status)
        )
        conn.commit()
        flash('Account added successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error adding account: {e}")
        flash('Error adding account', 'danger')
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()
    
    return redirect(url_for('index'))

@app.route('/update_status', methods=['POST'])
@limiter.limit("10 per minute")
@route_manager.monitor(
    route='/update_status',
    required_params={
        'POST': {
            'account_id': str,
            'status': str
        }
    },
    description="Update account status"
)
def update_status():
    """Update account status"""
    conn = None
    try:
        account_id = request.form.get('account_id')
        new_status = request.form.get('status')
        
        if not account_id or not new_status:
            flash('Account ID and status are required', 'danger')
            return redirect(url_for('index'))
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute(
            'UPDATE accounts SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
            (new_status, account_id)
        )
        conn.commit()
        flash('Status updated successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error updating status: {e}")
        flash('Error updating status', 'danger')
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()
    
    return redirect(url_for('index'))

@app.route('/check_client', methods=['POST'])
@route_manager.monitor(
    route='/check_client',
    required_params={
        'POST': {
            'email': str
        }
    },
    description="Check if a client exists"
)
def check_client():
    """Check if a client with the given email already exists"""
    conn = None
    try:
        email = request.form.get('email')
        if not email:
            return {'exists': False}
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT id, name, email, phone, renewal_date
            FROM clients
            WHERE email = %s
        ''', (email,))
        
        client = cur.fetchone()
        if client:
            return {
                'exists': True,
                'client': {
                    'id': client[0],
                    'name': client[1],
                    'email': client[2],
                    'phone': client[3],
                    'renewal_date': client[4].strftime('%Y-%m-%d') if client[4] else None
                }
            }
        return {'exists': False}
        
    except Exception as e:
        logger.error(f"Error checking client: {e}")
        return {'error': str(e)}, 500
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()

@app.route('/add_client', methods=['POST'])
@limiter.limit("5 per minute")
@route_manager.monitor(
    route='/add_client',
    required_params={
        'POST': {
            'name': str,
            'email': str
        }
    },
    description="Add a new client"
)
def add_client():
    """Add a new client"""
    conn = None
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        renewal_date = request.form.get('renewal_date')
        force_add = request.form.get('force_add') == 'true'
        
        logger.info(f"Attempting to add client - Name: {name}, Email: {email}, Phone: {phone}, Renewal: {renewal_date}")
        
        # Validate required fields
        if not name or not name.strip():
            flash('Client name is required', 'danger')
            return redirect(url_for('index'))
            
        if not email or not email.strip():
            flash('Email is required', 'danger')
            return redirect(url_for('index'))
        
        # Validate email format
        if not validate_email(email):
            flash('Invalid email format', 'danger')
            return redirect(url_for('index'))
        
        # Clean and validate phone number if provided
        if phone:
            phone = phone.strip()
            if not re.match(r'^\+?1?\d{9,15}$', phone):
                flash('Invalid phone number format. Please use numbers only, optionally with country code.', 'danger')
                return redirect(url_for('index'))
        
        # Validate renewal date if provided
        if renewal_date:
            try:
                # Ensure the date is in YYYY-MM-DD format
                renewal_date = datetime.strptime(renewal_date, '%Y-%m-%d').date()
            except ValueError as e:
                logger.error(f"Date parsing error: {e}")
                flash('Invalid renewal date format. Please use YYYY-MM-DD format.', 'danger')
                return redirect(url_for('index'))
        
        conn = check_db_connection()  # Use the connection checker instead
        cur = conn.cursor()
        
        # Check if email already exists
        cur.execute('SELECT id FROM clients WHERE email = %s', (email,))
        if cur.fetchone() and not force_add:
            flash('Email already exists', 'danger')
            return redirect(url_for('index'))
        
        # Insert new client
        try:
            logger.info("Executing client insert query...")
            cur.execute(
                'INSERT INTO clients (name, email, phone, renewal_date) VALUES (%s, %s, %s, %s) RETURNING id',
                (name.strip(), email.strip(), phone, renewal_date)
            )
            new_client_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"Successfully added client with ID: {new_client_id}")
            flash(f'Client {name} added successfully', 'success')
            
        except psycopg2.IntegrityError as e:
            conn.rollback()
            logger.error(f"Database integrity error: {e}")
            if 'unique constraint' in str(e).lower():
                flash('A client with this email already exists', 'danger')
            else:
                flash('Error adding client: database constraint violation', 'danger')
            return redirect(url_for('index'))
            
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Database error adding client: {e}")
            flash('Error adding client: database error', 'danger')
            return redirect(url_for('index'))
            
    except Exception as e:
        logger.error(f"Unexpected error adding client: {e}", exc_info=True)
        flash(f'Error adding client: {str(e)}', 'danger')
        if conn:
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()
    
    return redirect(url_for('index'))

@app.route('/link_client', methods=['POST'])
@limiter.limit("5 per minute")
@route_manager.monitor(
    route='/link_client',
    required_params={
        'POST': {
            'client_id': str,
            'account_id': str
        }
    },
    description="Link a client to an account"
)
def link_client():
    """Link a client to an account"""
    conn = None
    try:
        client_id = request.form.get('client_id')
        account_id = request.form.get('account_id')
        
        if not client_id or not account_id:
            flash('Client and account are required', 'danger')
            return redirect(url_for('index'))
        
        conn = get_db()
        cur = conn.cursor()
        
        # Check if account already has 5 clients
        cur.execute('''
            SELECT COUNT(*) FROM client_accounts 
            WHERE account_id = %s
        ''', (account_id,))
        client_count = cur.fetchone()[0]
        
        if client_count >= 5:
            flash('Account already has maximum number of clients (5)', 'danger')
            return redirect(url_for('index'))
        
        # Check if client is already linked to this account
        cur.execute('''
            SELECT id FROM client_accounts 
            WHERE client_id = %s AND account_id = %s
        ''', (client_id, account_id))
        if cur.fetchone():
            flash('Client is already linked to this account', 'danger')
            return redirect(url_for('index'))
        
        # Link client to account
        cur.execute(
            'INSERT INTO client_accounts (client_id, account_id) VALUES (%s, %s)',
            (client_id, account_id)
        )
        conn.commit()
        flash('Client linked successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error linking client: {e}")
        flash('Error linking client', 'danger')
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()
    
    return redirect(url_for('index'))

@app.route('/unlink_client', methods=['POST'])
@limiter.limit("5 per minute")
@route_manager.monitor(
    route='/unlink_client',
    required_params={
        'POST': {
            'client_id': str,
            'account_id': str
        }
    },
    description="Unlink a client from an account"
)
def unlink_client():
    """Unlink a client from an account"""
    conn = None
    try:
        client_id = request.form.get('client_id')
        account_id = request.form.get('account_id')
        
        if not client_id or not account_id:
            flash('Client and account are required', 'danger')
            return redirect(url_for('index'))
        
        conn = get_db()
        cur = conn.cursor()
        
        # Unlink client from account
        cur.execute('''
            DELETE FROM client_accounts 
            WHERE client_id = %s AND account_id = %s
        ''', (client_id, account_id))
        
        if cur.rowcount == 0:
            flash('Client is not linked to this account', 'danger')
        else:
            conn.commit()
            flash('Client unlinked successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error unlinking client: {e}")
        flash('Error unlinking client', 'danger')
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()
    
    return redirect(url_for('index'))

@app.route('/account_clients/<int:account_id>')
@route_manager.monitor(
    route='/account_clients/<int:account_id>',
    description="Get all clients linked to an account"
)
def get_account_clients(account_id):
    """Get all clients linked to an account"""
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # First check if the account exists
        cur.execute('SELECT id FROM accounts WHERE id = %s', (account_id,))
        if not cur.fetchone():
            return {'error': 'Account not found'}, 404
        
        # Get all clients linked to this account
        cur.execute('''
            SELECT c.id, c.name, c.email, c.phone, c.renewal_date
            FROM clients c
            JOIN client_accounts ca ON c.id = ca.client_id
            WHERE ca.account_id = %s
            ORDER BY c.name
        ''', (account_id,))
        
        clients = []
        for row in cur.fetchall():
            clients.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'renewal_date': row[4].strftime('%Y-%m-%d') if row[4] else None
            })
        
        return {'clients': clients}
        
    except Exception as e:
        logger.error(f"Error fetching account clients: {e}")
        return {'error': str(e)}, 500
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()

@app.route('/renew_client', methods=['POST'])
@limiter.limit("5 per minute")
@route_manager.monitor(
    route='/renew_client',
    required_params={
        'POST': {
            'client_id': str,
            'renewal_date': str
        }
    },
    description="Renew a client's account"
)
def renew_client():
    """Renew a client's account"""
    conn = None
    try:
        # Try to get data from both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        client_id = data.get('client_id')
        renewal_date = data.get('renewal_date')
        
        # Validate required parameters
        if not client_id:
            error_msg = 'Client ID is required'
            logger.error(f"Renew client error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        if not renewal_date:
            error_msg = 'Renewal date is required'
            logger.error(f"Renew client error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        # Convert client_id to integer
        try:
            client_id = int(client_id)
        except ValueError:
            error_msg = 'Invalid client ID format'
            logger.error(f"Renew client error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        # Validate renewal date format
        try:
            # Parse and format the date to ensure it's valid
            parsed_date = datetime.strptime(renewal_date, '%Y-%m-%d').date()
            formatted_date = parsed_date.strftime('%Y-%m-%d')
        except ValueError as e:
            error_msg = 'Invalid date format. Please use YYYY-MM-DD'
            logger.error(f"Renew client error: {error_msg} - {str(e)}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        conn = check_db_connection()
        cur = conn.cursor()
        
        # First check if client exists
        cur.execute('SELECT id FROM clients WHERE id = %s', (client_id,))
        if not cur.fetchone():
            error_msg = 'Client not found'
            logger.error(f"Renew client error: {error_msg} - ID: {client_id}")
            return jsonify({'success': False, 'error': error_msg}), 404
        
        # Update client's renewal date
        cur.execute('''
            UPDATE clients 
            SET renewal_date = %s, 
                updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s
            RETURNING id, name, renewal_date
        ''', (formatted_date, client_id))
        
        updated = cur.fetchone()
        conn.commit()
        
        if updated:
            logger.info(f"Successfully renewed client {updated[1]} (ID: {updated[0]}) to {updated[2]}")
            return jsonify({
                'success': True,
                'message': 'Renewal date updated successfully',
                'client_id': updated[0],
                'renewal_date': formatted_date
            })
        else:
            error_msg = 'Failed to update renewal date'
            logger.error(f"Renew client error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except psycopg2.Error as e:
        error_msg = f"Database error: {str(e)}"
        logger.error(f"Renew client database error: {error_msg}")
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': error_msg}), 500
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Renew client error: {error_msg}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': error_msg}), 500
        
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()

@app.route('/delete_account', methods=['POST'])
@limiter.limit("5 per minute")
@route_manager.monitor(
    route='/delete_account',
    required_params={
        'POST': {
            'account_id': str
        }
    },
    description="Delete an account and all its client associations"
)
def delete_account():
    """Delete an account and all its client associations"""
    conn = None
    try:
        account_id = request.form.get('account_id')
        
        if not account_id:
            flash('Account ID is required', 'danger')
            return redirect(url_for('index'))
        
        conn = get_db()
        cur = conn.cursor()
        
        # Delete the account (client_accounts will be deleted automatically due to ON DELETE CASCADE)
        cur.execute('DELETE FROM accounts WHERE id = %s', (account_id,))
        
        if cur.rowcount == 0:
            flash('Account not found', 'danger')
        else:
            conn.commit()
            flash('Account deleted successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        flash('Error deleting account', 'danger')
        if conn:
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()
    
    return redirect(url_for('index'))

@app.route('/clients')
@route_manager.monitor(
    route='/clients',
    description="Get list of all clients"
)
def get_clients():
    """Get list of all clients"""
    # Check if JSON response is requested
    want_json = (
        request.headers.get('Accept', '').find('application/json') != -1 or
        request.args.get('format') == 'json'
    )

    conn = None
    try:
        conn = check_db_connection()
        cur = conn.cursor()
        
        # Get all clients with their account counts
        cur.execute('''
            SELECT 
                c.id, 
                c.name, 
                c.email, 
                COALESCE(c.phone, 'N/A') as phone,
                COALESCE(to_char(c.renewal_date, 'YYYY-MM-DD'), 'N/A') as renewal_date,
                COALESCE(to_char(c.next_renewal_date, 'YYYY-MM-DD'), 'N/A') as next_renewal_date,
                COALESCE(to_char(c.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS'), 'N/A') as created_at,
                COUNT(ca.account_id) as account_count
            FROM clients c
            LEFT JOIN client_accounts ca ON c.id = ca.client_id
            GROUP BY 
                c.id, 
                c.name, 
                c.email, 
                c.phone, 
                c.renewal_date,
                c.next_renewal_date,
                c.created_at
            ORDER BY c.name
        ''')
        clients = cur.fetchall()
        
        # Format the results
        formatted_clients = []
        for client in clients:
            formatted_clients.append({
                'id': client[0],
                'name': client[1],
                'email': client[2],
                'phone': client[3],
                'renewal_date': client[4],
                'next_renewal_date': client[5],
                'created_at': client[6],
                'account_count': client[7]
            })
        
        if want_json:
            return jsonify({
                'status': 'success',
                'clients': formatted_clients
            })
        else:
            return render_template('clients.html', clients=formatted_clients, initial_data={
                'status': 'success',
                'clients': formatted_clients
            })
        
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection error in get_clients: {e}")
        health_checker.check_database(force=True)  # Force health check update
        if want_json:
            return jsonify({
                'status': 'error',
                'message': 'Database connection error',
                'error': str(e)
            }), 503
        else:
            flash('Database connection error. Please try again later.', 'danger')
            return render_template('clients.html', clients=[], db_error=True)
            
    except psycopg2.Error as e:
        logger.error(f"Database error in get_clients: {e}")
        if want_json:
            return jsonify({
                'status': 'error',
                'message': 'Database error',
                'error': str(e)
            }), 500
        else:
            flash('Database error. Please try again later.', 'danger')
            return render_template('clients.html', clients=[])
            
    except Exception as e:
        logger.error(f"Unexpected error in get_clients: {e}", exc_info=True)
        if want_json:
            return jsonify({
                'status': 'error',
                'message': 'Error fetching clients',
                'error': str(e)
            }), 500
        else:
            flash('Error fetching clients: ' + str(e), 'danger')
            return render_template('clients.html', clients=[])
    finally:
        if 'cur' in locals():
            try:
                cur.close()
            except Exception as e:
                logger.error(f"Error closing cursor: {e}")
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

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

@app.errorhandler(psycopg2.OperationalError)
def handle_db_error(error):
    """Handle database connection errors"""
    logger.error(f"Database error: {error}")
    db_status = health_checker.check_database(force=True)
    
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

if __name__ == '__main__':
    # Initialize database and check health before starting
    try:
        init_db()
        with app.app_context():
            initial_health = health_checker.check_application()
            if initial_health['status'] != 'healthy':
                logger.warning("Application started with unhealthy status")
                logger.warning(f"Health check results: {initial_health}")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    try:
        app.run(debug=True)
    finally:
        DatabasePool.close_pool()  # Close all connections when the app stops 