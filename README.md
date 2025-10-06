@"
# CoursePay

Flask + Stripe Checkout（一次性付款）  
- /billing：Checkout + Webhook（驗簽＋入庫）
- /admin/payments：付款清單（分頁、搜尋、日期篩選）

## 需求
- Python 3.10+
- Stripe CLI（開發用 Webhook 轉發）

## 快速開始

```bash
# 1) 建虛擬環境並啟用
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
# source ./venv/bin/activate

# 2) 安裝套件
pip install -r requirements.txt

# 3) 準備環境設定（不要提交真實金鑰）
copy .env.example .env   # Windows (macOS/Linux: cp .env.example .env)
# 編輯 .env，填入：
# STRIPE_API_KEY=sk_test_xxx
# STRIPE_WEBHOOK_SECRET=whsec_xxx
# DATABASE_URL=sqlite:///D:/完整/絕對/路徑/coursepay.db   # 建議用絕對路徑
