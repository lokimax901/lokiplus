import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class Config:
    """Application configuration."""
    DB_CONFIG = {
        'database': 'postgres',
        'user': 'postgres',
        'password': '%lYXB2QTupE',
        'host': 'db.nusligglyvgsmuvauyce.supabase.co',
        'port': 5432
    }
    
    # Flask configuration
    DEBUG = True
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"
    
    # Health check configuration
    HEALTH_CHECK_CACHE_TIMEOUT = 300  # 5 minutes
    
    # Logging configuration
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    @classmethod
    def get_db_connection_string(cls):
        """Returns the database connection string"""
        return f"postgresql://{cls.DB_CONFIG['user']}:{cls.DB_CONFIG['password']}@{cls.DB_CONFIG['host']}:{cls.DB_CONFIG['port']}/{cls.DB_CONFIG['database']}" 