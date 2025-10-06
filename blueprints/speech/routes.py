from flask import jsonify
from . import bp

@bp.get("/ping")
def ping():
    return jsonify({"module": "speech", "ok": True})
