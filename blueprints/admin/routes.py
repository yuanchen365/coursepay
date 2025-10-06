# blueprints/admin/routes.py
from __future__ import annotations

from flask import jsonify, request, render_template
from . import bp

from services.db import get_session
from services.models import Payment
from sqlalchemy import desc, and_
from datetime import datetime, timedelta


@bp.get("/ping")
def ping():
    return jsonify({"module": "admin", "ok": True})


@bp.get("/payments")
def payments_list():
    """
    付款清單（只讀）+ 搜尋 / 日期篩選 / 分頁
    參數：
      - q: 同時模糊比對 course_id / buyer_email
      - date_from: YYYY-MM-DD（含當日 00:00）
      - date_to:   YYYY-MM-DD（含當日 23:59）
      - page: 頁碼（>=1）
      - page_size: 每頁筆數（1~100）
    """
    # --- 讀取查詢參數 ---
    q = (request.args.get("q") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()

    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1

    try:
        page_size = int(request.args.get("page_size", 20))
        page_size = min(max(page_size, 1), 100)
    except ValueError:
        page_size = 20

    offset = (page - 1) * page_size

    # --- 組合查詢 ---
    with get_session() as s:
        query = s.query(Payment)

        # 文字搜尋：course_id / buyer_email
        if q:
            like = f"%{q}%"
            query = query.filter(
                (Payment.course_id.ilike(like)) | (Payment.buyer_email.ilike(like))
            )

        # 日期範圍（含當日）
        conds = []
        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                conds.append(Payment.created_at >= dt_from)
            except ValueError:
                pass
        if date_to:
            try:
                # 讓 date_to 含當日：+1 天再用 < 上界
                dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                conds.append(Payment.created_at < dt_to)
            except ValueError:
                pass
        if conds:
            query = query.filter(and_(*conds))

        query = query.order_by(desc(Payment.created_at))
        total = query.count()
        rows = query.offset(offset).limit(page_size).all()

    # --- 分頁資訊 ---
    has_prev = page > 1
    has_next = (offset + len(rows)) < total

    return render_template(
        "admin_payments.html",
        rows=rows,
        page=page,
        page_size=page_size,
        total=total,
        has_prev=has_prev,
        has_next=has_next,
        # 把查詢參數回傳給模板，維持表單值 & 分頁串接
        q=q,
        date_from=date_from,
        date_to=date_to,
    )
