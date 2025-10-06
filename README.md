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


執行
方式 A：兩個視窗

視窗 A（啟動 Flask）

flask run


視窗 B（Stripe 轉發 Webhook）

stripe listen --forward-to http://localhost:5000/billing/webhook
# 複製輸出的 whsec_* → 貼入 .env 的 STRIPE_WEBHOOK_SECRET

方式 B：開發腳本（若有 scripts/）
# Windows PowerShell
.\scripts\dev_restart.ps1
# macOS/Linux
bash scripts/dev_restart.sh

使用

前台課程：/courses（按「購買」→ 轉到 Stripe Checkout）

成功/取消：/billing/success、/billing/cancel（僅顯示，判準以 Webhook 為主）

後台清單：/admin/payments?q=&date_from=&date_to=&page=&page_size=

觸發測試事件：

stripe trigger checkout.session.completed

環境變數（.env）
STRIPE_API_KEY=
STRIPE_WEBHOOK_SECRET=
DATABASE_URL=

安全

.env、.db 已在 .gitignore，請勿提交。

程式碼中不要硬編碼 sk_test_ / whsec_。

真正付款判準以 Webhook 入庫的 payments 為準。

"@ | Set-Content -Encoding utf8 README.md


## 3-B-2 提交與推送
```powershell
git add README.md
git commit -m "docs: add quickstart and usage to README"
git push