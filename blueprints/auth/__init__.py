# blueprints/auth/__init__.py
from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/auth")

# 匯入視圖，確保路由被註冊
from . import views  # noqa: E402,F401
