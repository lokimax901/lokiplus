import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, current_app
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RouteManager:
    def __init__(self):
        self.routes = {}
        self.start_time = datetime.now()

    def monitor(self, route=None, required_params=None, description=None):
        """Decorator to monitor route performance and validate parameters"""
        def decorator(f):
            # Register the route
            endpoint = route or f.__name__
            self.routes[endpoint] = {
                'description': description or f.__doc__ or 'No description',
                'required_params': required_params or {},
                'status': 'healthy',
                'last_check': None,
                'total_calls': 0,
                'failed_calls': 0,
                'avg_response_time': 0
            }

            @wraps(f)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    # Validate required parameters
                    if required_params and request.method in required_params:
                        # Get parameters from appropriate source
                        if request.is_json:
                            params = request.get_json()
                        elif request.method == 'POST':
                            params = request.form
                        else:
                            params = request.args
                            
                        # Handle case where params might be None
                        params = params or {}
                        
                        # Validate each required parameter
                        for param, param_type in required_params[request.method].items():
                            if param not in params:
                                raise ValueError(f"Missing required parameter: {param}")
                            
                            # Get the value and validate type if needed
                            value = params[param]
                            if value is None:
                                raise ValueError(f"Parameter {param} cannot be null")
                            
                            # Special handling for certain types
                            if param_type == int:
                                try:
                                    int(value)
                                except (TypeError, ValueError):
                                    raise ValueError(f"Parameter {param} must be an integer")
                            elif param_type == float:
                                try:
                                    float(value)
                                except (TypeError, ValueError):
                                    raise ValueError(f"Parameter {param} must be a number")
                            elif param_type == bool:
                                if not isinstance(value, bool) and str(value).lower() not in ['true', 'false', '0', '1']:
                                    raise ValueError(f"Parameter {param} must be a boolean")
                            
                    result = f(*args, **kwargs)
                    
                    # Update statistics
                    self.routes[endpoint]['total_calls'] += 1
                    response_time = time.time() - start_time
                    avg_time = self.routes[endpoint]['avg_response_time']
                    self.routes[endpoint]['avg_response_time'] = (
                        (avg_time * (self.routes[endpoint]['total_calls'] - 1) + response_time) /
                        self.routes[endpoint]['total_calls']
                    )
                    self.routes[endpoint]['status'] = 'healthy'
                    self.routes[endpoint]['last_check'] = datetime.now()
                    
                    return result
                    
                except Exception as e:
                    # Update error statistics
                    self.routes[endpoint]['failed_calls'] += 1
                    self.routes[endpoint]['status'] = 'unhealthy'
                    self.routes[endpoint]['last_error'] = str(e)
                    self.routes[endpoint]['last_check'] = datetime.now()
                    logger.error(f"Route {endpoint} failed: {e}")
                    raise
                    
            return wrapper
        return decorator

    def generate_report(self):
        """Generate a report of all routes and their health status"""
        try:
            total_routes = len(self.routes)
            healthy_routes = sum(1 for r in self.routes.values() if r['status'] == 'healthy')
            
            return {
                'status': 'healthy' if healthy_routes == total_routes else 'degraded',
                'total': total_routes,
                'healthy': healthy_routes,
                'routes': self.routes
            }
        except Exception as e:
            logger.error(f"Error generating route report: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'total': 0,
                'healthy': 0,
                'routes': {}
            }

# Create a global instance
route_manager = RouteManager() 