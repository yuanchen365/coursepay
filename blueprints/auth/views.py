# blueprints/auth/views.py
from flask import jsonify, render_template, request, redirect, url_for, flash
from . import bp

# 新增：存取資料庫與 User 模型
from services.db import get_session
from services.models import User


@bp.get("/health")
def health():
    return jsonify({"ok": True, "module": "auth"})


@bp.route("/register", methods=["GET", "POST"])
def register():
    """最小註冊：email + password → 寫入 users"""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        # 1) 基本檢查
        if not email or not password:
            flash("請輸入 Email 與密碼。", "error")
            return render_template("auth/register.html", email=email)

        # 2) 寫入資料庫（重複信箱檢查）
        with get_session() as s:
            exists = s.query(User).filter_by(email=email).one_or_none()
            if exists:
                flash("此 Email 已註冊。", "error")
                return render_template("auth/register.html", email=email)

            user = User(email=email, plan="free")
            user.set_password(password)  # 以 werkzeug 產生雜湊
            s.add(user)
            s.commit()

        # 3) 暫時導回課程頁（登入頁下一步才會做）
        flash("註冊成功！請稍後建立登入功能後再登入。", "success")
        return redirect(url_for("courses"))

    # GET 顯示表單
    return render_template("auth/register.html")

# 追加在檔案底部
from flask_login import login_user
from werkzeug.security import check_password_hash  # 備用：也可直接用 user.check_password()

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash("請輸入 Email 與密碼。", "error")
            return render_template("auth/login.html", email=email)

        # 找使用者並驗證密碼
        with get_session() as s:
            user = s.query(User).filter_by(email=email).one_or_none()

        if not user or not user.check_password(password):
            flash("帳號或密碼錯誤。", "error")
            return render_template("auth/login.html", email=email)

        # 設為登入狀態
        login_user(user)  # 預設「關閉瀏覽器後登出」，之後可加 remember=True
        flash("登入成功！", "success")
        return redirect(url_for("courses"))

    # GET：顯示登入表單
    return render_template("auth/login.html")
# A-4：登出
from flask_login import logout_user, login_required


# A-4：登出（追加在檔案底部）


@bp.get("/logout")
@login_required
def logout():
    logout_user()
    flash("您已登出。", "success")
    return redirect(url_for("courses"))
