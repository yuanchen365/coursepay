# app.py
from flask import Flask, render_template, current_app, request
from config import Config
from models import catalog  # catalog.COURSE_CATALOG

# DB / Login
from services.db import init_db, create_all, get_session
from services.models import User
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.login_view = "auth.login"  # type: ignore[assignment]


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ---- 初始化資料庫（用 get + 預設，避免 KeyError）----
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///coursepay.db")
    init_db(db_uri, echo=app.config.get("SQLALCHEMY_ECHO", False))
    create_all()

    # ---- 初始化 Flask-Login ----
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None
        with get_session() as s:
            return s.get(User, uid)

    # ---- 藍圖註冊 ----
    from blueprints.auth import bp as auth_bp
    from blueprints.billing import bp as billing_bp
    from blueprints.speech import bp as speech_bp
    from blueprints.admin import bp as admin_bp
    app.register_blueprint(admin_bp)


    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(billing_bp, url_prefix="/billing")
    app.register_blueprint(speech_bp, url_prefix="/speech")

    # ---- 頁面與健康檢查 ----
    @app.get("/")
    def index():
        return render_template("index.html")
    
    @app.get("/courses")
    def courses():
        # 1) 取用課程清單並正規化成 list
        items = getattr(catalog, "COURSE_CATALOG", [])
        if isinstance(items, dict):
            items = list(items.values())
        elif not isinstance(items, (list, tuple)):
            items = []

        # 2) 若指定 fallback=1，就「直接」渲染備援頁（不要 raise）
        if request.args.get("fallback") == "1":
            return render_template(
                "courses_fallback.html",
                items=items,
                error="(測試) 強制顯示備援頁"
            ), 500

        # 3) 正常情況：嘗試渲染主頁，失敗才回備援頁
        try:
            return render_template("courses.html", items=items)
        except Exception as e:
            current_app.logger.exception("Render courses failed")
            return render_template("courses_fallback.html", items=items, error=str(e)), 500



    # 直接渲染備援頁的測試路由
    @app.get("/debug/courses_fallback")
    def debug_courses_fallback():
        items = getattr(catalog, "COURSE_CATALOG", [])
        if isinstance(items, dict):
            items = list(items.values())
        elif not isinstance(items, (list, tuple)):
            items = []
        return render_template(
            "courses_fallback.html",
            items=items,
            error="(測試) 這是手動顯示的備援頁"
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/debug/keys")
    def debug_keys():
        return {
            "has_SECRET_KEY": bool(app.config.get("SECRET_KEY")),
            "has_STRIPE_API_KEY": bool(app.config.get("STRIPE_API_KEY")),
            "has_STRIPE_WEBHOOK_SECRET": bool(app.config.get("STRIPE_WEBHOOK_SECRET")),
            "database_url": app.config.get("SQLALCHEMY_DATABASE_URI", "N/A"),
        }

    return app


# 方便 flask run
app = create_app()
