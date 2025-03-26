import multiprocessing
import os

# Bind to 0.0.0.0:$PORT for Render compatibility
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increased timeout for slow startups
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "debug"  # Increased logging level for debugging
capture_output = True
enable_stdio_inheritance = True

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Startup
preload_app = True
reload = False  # Disable auto-reload in production 