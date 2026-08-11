# Dans app/main.py

from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.audit import AuditMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.validation import Validators

# Ajouter les middlewares (ordre important)
app.add_middleware(RateLimitMiddleware)  # Le premier
app.add_middleware(CSRFMiddleware)
app.add_middleware(AuditMiddleware)  # Le dernier
