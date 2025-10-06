# blueprints/billing/routes.py
from __future__ import annotations

import stripe
from flask import jsonify, request, current_app, redirect, url_for, render_template
from jinja2 import TemplateNotFound
from . import bp
from models import catalog

from services.db import get_session
from services.models import Payment, WebhookEvent

# 建議固定 API 版本（若專案有集中設定可移除此行）
stripe.api_version = "2024-10-28.acacia"

# ---- 不直接 from stripe.error 匯入，動態抓取避免 Pylance 報錯 ----
_stripe_error = getattr(stripe, "error", None)
SignatureVerificationError = getattr(_stripe_error, "SignatureVerificationError", Exception)
StripeError = getattr(_stripe_error, "StripeError", Exception)
# -----------------------------------------------------------------------


@bp.get("/ping")
def ping():
    return jsonify({"module": "billing", "ok": True})


# 方便用瀏覽器直接開此網址時得到明確提示（避免 404/405 困惑）
@bp.get("/checkout/create")
def checkout_create_get():
    return "請從 /courses 的『購買』按鈕送出（POST），不要用 GET 開此網址。", 405


# 新增：/checkout GET 的友善提示（避免有人直接 GET）
@bp.get("/checkout", endpoint="checkout_get")
def checkout_get_alias():
    return "請從 /courses 的『購買』按鈕送出（POST），不要用 GET 開此網址。", 405


