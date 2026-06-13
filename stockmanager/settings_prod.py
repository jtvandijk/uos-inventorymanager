from .settings import *

# SECURITY
DEBUG = False

ALLOWED_HOSTS = ["178.79.153.239", "127.0.0.1", "localhost"]

# STATIC FILES (required for production)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "/inventory/static/"

# Extra security (safe defaults)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Nginx
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'http')