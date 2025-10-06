# config.py
import os
from dotenv import load_dotenv

# 載入專案根目錄的 .env（沒有也不會報錯）
load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "please_change_me_in_dev")

    # Database（預設用 SQLite 檔案）
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///coursepay.db")
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") == "1"

    # Stripe
    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
