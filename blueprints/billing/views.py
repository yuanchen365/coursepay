# blueprints/billing/views.py
from flask import (
    request, redirect, url_for, flash, jsonify,
    render_template, current_app, abort
)
from flask_login import login_required, current_user
import stripe

from . import bp


# 健康檢查：/billing/ping → {"module":"billing","ok":true}
@bp.get("/ping")
def ping():
    return jsonify({"module": "billing", "ok": True})


# 建立 Stripe Checkout Session（需登入）
@bp.post("/checkout")
@login_required
def checkout():
    course_id = (request.form.get("course_id") or "").strip()
    price_twd_raw = (request.form.get("price_twd") or "").strip()

    if not course_id:
        flash("缺少課程代碼（course_id）。", "error")
        return redirect(url_for("courses"))

    # 價格處理：允許空值；有值時需為整數
    try:
        price_twd = int(price_twd_raw) if price_twd_raw else 0
    except ValueError:
        flash("價格格式錯誤。", "error")
        return redirect(url_for("courses"))

    # 設定 Stripe 金鑰
    stripe.api_key = current_app.config["STRIPE_API_KEY"]

    # 準備建立 Session 參數（避免把 None 傳給 customer_email）
    params: dict = {
        "mode": "payment",
        "line_items": [{
            "quantity": 1,
            "price_data": {
                "currency": "twd",
                "unit_amount": max(price_twd, 0) * 100,  # 以分為單位
                "product_data": {"name": f"Course {course_id}"},
            },
        }],
        "success_url": url_for("billing.success", _external=True) + "?sid={CHECKOUT_SESSION_ID}",
        "cancel_url": url_for("courses", _external=True),
        "metadata": {"user_id": str(current_user.id), "course_id": course_id},
    }
    email = getattr(current_user, "email", None)
    if email:
        params["customer_email"] = email

    try:
        session = stripe.checkout.Session.create(**params)
    except Exception as e:
        flash(f"建立結帳失敗：{e}", "error")
        return redirect(url_for("courses"))

    # 303 轉向到 Stripe Checkout（保險檢查，避免 None）
    checkout_url = getattr(session, "url", None)
    if not checkout_url:
        flash("建立結帳成功，但未取得導向網址，請稍後再試。", "error")
        return redirect(url_for("courses"))
    return redirect(checkout_url, code=303)


# 付款成功頁：以 sid 查詢 Session 並顯示結果
@bp.get("/success")
def success():
    sid = request.args.get("sid") or request.args.get("session_id")
    if not sid:
        return abort(400, "Missing sid")

    stripe.api_key = current_app.config["STRIPE_API_KEY"]
    try:
        session = stripe.checkout.Session.retrieve(
            sid, expand=["payment_intent", "customer_details"]
        )
    except Exception as e:
        return abort(400, f"Stripe error: {e}")

    return render_template("billing/success.html", session=session)
