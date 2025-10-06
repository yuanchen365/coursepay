# services/db.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base"""
    pass


_engine: Optional[Engine] = None
_Session: Optional[sessionmaker] = None


# -----------------------------
# URL & 路徑處理
# -----------------------------
def _to_sqlite_url(db_file: str | Path) -> str:
    """
    將本機檔案路徑轉為 SQLAlchemy 可用的 sqlite URL（使用絕對路徑）。
    例：D:\\foo\\bar.db  -> sqlite:///D:/foo/bar.db
    """
    p = Path(db_file).expanduser().resolve()
    # SQLAlchemy/SQLite 在 Windows 需要使用正斜線
    return f"sqlite:///{p.as_posix()}"


def _resolve_database_url() -> str:
    """
    解析最終使用的 DATABASE_URL。
    優先順序：
    1) 環境變數 DATABASE_URL（建議設為絕對路徑）
    2) 環境變數 COURSEPAY_DB_FILE（檔名或路徑） -> 轉 sqlite URL
    3) 專案根目錄下的 coursepay.db -> 轉 sqlite URL
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # 若提供了檔名或路徑，轉為 sqlite URL
    db_file = os.getenv("COURSEPAY_DB_FILE")
    if db_file:
        return _to_sqlite_url(db_file)

    # 預設：專案根目錄 /coursepay.db
    # services/db.py -> services/ -> 專案根目錄
    project_root = Path(__file__).resolve().parents[1]
    return _to_sqlite_url(project_root / "coursepay.db")


# -----------------------------
# 初始化與 Session 取得
# -----------------------------
def init_db(uri: Optional[str] = None, echo: bool = False) -> Engine:
    """
    初始化 Engine 與 Session factory（整個 app 共用一次）。
    若 uri 為 None，會自動依環境解析。
    """
    global _engine, _Session

    uri = uri or _resolve_database_url()
    _engine = create_engine(uri, echo=echo, future=True)
    _Session = sessionmaker(bind=_engine, future=True, autoflush=False, autocommit=False)
    return _engine


def init_from_env(echo: bool = False) -> Engine:
    """
    便利函式：直接依環境變數初始化（等同於 init_db(None, echo)）。
    建議在 create_app() 中呼叫一次。
    """
    return init_db(None, echo=echo)


def get_session():
    """
    取得一個 SQLAlchemy Session。
    可直接用 with 來自動關閉：
        with get_session() as s:
            ...
    """
    assert _Session is not None, "DB not initialized; call init_db() or init_from_env() first."
    return _Session()


def get_engine() -> Optional[Engine]:
    return _engine


def get_db_path() -> Optional[str]:
    """
    取得目前 Engine 指向的實體 DB 檔案路徑（僅 SQLite 有意義）。
    方便在除錯路由中回報真實檔案位置，避免連錯 DB。
    """
    if _engine is None:
        return None
    try:
        dbfile = _engine.url.database
        if not dbfile:
            return None
        return str(Path(dbfile).resolve())
    except Exception:
        return None


# -----------------------------
# 建表
# -----------------------------
def create_all() -> None:
    """在首次啟動時建立所有資料表"""
    from services import models  # noqa: F401  確保模型已載入
    engine = get_engine()
    assert engine is not None, "DB engine not initialized. Call init_db() or init_from_env() first."
    Base.metadata.create_all(bind=engine)
