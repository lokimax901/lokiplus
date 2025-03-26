import os
import sys
import pytest
import psycopg2

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config

# Test configuration
class TestConfig(Config):
    TESTING = True
    DB_CONFIG = {
        'database': 'submax_test',
        'user': Config.DB_CONFIG['user'],
        'password': Config.DB_CONFIG['password'],
        'host': Config.DB_CONFIG['host'],
        'port': Config.DB_CONFIG['port']
    }

@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    from app import app as flask_app
    flask_app.config.from_object(TestConfig)
    return flask_app

@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()

@pytest.fixture
def db():
    """Create a test database and return a connection."""
    # Connect to default database to create test database
    conn = psycopg2.connect(
        dbname='postgres',
        user=TestConfig.DB_CONFIG['user'],
        password=TestConfig.DB_CONFIG['password'],
        host=TestConfig.DB_CONFIG['host'],
        port=TestConfig.DB_CONFIG['port']
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Create test database
    try:
        cur.execute(f"DROP DATABASE IF EXISTS {TestConfig.DB_CONFIG['database']}")
        cur.execute(f"CREATE DATABASE {TestConfig.DB_CONFIG['database']}")
    finally:
        cur.close()
        conn.close()
    
    # Connect to test database and set up schema
    conn = psycopg2.connect(**TestConfig.DB_CONFIG)
    try:
        cur = conn.cursor()
        # Read and execute schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')
        with open(schema_path, 'r') as f:
            cur.execute(f.read())
        conn.commit()
        yield conn
    finally:
        conn.close()

@pytest.fixture
def test_data(db):
    """Insert test data into the database."""
    cur = db.cursor()
    try:
        # Insert test clients
        cur.execute("""
            INSERT INTO clients (name, email, phone, renewal_date)
            VALUES 
                ('Test Client 1', 'test1@example.com', '1234567890', '2024-12-31'),
                ('Test Client 2', 'test2@example.com', '0987654321', '2024-06-30')
            RETURNING id
        """)
        client_ids = [row[0] for row in cur.fetchall()]
        
        # Insert test accounts
        cur.execute("""
            INSERT INTO accounts (email, password, status)
            VALUES 
                ('account1@example.com', 'hashed_password_1', 'active'),
                ('account2@example.com', 'hashed_password_2', 'active')
            RETURNING id
        """)
        account_ids = [row[0] for row in cur.fetchall()]
        
        # Link clients and accounts
        cur.execute("""
            INSERT INTO client_accounts (client_id, account_id)
            VALUES (%s, %s)
        """, (client_ids[0], account_ids[0]))
        
        db.commit()
        
        return {
            'client_ids': client_ids,
            'account_ids': account_ids
        }
    finally:
        cur.close() 