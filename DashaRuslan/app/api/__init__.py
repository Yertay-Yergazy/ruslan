from flask import Blueprint

bp = Blueprint('api', __name__)

from app.api import routes  # noqa

# Exempt API blueprint from CSRF (JSON API, uses session auth only)
from app import csrf
csrf.exempt(bp)
