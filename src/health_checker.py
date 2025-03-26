import logging
import psycopg2
from datetime import datetime, timedelta
from config import Config
from route_manager import route_manager

logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self):
        self.db_status = {
            'status': 'unknown',
            'last_check': None,
            'error': None,
            'connection_time': None,
            'tables': {}
        }
        self.cache_duration = timedelta(minutes=5)  # Cache health check results for 5 minutes
        self.start_time = datetime.now()  # Track application start time

    def check_database(self, force=False):
        """Check database connectivity and table status"""
        # Return cached result if available and not forced
        if not force and self.db_status['last_check']:
            if datetime.now() - self.db_status['last_check'] < self.cache_duration:
                return self.db_status

        start_time = datetime.now()
        conn = None
        try:
            # Test database connection
            conn = psycopg2.connect(**Config.DB_CONFIG)
            cur = conn.cursor()

            # Quick connection test
            cur.execute('SELECT 1')
            
            # Update status with basic info first
            self.db_status = {
                'status': 'healthy',
                'last_check': datetime.now(),
                'error': None,
                'connection_time': (datetime.now() - start_time).total_seconds(),
                'latency': (datetime.now() - start_time).total_seconds() * 1000  # in milliseconds
            }

            # Only do detailed checks if forced or cache expired
            if force or not self.db_status['last_check']:
                # Check if all required tables exist and their row counts
                tables_to_check = ['clients', 'accounts', 'client_accounts']
                tables_status = {}

                for table in tables_to_check:
                    # Check if table exists
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                        )
                    """, (table,))
                    exists = cur.fetchone()[0]

                    if exists:
                        # Get row count
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        row_count = cur.fetchone()[0]
                        
                        tables_status[table] = {
                            'exists': True,
                            'row_count': row_count
                        }
                    else:
                        tables_status[table] = {
                            'exists': False,
                            'error': f"Table '{table}' does not exist"
                        }

                self.db_status['tables'] = tables_status

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Database health check failed: {error_msg}")
            self.db_status = {
                'status': 'unhealthy',
                'last_check': datetime.now(),
                'error': error_msg,
                'connection_time': (datetime.now() - start_time).total_seconds() if start_time else None,
                'latency': None
            }
        finally:
            if 'cur' in locals():
                cur.close()
            if conn:
                conn.close()

        return self.db_status

    def check_application(self):
        """Check overall application health including routes and database"""
        try:
            # Get basic database status without detailed checks
            db_status = self.check_database(force=False)
            
            # Calculate uptime
            uptime = datetime.now() - self.start_time
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            
            return {
                'status': db_status['status'],
                'uptime': uptime_str,
                'database_latency': db_status.get('latency', 'N/A'),
                'error': db_status.get('error')
            }
        except Exception as e:
            logger.error(f"Application health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'uptime': 'N/A',
                'database_latency': 'N/A'
            }

    def get_recommendations(self):
        """Get recommendations for improving application health"""
        recommendations = []
        db_status = self.check_database()

        # Database recommendations
        if db_status['status'] == 'healthy':
            for table_name, table_info in db_status['tables'].items():
                if table_info['exists']:
                    # Check for missing indexes on foreign keys
                    if table_name == 'client_accounts':
                        has_client_id_index = any('client_id' in idx['definition'] 
                                                for idx in table_info['indexes'])
                        has_account_id_index = any('account_id' in idx['definition'] 
                                                 for idx in table_info['indexes'])
                        
                        if not has_client_id_index:
                            recommendations.append({
                                'type': 'index',
                                'priority': 'high',
                                'message': f"Add index on {table_name}.client_id for better query performance"
                            })
                        if not has_account_id_index:
                            recommendations.append({
                                'type': 'index',
                                'priority': 'high',
                                'message': f"Add index on {table_name}.account_id for better query performance"
                            })

                    # Check for large tables that might need archiving
                    row_count = table_info['row_count']
                    if row_count > 1000000:  # 1 million rows
                        recommendations.append({
                            'type': 'performance',
                            'priority': 'medium',
                            'message': f"Consider archiving old data from {table_name} ({row_count:,} rows)"
                        })

        # Route recommendations
        route_status = route_manager.generate_report()
        for route in route_status.get('routes', []):
            stats = route.get('stats', {})
            error_rate = (stats.get('failed_calls', 0) / stats.get('total_calls', 1)) * 100
            if error_rate > 5:  # More than 5% error rate
                recommendations.append({
                    'type': 'reliability',
                    'priority': 'high',
                    'message': f"High error rate ({error_rate:.1f}%) on route {route['endpoint']}"
                })

        return recommendations

# Create a global instance
health_checker = HealthChecker() 