# /checkout 端點別名，讓 url_for('billing.checkout') 能命中
@bp.post("/checkout/create")
@bp.post("/checkout", endpoint="checkout")
def checkout_create():
    """
    建立 Stripe Checkout Session。
    - 未設定 STRIPE_API_KEY：回 echo JSON（方便先驗表單/路由）
    - 已設定：建立 Checkout Session 並 303 轉導
    """
    course_id = request.form.get("course_id")
    # price_twd 改為非必要；實際金額一律以後端 catalog 為準，避免前端被竄改
    price_twd = request.form.get("price_twd")

    if not course_id:
        return jsonify({"ok": False, "error": "missing course_id"}), 400

    # 驗證課程存在
    items = {c["id"]: c for c in catalog.COURSE_CATALOG}
    course = items.get(course_id)
    if not course:
        return jsonify({"ok": False, "error": "invalid course_id"}), 400

    # 未填金鑰 → 回 echo（確認前端 POST 正常）
    if not current_app.config.get("STRIPE_API_KEY"):
        return jsonify({"ok": True, "echo": {"course_id": course_id, "price_twd": price_twd}})

    # ===== 真正 Stripe 流程 =====
    stripe.api_key = current_app.config["STRIPE_API_KEY"]

    success_url = url_for("billing.checkout_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = url_for("billing.checkout_cancel", _external=True)

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            line_items=[{
                "quantity": 1,
                "price_data": {
                    "currency": "twd",
                    "unit_amount": int(course["price_twd"]) * 100,  # 以 catalog 為準（單位：分）
                    "product_data": {
                        "name": course["title"],
                        "metadata": {"course_id": course_id},
                    },
                },
            }],
            metadata={"course_id": course_id},
        )
    except StripeError as e:  # 先攔 Stripe 相關錯誤
        user_msg = getattr(e, "user_message", None)
        return jsonify({"ok": False, "error": f"stripe error: {user_msg or str(e)}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    # 安全取得 URL
    checkout_url = getattr(session, "url", None)
    if not checkout_url and isinstance(session, dict):
        checkout_url = session.get("url")
    if not checkout_url:
        return jsonify({"ok": False, "error": "Stripe did not return a checkout URL"}), 500

    return redirect(checkout_url, code=303)


@bp.get("/success")
def checkout_success():
    """
    成功頁：若有 session_id 與 STRIPE_API_KEY，就嘗試查詢一次細節；
    任何錯誤都不會 500，最多只顯示簡版訊息。
    重要：實際交易結果仍以 Webhook 入庫為準。
    """
    session_id = request.args.get("session_id")
    summary = None

    if session_id and current_app.config.get("STRIPE_API_KEY"):
        stripe.api_key = current_app.config["STRIPE_API_KEY"]
        try:
            sess = stripe.checkout.Session.retrieve(
                session_id,
                expand=["customer_details", "payment_intent"],
            )
            summary = {
                "session_id": sess.get("id"),
                "status": sess.get("payment_status"),
                "amount_twd": int((sess.get("amount_total") or 0) / 100),
                "email": (sess.get("customer_details") or {}).get("email"),
                "course_id": (sess.get("metadata") or {}).get("course_id"),
            }
        except Exception as e:
            current_app.logger.warning(f"[success] retrieve session failed: {e}")

    try:
        return render_template("billing_success.html", summary=summary, session_id=session_id)
    except TemplateNotFound:
        # 範本缺失時的極簡回應，避免 500
        pretty = (
            f"<p>Session: {summary.get('session_id')}</p>"
            f"<p>Status: {summary.get('status')}</p>"
            f"<p>Amount: NT$ {summary.get('amount_twd')}</p>"
            f"<p>Email: {summary.get('email')}</p>"
            f"<p>Course: {summary.get('course_id')}</p>"
            if summary else
            "<p>已返回網站。實際付款結果以後端 Webhook 入庫為準。</p>"
        )
        return f"<h1>付款成功</h1>{pretty}", 200


@bp.get("/cancel")
def checkout_cancel():
    try:
        return render_template("billing_cancel.html")
    except TemplateNotFound:
        return "<h1>已取消結帳</h1><p>你可以回到課程頁面重新選購。</p>", 200


@bp.post("/webhook")
def webhook():
    """
    Stripe Webhook：驗簽 → 記錄事件（webhook_events）→
    若為 checkout.session.completed，則寫入/更新 payments。
    本地測試方式：
      1) stripe login
      2) stripe listen --forward-to http://localhost:5000/billing/webhook
         取得 whsec_... 貼入 .env 的 STRIPE_WEBHOOK_SECRET
    """
    # --- 讀取必要設定 ---
    secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        # 未設定密鑰，拒絕處理，避免被偽造請求打爆
        return jsonify({"ok": False, "error": "missing STRIPE_WEBHOOK_SECRET"}), 400

    payload = request.data  # 必須是 bytes 原文
    sig_header = request.headers.get("Stripe-Signature", "")

    # --- 驗簽 ---
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=secret,
        )
    except SignatureVerificationError:
        return jsonify({"ok": False, "error": "invalid signature"}), 400
    except StripeError as e:
        return jsonify({"ok": False, "error": f"stripe error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"bad payload: {e}"}), 400

    # --- 通用：將原始事件冪等寫入 webhook_events（便於審計/重放/對帳） ---
    etype = event.get("type", "")
    data_obj = (event.get("data") or {}).get("object") or {}
    eid = event.get("id")

    try:
        with get_session() as s:
            if eid:
                exists = s.query(WebhookEvent).filter_by(event_id=eid).first()
                if not exists:
                    s.add(WebhookEvent(event_id=eid, type=etype, payload=event))
                    s.commit()
    except Exception as e:
        current_app.logger.exception(f"[webhook] save event failed: {e}")
        # 若事件落地失敗，仍回 200 避免 Stripe 持續重試；但把錯誤記錄在 log
        # （若你希望 Stripe 重試，可改回 500）
        return jsonify({"ok": False, "warning": "event log failed but ignored"}), 200

    # --- 針對 checkout.session.completed：寫/更新 payments ---
    if etype == "checkout.session.completed":
        session_id = data_obj.get("id") or ""
        meta = data_obj.get("metadata") or {}
        course_id = meta.get("course_id") or "unknown"
        amount_total = data_obj.get("amount_total")  # 單位：分
        status = data_obj.get("payment_status")      # "paid" / ...
        email = (data_obj.get("customer_details") or {}).get("email")

        try:
            with get_session() as s:
                pay = s.query(Payment).filter_by(stripe_session_id=session_id).first()
                amount_twd = int((amount_total or 0) / 100)  # 轉成「元」

                if not pay:
                    pay = Payment(
                        stripe_session_id=session_id,
                        course_id=course_id,
                        amount_twd=amount_twd,
                        status="paid" if status == "paid" else (status or "unknown"),
                        buyer_email=email,
                    )
                    s.add(pay)
                else:
                    # Stripe 可能重送事件：僅更新狀態，不新增
                    pay.status = "paid" if status == "paid" else (status or pay.status)
                s.commit()

            current_app.logger.info(
                f"[webhook] checkout.completed stored: session={session_id} "
                f"course_id={course_id} amount_twd={int((amount_total or 0)/100)} status={status}"
            )
        except Exception as e:
            current_app.logger.exception(f"[webhook] save payment failed: {e}")
            # 同上：避免 Stripe 無限重試；若你想要重試，改回 500。
            return jsonify({"ok": False, "warning": "payment save failed but ignored"}), 200
    else:
        current_app.logger.info(f"[webhook] received event: {etype}")

    # 正常完成
    return jsonify({"ok": True}), 200

# --- 診斷 1：檢查金鑰是否載入（避免 SECRET 沒讀到 .env） ---
@bp.get("/debug/keys")
def _debug_keys():
    return jsonify({
        "has_STRIPE_API_KEY": bool(current_app.config.get("STRIPE_API_KEY")),
        "has_STRIPE_WEBHOOK_SECRET": bool(current_app.config.get("STRIPE_WEBHOOK_SECRET")),
    })

# --- 診斷 2：自我測試寫入（確認 DB/Model/Session 沒問題） ---
@bp.get("/webhook/selftest")
def _webhook_selftest():
    import uuid, datetime as _dt
    fake_event_id = f"evt_selftest_{uuid.uuid4().hex[:12]}"
    try:
        with get_session() as s:
            # 寫一筆 webhook_events
            s.add(WebhookEvent(
                event_id=fake_event_id,
                type="selftest",
                payload={"hello": "world", "ts": _dt.datetime.utcnow().isoformat()}
            ))
            # 寫一筆 payments
            s.add(Payment(
                stripe_session_id=f"cs_selftest_{uuid.uuid4().hex[:10]}",
                course_id="selftest_course",
                amount_twd=123,
                status="paid",
                buyer_email="test@example.com",
            ))
            s.commit()
    except Exception as e:
        current_app.logger.exception(e)
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "event_id": fake_event_id})
