import psycopg2
from psycopg2 import pool
from config import Config
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from config import supabase

logger = logging.getLogger(__name__)

class DatabasePool:
    _pool = None
    
    @classmethod
    def get_pool(cls):
        """Get or create a connection pool"""
        if cls._pool is None:
            try:
                cls._pool = pool.SimpleConnectionPool(
                    1,  # minconn
                    20, # maxconn
                    Config.get_db_connection_string()
                )
                logger.info("Database connection pool created successfully")
            except Exception as e:
                logger.error(f"Error creating connection pool: {e}")
                raise
        return cls._pool
    
    @classmethod
    def get_connection(cls):
        """Get a connection from the pool"""
        try:
            return cls.get_pool().getconn()
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise
    
    @classmethod
    def return_connection(cls, conn):
        """Return a connection to the pool"""
        if conn:
            try:
                cls.get_pool().putconn(conn)
            except Exception as e:
                logger.error(f"Error returning connection to pool: {e}")
                conn.close()
    
    @classmethod
    def close_pool(cls):
        """Close all connections in the pool"""
        if cls._pool:
            try:
                cls._pool.closeall()
                cls._pool = None
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")

class Database:
    @staticmethod
    def get_accounts() -> List[Dict[str, Any]]:
        """Get all accounts from Supabase."""
        try:
            response = supabase.table('accounts').select('*').execute()
            return response.data
        except Exception as e:
            print(f"Error fetching accounts: {str(e)}")
            return []

    @staticmethod
    def get_clients() -> List[Dict[str, Any]]:
        """Get all clients from Supabase."""
        try:
            response = supabase.table('clients').select('*').execute()
            return response.data
        except Exception as e:
            print(f"Error fetching clients: {str(e)}")
            return []

    @staticmethod
    def add_account(email: str, password: str) -> Optional[Dict[str, Any]]:
        """Add a new account to Supabase."""
        try:
            data = {
                'email': email,
                'password': password,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            response = supabase.table('accounts').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error adding account: {str(e)}")
            return None

    @staticmethod
    def add_client(email: str, password: str, renewal_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Add a new client to Supabase."""
        try:
            data = {
                'email': email,
                'password': password,
                'renewal_date': renewal_date,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            response = supabase.table('clients').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error adding client: {str(e)}")
            return None

    @staticmethod
    def update_client_status(client_id: int, status: str) -> bool:
        """Update client status in Supabase."""
        try:
            data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            response = supabase.table('clients').update(data).eq('id', client_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating client status: {str(e)}")
            return False

    @staticmethod
    def link_client_to_account(client_id: int, account_id: int) -> bool:
        """Link a client to an account in Supabase."""
        try:
            data = {
                'client_id': client_id,
                'account_id': account_id,
                'created_at': datetime.utcnow().isoformat()
            }
            response = supabase.table('account_clients').insert(data).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error linking client to account: {str(e)}")
            return False

    @staticmethod
    def unlink_client_from_account(client_id: int, account_id: int) -> bool:
        """Unlink a client from an account in Supabase."""
        try:
            response = supabase.table('account_clients').delete().eq('client_id', client_id).eq('account_id', account_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error unlinking client from account: {str(e)}")
            return False

    @staticmethod
    def get_account_clients(account_id: int) -> List[Dict[str, Any]]:
        """Get all clients linked to an account from Supabase."""
        try:
            response = supabase.table('account_clients').select('clients(*)').eq('account_id', account_id).execute()
            return [item['clients'] for item in response.data]
        except Exception as e:
            print(f"Error fetching account clients: {str(e)}")
            return []

    @staticmethod
    def delete_account(account_id: int) -> bool:
        """Delete an account from Supabase."""
        try:
            # First, unlink all clients
            supabase.table('account_clients').delete().eq('account_id', account_id).execute()
            # Then delete the account
            response = supabase.table('accounts').delete().eq('id', account_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error deleting account: {str(e)}")
            return False

    @staticmethod
    def check_client_exists(email: str) -> bool:
        """Check if a client exists in Supabase."""
        try:
            response = supabase.table('clients').select('id').eq('email', email).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error checking client existence: {str(e)}")
            return False

    @staticmethod
    def get_client_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get a client by email from Supabase."""
        try:
            response = supabase.table('clients').select('*').eq('email', email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching client by email: {str(e)}")
            return None 