import psycopg2
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, supabase
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_postgres_connection():
    """Get a connection to the PostgreSQL database."""
    try:
        return psycopg2.connect(Config.get_db_connection_string())
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        raise

def migrate_accounts():
    """Migrate accounts from PostgreSQL to Supabase."""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    try:
        # Get all accounts from PostgreSQL
        cur.execute("SELECT id, email, password, created_at, updated_at FROM accounts")
        accounts = cur.fetchall()
        
        # Insert accounts into Supabase
        for account in accounts:
            data = {
                'id': account[0],  # Keep the same ID
                'email': account[1],
                'password': account[2],
                'created_at': account[3].isoformat() if account[3] else datetime.utcnow().isoformat(),
                'updated_at': account[4].isoformat() if account[4] else datetime.utcnow().isoformat()
            }
            try:
                supabase.table('accounts').insert(data).execute()
                logger.info(f"Migrated account: {account[1]}")
            except Exception as e:
                logger.error(f"Error migrating account {account[1]}: {e}")
        
        conn.commit()
        logger.info(f"Successfully migrated {len(accounts)} accounts")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in account migration: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def migrate_clients():
    """Migrate clients from PostgreSQL to Supabase."""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    try:
        # Get all clients from PostgreSQL
        cur.execute("""
            SELECT id, email, password, status, renewal_date, 
                   next_renewal_date, created_at, updated_at 
            FROM clients
        """)
        clients = cur.fetchall()
        
        # Insert clients into Supabase
        for client in clients:
            data = {
                'id': client[0],  # Keep the same ID
                'email': client[1],
                'password': client[2],
                'status': client[3],
                'renewal_date': client[4].isoformat() if client[4] else None,
                'next_renewal_date': client[5].isoformat() if client[5] else None,
                'created_at': client[6].isoformat() if client[6] else datetime.utcnow().isoformat(),
                'updated_at': client[7].isoformat() if client[7] else datetime.utcnow().isoformat()
            }
            try:
                supabase.table('clients').insert(data).execute()
                logger.info(f"Migrated client: {client[1]}")
            except Exception as e:
                logger.error(f"Error migrating client {client[1]}: {e}")
        
        conn.commit()
        logger.info(f"Successfully migrated {len(clients)} clients")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in client migration: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def migrate_account_clients():
    """Migrate account-client relationships from PostgreSQL to Supabase."""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    try:
        # Get all account-client relationships from PostgreSQL
        cur.execute("""
            SELECT id, account_id, client_id, created_at 
            FROM client_accounts
        """)
        relationships = cur.fetchall()
        
        # Insert relationships into Supabase
        for rel in relationships:
            data = {
                'id': rel[0],  # Keep the same ID
                'account_id': rel[1],
                'client_id': rel[2],
                'created_at': rel[3].isoformat() if rel[3] else datetime.utcnow().isoformat()
            }
            try:
                supabase.table('account_clients').insert(data).execute()
                logger.info(f"Migrated relationship: Account {rel[1]} - Client {rel[2]}")
            except Exception as e:
                logger.error(f"Error migrating relationship Account {rel[1]} - Client {rel[2]}: {e}")
        
        conn.commit()
        logger.info(f"Successfully migrated {len(relationships)} account-client relationships")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in relationship migration: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def main():
    """Main migration function."""
    try:
        logger.info("Starting migration to Supabase...")
        
        # Migrate in order of dependencies
        migrate_accounts()
        migrate_clients()
        migrate_account_clients()
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    main() 