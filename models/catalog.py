# models/catalog.py
from __future__ import annotations
from typing import TypedDict, List

class CourseItem(TypedDict):
    id: str
    title: str
    price_twd: int
    desc: str
    badge: str

__all__ = ["COURSE_CATALOG"]

COURSE_CATALOG: List[CourseItem] = [
    {
        "id": "course_py_basic",
        "title": "Python 入門：從零到能寫",
        "price_twd": 990,
        "desc": "變數、if/for、函式、模組；實作迷你專案。",
        "badge": "新手友善",
    },
    {
        "id": "course_flask_web",
        "title": "Flask 網站實戰",
        "price_twd": 1490,
        "desc": "Blueprint、Jinja、部署；打造可上線的小網站。",
        "badge": "實戰",
    },
    {
        "id": "course_speech_ai",
        "title": "語音轉錄與摘要：從 Whisper 到報告",
        "price_twd": 1990,
        "desc": "上傳音檔→轉寫→摘要→Docx 報告自動生成。",
        "badge": "進階",
    },
]
