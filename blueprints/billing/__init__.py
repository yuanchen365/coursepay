# blueprints/billing/__init__.py
from flask import Blueprint
bp = Blueprint("billing", __name__, url_prefix="/billing")

from . import routes  # noqa: E402 讓路由生效
