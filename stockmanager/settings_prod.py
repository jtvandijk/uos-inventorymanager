from .settings import *

# SECURITY
DEBUG = False

ALLOWED_HOSTS = ["178.79.153.239"]

# STATIC FILES (required for production)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "/static/"

# Extra security (safe defaults)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True