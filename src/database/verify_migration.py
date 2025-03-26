import psycopg2
from config import Config, supabase
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

def verify_accounts():
    """Verify that all accounts were migrated correctly."""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    try:
        # Get counts from both databases
        cur.execute("SELECT COUNT(*) FROM accounts")
        pg_count = cur.fetchone()[0]
        
        supabase_count = len(supabase.table('accounts').select('id').execute().data)
        
        logger.info(f"PostgreSQL accounts: {pg_count}")
        logger.info(f"Supabase accounts: {supabase_count}")
        
        if pg_count != supabase_count:
            logger.warning("Account counts do not match!")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error verifying accounts: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def verify_clients():
    """Verify that all clients were migrated correctly."""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    try:
        # Get counts from both databases
        cur.execute("SELECT COUNT(*) FROM clients")
        pg_count = cur.fetchone()[0]
        
        supabase_count = len(supabase.table('clients').select('id').execute().data)
        
        logger.info(f"PostgreSQL clients: {pg_count}")
        logger.info(f"Supabase clients: {supabase_count}")
        
        if pg_count != supabase_count:
            logger.warning("Client counts do not match!")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error verifying clients: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def verify_account_clients():
    """Verify that all account-client relationships were migrated correctly."""
    conn = get_postgres_connection()
    cur = conn.cursor()
    
    try:
        # Get counts from both databases
        cur.execute("SELECT COUNT(*) FROM client_accounts")
        pg_count = cur.fetchone()[0]
        
        supabase_count = len(supabase.table('account_clients').select('id').execute().data)
        
        logger.info(f"PostgreSQL relationships: {pg_count}")
        logger.info(f"Supabase relationships: {supabase_count}")
        
        if pg_count != supabase_count:
            logger.warning("Relationship counts do not match!")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error verifying relationships: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def main():
    """Main verification function."""
    try:
        logger.info("Starting migration verification...")
        
        accounts_ok = verify_accounts()
        clients_ok = verify_clients()
        relationships_ok = verify_account_clients()
        
        if accounts_ok and clients_ok and relationships_ok:
            logger.info("All verifications passed successfully!")
        else:
            logger.warning("Some verifications failed. Please check the logs for details.")
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise

if __name__ == "__main__":
    main() 