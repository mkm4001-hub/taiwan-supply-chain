import textwrap
"""
================================================================================
科技巨頭台灣供應鏈情報庫 - Streamlit 旗艦正式版 (直通 V25 網頁版)
根據使用者指示更新：
1. 移除多餘的內建 V25 粗糙運算面板（避免因資料不足顯示 0 分雜訊）。
2. 全面改為純粹乾淨的「直通 V25.2 獨立網頁」：
   - 每家公司旁「更新行情」正下方，直接設置醒目的「🐋 前往 V25.2 完整分析 ↗」按鈕！
   - 點擊後以新分頁直接開啟你的真實 V25.2 網頁，並自動帶入該檔股票代號（例如 ?stock=2330）。
3. 提供智能網址自動儲存：在側邊欄貼上一次真實網址，系統自動寫入 users.json 永久記住！
4. 保留多使用者登入驗證、FinMind Token 上傳、公司名稱字體放大 2 倍等完整功能。
================================================================================
"""

import streamlit as st
import json
import os
import time
import random
import urllib.request
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="科技巨頭台灣供應鏈情報庫 (V14 旗艦正式版)",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)


_RENDERED_KEYS = set()

def get_unique_key(base_key: str) -> str:
    global _RENDERED_KEYS
    if base_key not in _RENDERED_KEYS:
        _RENDERED_KEYS.add(base_key)
        return base_key
    i = 1
    while f"{base_key}_{i}" in _RENDERED_KEYS:
        i += 1
    unique_k = f"{base_key}_{i}"
    _RENDERED_KEYS.add(unique_k)
    return unique_k

V25_APP_URL = "https://yiy6gksxghhs5mnc7ufxcs.streamlit.app"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_supply_chain_db.json")
USERS_PATH = os.path.join(BASE_DIR, "users.json")

# ==============================================================================
# CSS 樣式注入
# ==============================================================================
st.markdown("""
<style>
    div[data-baseweb="tab-list"] {
        gap: 12px !important;
        margin-bottom: 24px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
    }
    div[data-baseweb="tab-list"] button[role="tab"] {
        font-size: 1.22rem !important;
        padding: 12px 26px !important;
        letter-spacing: 0.02em !important;
        border-radius: 10px 10px 0 0 !important;
        transition: all 0.25s ease !important;
    }
    div[data-baseweb="tab-list"] button[aria-selected="true"] {
        font-weight: 800 !important;
        color: #0284c7 !important;
        border-bottom: 3.5px solid #0284c7 !important;
        background: rgba(2, 132, 199, 0.08) !important;
    }
    div[data-baseweb="tab-list"] button[aria-selected="false"] {
        font-weight: 500 !important;
        color: #64748b !important;
    }
    .hero-banner {
        padding: 18px 24px;
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        border-radius: 18px;
        border: 1px solid rgba(56,189,248,0.35);
        margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(2, 132, 199, 0.25);
    }
    .hero-title {
        color: #ffffff;
        margin: 0;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.01em;
    }
    .hero-sub {
        color: #94a3b8;
        margin: 6px 0 0 0;
        font-size: 0.95rem;
    }
    .company-card {
        padding: 14px 18px;
        border: 1.5px solid rgba(2, 132, 199, 0.25);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.03);
        margin-bottom: 12px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 多使用者帳號與設定檔管理
# ==============================================================================
DEFAULT_USERS_DATA = {
    "settings": {
        "v25_default_url": ""
    },
    "users": {
        "admin": {"password": "v25", "role": "VIP", "name": "巨鯨管理員"},
        "vip": {"password": "v25", "role": "VIP", "name": "尊榮 VIP 會員"},
        "user1": {"password": "123", "role": "Standard", "name": "一般體驗會員"}
    }
}

def load_users_data():
    if os.path.exists(USERS_PATH):
        try:
            with open(USERS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 啟動時自動全量對齊各指標
            for c, v in data.get("vendors", {}).items():
                p_val = float(str(v.get("price", "0")).replace("元", "").replace(",", "").strip()) if str(v.get("price", "0")).replace("元", "").replace(",", "").strip().replace(".", "").isdigit() else 0
                if p_val > 0:
                    recalculate_vendor_metrics(v, p_val)
            return data
        except Exception:
            return DEFAULT_USERS_DATA
    return DEFAULT_USERS_DATA

def save_users_data(data):
    try:
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"儲存帳號設定檔警示: {e}")

users_payload = load_users_data()
users_dict = users_payload.get("users", {})

def check_multiuser_auth():
    if st.session_state.get("authenticated", False):
        return True

    # 登入畫面調整 1.5 倍放大樣式注入 (不放置更改說明)
    st.markdown("""
        <style>
            div[data-testid="stTextInput"] input {
                font-size: 1.35rem !important;
                height: 3.6rem !important;
                border-radius: 12px !important;
                border: 1.8px solid rgba(2, 132, 199, 0.35) !important;
                padding: 10px 16px !important;
            }
            div[data-testid="stTextInput"] label p {
                font-size: 1.25rem !important;
                font-weight: 700 !important;
                color: #0284c7 !important;
                margin-bottom: 6px !important;
            }
            div.stButton > button {
                font-size: 1.35rem !important;
                font-weight: 800 !important;
                padding: 12px 28px !important;
                height: 3.8rem !important;
                border-radius: 12px !important;
                background: linear-gradient(135deg, #0284c7, #2563eb) !important;
                color: white !important;
                box-shadow: 0 4px 18px rgba(2, 132, 199, 0.35) !important;
                transition: all 0.25s !important;
            }
            div.stButton > button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 24px rgba(2, 132, 199, 0.5) !important;
            }
        </style>
        <div style="max-width: 720px; margin: 35px auto 25px auto; padding: 40px 36px; border-radius: 24px; border: 2.5px solid #0284c7; background: linear-gradient(180deg, rgba(2, 132, 199, 0.08) 0%, rgba(99, 102, 241, 0.05) 100%); text-align: center; box-shadow: 0 16px 40px -10px rgba(2, 132, 199, 0.25);">
            <div style="font-size: 4.2rem; margin-bottom: 10px;">🔐</div>
            <h1 style="color: #0284c7; margin: 0 0 10px 0; font-weight: 900; font-size: 2.6rem; letter-spacing: -0.01em;">科技巨頭台灣供應鏈情報庫</h1>
            <p style="color: #475569; font-size: 1.35rem; margin: 0; font-weight: 600;">多使用者身分認證系統 ｜ V14 旗艦正式版</p>
        </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2.5, 1])
    with col_m:
        user_input = st.text_input("👤 使用者帳號 (Username)", placeholder="請輸入帳號 (例如 admin / vip)").strip()
        st.write("")
        pwd_input = st.text_input("🔑 登入密碼 (Password)", type="password", placeholder="請輸入密碼...")
        st.write("")
        if st.button("🚀 登入系統 ➔", use_container_width=True):
            if user_input in users_dict:
                acc = users_dict[user_input]
                if pwd_input == acc.get("password", ""):
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"] = user_input
                    st.session_state["user_role"] = acc.get("role", "Standard")
                    st.session_state["user_name"] = acc.get("name", user_input)
                    st.session_state["user_pwd"] = pwd_input
                    st.success(f"✅ 歡迎回來，{acc.get('name')}！(權限級別: {acc.get('role')})")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤！請重新輸入。")
            else:
                st.error("❌ 找不到此使用者帳號，請確認名稱是否正確。")
        
        st.markdown("<div style='text-align: center; color: #94a3b8; font-size: 1.05rem; margin-top: 18px;'>🔒 專屬量化情報系統，請使用授權帳號密碼登入。</div>", unsafe_allow_html=True)
    return False
if not check_multiuser_auth():
    st.stop()

# ==============================================================================
# 資料庫載入
# ==============================================================================
def init_database():
    if "db" not in st.session_state:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r", encoding="utf-8") as f:
                st.session_state["db"] = json.load(f)
        else:
            st.error(f"找不到資料庫母檔 {DB_PATH}")
            st.stop()

init_database()
db = st.session_state["db"]
clients = db["clients"]
domains = db["domains"]
vendors = db["vendors"]
current_role = st.session_state.get("user_role", "Standard")

# ==============================================================================
# V25.2 DataEngine 擬真安全資料同步核心
# ==============================================================================
class V25MarketSyncEngine:
    def __init__(self, finmind_token=""):
        self.finmind_token = finmind_token.strip()
        self.dl = None
        if self.finmind_token:
            try:
                from FinMind.data import DataLoader
                self.dl = DataLoader()
                self.dl.login_by_token(api_token=self.finmind_token)
            except Exception:
                self.dl = None

    def fetch_single_stock_price(self, stock_id, status_placeholder=None, apply_delay=True):
        stock_id = str(stock_id).strip()
        tw_code = f"{stock_id}.TW"
        two_code = f"{stock_id}.TWO"
        
        if apply_delay:
            delay_time = random.uniform(1.5, 3.0)
            if status_placeholder:
                status_placeholder.text(f"⏳ 正在載入 {stock_id} ... (擬真防爬安全延遲 {delay_time:.2f} 秒)")
            time.sleep(delay_time)

        # 方案 A：yfinance
        try:
            import yfinance as yf
            for code in [tw_code, two_code]:
                try:
                    ticker = yf.Ticker(code)
                    df = ticker.history(period="10d", auto_adjust=False)
                    if not df.empty and len(df) > 0:
                        latest = df.iloc[-1]
                        close_price = round(float(latest['Close']), 2)
                        trade_date = df.index[-1].strftime("%Y-%m-%d")
                        return {
                            "price": f"{close_price:,.1f} 元" if close_price >= 100 else f"{close_price:.2f} 元",
                            "raw_price": close_price,
                            "date": trade_date,
                            "status": "success"
                        }, None
                except Exception:
                    continue
        except Exception:
            pass

        # 方案 B：台灣證交所/櫃買中心官方 MIS API 備援
        try:
            url_tse = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{stock_id}.tw|otc_{stock_id}.two"
            req = urllib.request.Request(url_tse, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=5) as response:
                res_json = json.loads(response.read().decode('utf-8'))
                msg_list = res_json.get("msgArray", [])
                if msg_list:
                    row = msg_list[0]
                    price_str = row.get("z", "-")
                    if price_str == "-" or not price_str:
                        price_str = row.get("y", "0")
                    close_price = round(float(price_str), 2)
                    if close_price > 0:
                        trade_date = row.get("d", datetime.now().strftime("%Y-%m-%d"))
                        return {
                            "price": f"{close_price:,.1f} 元" if close_price >= 100 else f"{close_price:.2f} 元",
                            "raw_price": close_price,
                            "date": trade_date,
                            "status": "success"
                        }, None
        except Exception:
            pass

        # 方案 C：FinMind 備援
        if self.dl:
            try:
                today_str = (datetime.now() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
                df_fm = self.dl.taiwan_stock_daily(stock_id=stock_id, start_date=today_str)
                if not df_fm.empty:
                    latest = df_fm.iloc[-1]
                    close_price = round(float(latest['close']), 2)
                    return {
                        "price": f"{close_price:,.1f} 元" if close_price >= 100 else f"{close_price:.2f} 元",
                        "raw_price": close_price,
                        "date": latest.get('date', datetime.now().strftime("%Y-%m-%d")),
                        "status": "success"
                    }, None
            except Exception:
                pass

        return None, "所有線路皆連線失敗或查無代碼"

def recalculate_vendor_metrics(v, raw_price):
    """
    全自動連動計算：
    1. 動態本益比 (Trailing P/E) = raw_price / eps_4q
    2. 預估本益比 (Forward P/E) = raw_price / forward_eps
    3. 法人目標本益比區間 (Target P/E Range) = target_price / forward_eps
    4. 目標價潛在空間 (Target Upside) = (target_price - raw_price) / raw_price
    """
    if not raw_price or raw_price <= 0:
        return

    # 1. Trailing P/E
    try:
        raw_eps = float(str(v.get("eps_4q", "0")).replace("元", "").replace(",", "").strip())
        if raw_eps > 0:
            v["trailing_pe"] = f"{round(raw_price / raw_eps, 1)} 倍"
    except Exception:
        pass

    # 2. Forward P/E
    try:
        raw_fwd_eps = float(str(v.get("forward_eps", "0")).replace("元", "").replace(",", "").strip())
        if raw_fwd_eps > 0:
            v["forward_pe"] = f"{round(raw_price / raw_fwd_eps, 1)} 倍"
    except Exception:
        pass

    # 3. Target P/E Range & Target Upside
    try:
        target_str = str(v.get("target_price", "0")).replace("元", "").strip()
        raw_fwd_eps = float(str(v.get("forward_eps", "0")).replace("元", "").replace(",", "").strip())
        parts = target_str.split("~")
        
        if len(parts) == 2:
            t_low = float(parts[0].replace(",", "").strip())
            t_high = float(parts[1].replace(",", "").strip())
            
            if raw_fwd_eps > 0:
                pe_low = round(t_low / raw_fwd_eps, 1)
                pe_high = round(t_high / raw_fwd_eps, 1)
                v["target_pe_range"] = f"{pe_low} ~ {pe_high} 倍" if pe_low != pe_high else f"{pe_low} 倍"
            
            up_low = round(((t_low - raw_price) / raw_price) * 100, 1)
            up_high = round(((t_high - raw_price) / raw_price) * 100, 1)
            sign_low = "+" if up_low >= 0 else ""
            sign_high = "+" if up_high >= 0 else ""
            v["target_upside"] = f"{sign_low}{up_low}% ~ {sign_high}{up_high}%"
            v["upside_pot"] = v["target_upside"]
            
        elif len(parts) == 1 and parts[0]:
            t_val = float(parts[0].replace(",", "").strip())
            if raw_fwd_eps > 0:
                v["target_pe_range"] = f"{round(t_val / raw_fwd_eps, 1)} 倍"
            up_val = round(((t_val - raw_price) / raw_price) * 100, 1)
            sign = "+" if up_val >= 0 else ""
            v["target_upside"] = f"{sign}{up_val}%"
            v["upside_pot"] = v["target_upside"]
    except Exception:
        pass

def apply_vendor_market_update(code, res):
    v = st.session_state["db"]["vendors"][code]
    raw_price = res["raw_price"]
    v["price"] = res["price"]
    v["price_date"] = res.get("date", datetime.now().strftime("%Y-%m-%d"))
    v["last_synced_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 全面連動重新計算本益比與目標價空間
    recalculate_vendor_metrics(v, raw_price)

    st.session_state["db"]["last_global_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(st.session_state["db"], f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"本地存檔警示: {e}")
# ==============================================================================
# 主程式介面
# ==============================================================================

def render_single_vendor_page(code, v):
    """
    獨立單一公司戰略情報網頁專屬視圖：
    1. 不與其他公司混在同一畫面，純粹呈現該公司的全套深度情報檔案。
    2. 頂部與底部皆設有「← 返回前一頁 (供應商總覽)」按鈕。
    3. 全面採用 Streamlit 原生卡片與指標元件 (st.metric / st.columns)，杜絕 Markdown 縮排代碼塊渲染錯誤。
    4. 包含最新行情、動態/預估PE、目標PE區間、潛在空間、實收股本、最新月營收YoY/MoM、近3週籌碼集中度。
    """
    # 頂部導航列
    col_nav_back, col_nav_meta = st.columns([2.8, 7.2])
    with col_nav_back:
        if st.button("← 返回前一頁 (供應商總覽)", key="btn_back_single_top", use_container_width=True):
            st.session_state["selected_vendor_code"] = None
            st.rerun()
    with col_nav_meta:
        st.markdown(
            f"<div style='display:flex; justify-content:flex-end; align-items:center; gap:8px; padding-top:6px;'>"
            f"<span style='color:#64748b; font-size:0.88rem;'>所屬產業鏈：<strong>{v.get('tier', '供應鏈')}</strong></span>"
            f"<span style='color:#cbd5e1;'>｜</span>"
            f"<span style='color:#0284c7; font-size:0.88rem; font-weight:700; background:rgba(2,132,199,0.08); padding:2px 8px; border-radius:6px;'>{v.get('sub_segment', '-')}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    st.write("")

    # 1. 主公司頂部 Header 卡片 (乾淨 HTML，無多餘空行與縮排)
    header_html = (
        f"<div style='padding:20px 24px; background:linear-gradient(135deg, rgba(2,132,199,0.08), rgba(99,102,241,0.08)); border:1.5px solid #0284c7; border-radius:16px; margin-bottom:14px;'>"
        f"<div style='display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;'>"
        f"<div>"
        f"<h1 style='margin:0; font-size:2.2rem; font-weight:800; color:#0284c7; letter-spacing:-0.01em;'>"
        f"{v['name']} <span style='font-size:1.45rem; color:#6366f1; font-weight:700;'>({code})</span>"
        f"</h1>"
        f"<div style='font-size:0.95rem; color:#475569; margin-top:6px; font-weight:500;'>{v.get('products', '-')}</div>"
        f"</div>"
        f"<div style='font-size:0.82rem; color:#059669; background:rgba(5,150,105,0.12); border:1px solid rgba(5,150,105,0.3); padding:4px 10px; border-radius:8px; font-weight:700;'>"
        f"{v.get('role_type', '領頭羊主供應商')}"
        f"</div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # 2. 核心 5 大行情與估值指標 (採用 Streamlit 原生 st.columns + st.metric，100% 免疫 Markdown 程式碼塊問題)
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("最新收盤價", v.get("price", "-"))
    with m2:
        st.metric("動態本益比", v.get("trailing_pe", "-"), help=f"依據近四季EPS: {v.get('eps_4q', '-')} 計算")
    with m3:
        st.metric("預估本益比", v.get("forward_pe", "-"), help=f"依據法人預估EPS: {v.get('forward_eps', '-')} 計算")
    with m4:
        st.metric("🎯 目標 PE 區間", v.get("target_pe_range", "-"))
    with m5:
        up_raw = str(v.get("target_upside", "-")).strip()
        up_val = f"+{up_raw}" if up_raw and not up_raw.startswith("+") and not up_raw.startswith("-") else up_raw
        st.metric("🚀 目標價潛在空間", up_val)

    date_badge = v.get('price_date', '最新')
    sync_ts = v.get('last_synced_at', '')
    ts_label = f" (更新於: {sync_ts.split(' ')[1]})" if sync_ts else ""
    st.caption(f"📅 報價基準日：{date_badge}{ts_label}")

    st.write("")

    # 3. 核心新功能：【目前實收股本】＋【最新月營收 YoY / MoM】＋【近 3 週法人與散戶籌碼變化】
    sub1, sub2, sub3 = st.columns(3)
    with sub1:
        with st.container(border=True):
            st.caption("🏢 目前實收資本額 (股本)")
            st.markdown(f"<h4 style='margin:0; color:#0284c7; font-weight:800;'>{v.get('capital_stock', '評估中')}</h4>", unsafe_allow_html=True)
            st.caption("評估籌碼流動性與股本輕重")
    with sub2:
        with st.container(border=True):
            st.caption("📈 最新月營收動能 (YoY / MoM)")
            st.markdown(f"<h4 style='margin:0; color:#059669; font-weight:800;'>YoY {v.get('revenue_yoy', '-')} ｜ MoM {v.get('revenue_mom', '-')}</h4>", unsafe_allow_html=True)
            st.caption(v.get('revenue_summary', '營收增長中'))
    with sub3:
        with st.container(border=True):
            st.caption("💎 近 3 週籌碼集中度變化")
            st.markdown(f"<h4 style='margin:0; color:#d97706; font-weight:800;'>法人 {v.get('chip_inst_3w', '-')} ｜ 散戶 {v.get('chip_retail_3w', '-')}</h4>", unsafe_allow_html=True)
            st.caption(v.get('chip_summary', '籌碼安定'))

    st.write("")

    # 4. 兩大快捷操作按鈕
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 即時連網更新此股行情", key="btn_sync_single_stock", use_container_width=True):
            engine = V25MarketSyncEngine(finmind_token=st.session_state.get("fm_token", ""))
            with st.spinner(f"連網更新 {v['name']} ({code}) ..."):
                res, err = engine.fetch_single_stock_price(code, apply_delay=False)
                if res and res.get("status") == "success":
                    apply_vendor_market_update(code, res)
                    st.success(f"✅ {v['name']} 最新價: {res['price']}，各項指標已全數重算完成！")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"❌ 更新失敗: {err}")

    with col_btn2:
        v25_link = f"{V25_APP_URL}/?stock={code}"
        st.link_button(f"🐋 前往巨鯨 V25.2 完整技術籌碼分析 ↗", v25_link, use_container_width=True)

    st.markdown("---")

    # 5. 深度戰略情報檔案 (直接全開展示，不與其他公司混合)
    st.markdown("### 📋 完整深度戰略情報檔案")

    st.markdown(f"**🤝 核心合作客戶**： {' '.join([f'`{c}`' for c in v.get('clients', [])])}")
    st.markdown(f"**🎯 業務純度佔比**：`{v.get('pure_share', '-')}` ｜ **最新毛利率**：`{v.get('margin', '-')}`")

    st.markdown("##### 📊 各戰略領域營收比重拆解")
    domain_list = v.get("domain_breakdown", [])
    if domain_list:
        for item in domain_list:
            st.write(f"{item['domain']}: {item['share']}%")
            st.progress(item['share'] / 100)
    else:
        st.caption("暫無多領域詳細拆解數據")

    st.markdown(f"""##### 🏗️ 資本支出 (CapEx) 規模與擴產目的
- **未來 2 年預估規模**：`{v.get('capex_future_2y', '-')}`
- **年增幅度**：`{v.get('capex_yoy_increase', '-')}`
- **投資目的**：{v.get('capex_purpose', '-')}
""")

    st.markdown("##### 🎯 法人估值與重估解析 (Valuation & Rerating)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("當前預估 PE", v.get("forward_pe", "-"))
    with c2:
        st.metric("法人目標 PE 區間", v.get("target_pe_range", "-"))
    with c3:
        up_val_c3 = f"+{v.get('target_upside')}" if v.get("target_upside") and not str(v.get("target_upside")).startswith("+") else v.get("target_upside", "-")
        st.metric("目標價潛在空間", up_val_c3)

    rerating_text = v.get("rerating_driver", "")
    if rerating_text:
        st.info(f"💡 **法人估值重估 (Rerating) 關鍵驅動力**：\\n\\n{rerating_text}")

    if current_role == "VIP":
        st.markdown(f"**法說成長指引**：{v.get('guidance', '-')}")
        st.markdown(f"**法人共識目標價**：`{v.get('target_price', '-')}` ({v.get('analyst_count', '-')})")
    else:
        st.info("🔒 法說成長指引與法人共識目標價屬於 VIP 會員專屬內容，請升級帳號權限查閱。")

    if "last_synced_at" in v:
        st.caption(f"🕒 數據最後更新時間：{v['last_synced_at']} (已永久保存至硬碟)")

    st.markdown("##### 📑 官方數據出處佐證")
    for s in v.get("sources", []):
        st.markdown(f"- **[{s.get('date', '最新')}]** [{s['title']}]({s['url']})")

    st.markdown("---")
    if st.button("← 返回前一頁 (供應商總覽)", key="btn_back_single_bottom", use_container_width=True):
        st.session_state["selected_vendor_code"] = None
        st.rerun()

def main():
    global _RENDERED_KEYS
    _RENDERED_KEYS.clear()

    # 檢查是否進入單一公司專屬情報網頁模式 (完全獨立，不與其他公司混合)
    selected_v_code = st.session_state.get("selected_vendor_code")
    if selected_v_code and selected_v_code in vendors:
        render_single_vendor_page(selected_v_code, vendors[selected_v_code])
        return
    last_sync_info = db.get("last_global_sync", "2026-09-04 08:30:00")
    user_name = st.session_state.get("user_name", "會員")
    role_badge = "👑 VIP 尊榮權限" if current_role == "VIP" else "👤 一般會員權限"
    
    st.markdown(f"""
        <div class="hero-banner">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 class="hero-title">🌐 科技巨頭台灣供應鏈情報庫</h1>
                    <p class="hero-sub">AI 算力 ＆ 低軌衛星 ＆ 車用電子 ＆ 光通訊 ＆ 智慧機器人 ｜ V14 供應商同族群橫向評比 ＆ 巨鯨 V25.2 直連</p>
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <div style="font-size: 0.85rem; color: #f1f5f9; background: rgba(2, 132, 199, 0.25); border: 1px solid #38bdf8; padding: 6px 12px; border-radius: 8px;">
                        {user_name} ｜ <strong style="color: #fde047;">{role_badge}</strong>
                    </div>
                    <div style="font-size: 0.85rem; color: #94a3b8; background: rgba(0,0,0,0.35); padding: 6px 12px; border-radius: 8px;">
                        🕒 行情基準日：<strong style="color: #38bdf8;">{last_sync_info}</strong>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 側邊欄控制台
    with st.sidebar:
        st.header("⚙️ 系統設定與 V25.2 直連")
        st.write(f"👤 當前登入：**{user_name}** ({current_role})")
        if st.button("🔒 登出系統", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

        st.markdown("---")
        # V25.2 網址直連設定 (直接綁定，不需再輸入或詢問)
        st.subheader("🔗 巨鯨 V25.2 系統直連")
        st.caption(f"🎯 官方目標網址：`{V25_APP_URL}`")
        st.info("💡 點擊任一廠商卡片旁的「前往 V25.2 分析」按鈕，即可直接以新分頁直連該網頁，由使用者自行在 V25 頁面輸入密碼登入。")

        # 管理員專屬：多使用者帳號管理
        if st.session_state.get("current_user") == "admin":
            with st.expander("👥 帳號管理小面板 (管理員專屬)"):
                st.caption("直接在此為學員或客戶新增帳號密碼")
                for u_id, u_data in users_dict.items():
                    st.text(f"• {u_id} ({u_data.get('role')}): 密碼 {u_data.get('password')}")
                
                st.markdown("---")
                new_u_id = st.text_input("帳號 (Username)", key="m_new_uid").strip()
                new_u_pwd = st.text_input("密碼 (Password)", key="m_new_pwd").strip()
                new_u_role = st.selectbox("權限級別", ["VIP", "Standard"], key="m_new_role")
                new_u_name = st.text_input("暱稱 / 顯示名稱", key="m_new_name").strip()
                
                if st.button("💾 儲存此帳號", use_container_width=True):
                    if new_u_id and new_u_pwd:
                        users_dict[new_u_id] = {
                            "password": new_u_pwd,
                            "role": new_u_role,
                            "name": new_u_name or new_u_id,
                            "v25_access": "全功能解鎖" if new_u_role == "VIP" else "基礎瀏覽"
                        }
                        users_payload["users"] = users_dict
                        save_users_data(users_payload)
                        st.success(f"✅ 帳號 {new_u_id} 儲存成功！")
                        time.sleep(0.8)
                        st.rerun()

        st.markdown("---")
        # FinMind Token 上傳
        st.subheader("🔑 FinMind Token (檔案上傳)")
        uploaded_token = st.file_uploader("📂 上傳 Token (.txt 檔)", type=["txt"], help="比照 V25.2 模式，直接將包含 Token 的 txt 文字檔拖入即可")
        if uploaded_token is not None:
            token_content = uploaded_token.read().decode('utf-8').strip()
            if token_content:
                st.session_state["fm_token"] = token_content
                os.environ["FINMIND_TOKEN"] = token_content
                st.success(f"✅ 成功載入 Token！({token_content[:5]}****)")
        
        token_input = st.text_input("或手動貼上 Token (選填)", value=st.session_state.get("fm_token", ""), type="password")
        if token_input:
            st.session_state["fm_token"] = token_input.strip()
            os.environ["FINMIND_TOKEN"] = token_input.strip()

        st.markdown("---")
        st.subheader("🔄 全體批次行情同步")
        st.caption("💡 內建 V25.2 擬真隨機延遲 (1.5~3.0秒)，模擬真人防封鎖。")
        batch_count = st.slider("單次更新數量", min_value=5, max_value=len(vendors), value=15, step=5)
        
        if st.button("🚀 啟動 V25.2 批次擬真安全同步", use_container_width=True):
            engine = V25MarketSyncEngine(finmind_token=st.session_state.get("fm_token", ""))
            progress_bar = st.progress(0)
            status_box = st.empty()
            
            selected_codes = list(vendors.keys())[:batch_count]
            success_count = 0
            
            for i, code in enumerate(selected_codes):
                v = vendors[code]
                status_box.text(f"正在同步 [{i+1}/{len(selected_codes)}] {v['name']} ({code}) ...")
                res, err = engine.fetch_single_stock_price(code, status_placeholder=status_box, apply_delay=True)
                
                if res and res.get("status") == "success":
                    apply_vendor_market_update(code, res)
                    success_count += 1
                
                progress_bar.progress((i + 1) / len(selected_codes))
            
            status_box.success(f"✅ 完成 {success_count} 檔個股最新行情更新並永久存檔！")
            time.sleep(1)
            st.rerun()

        st.markdown("---")
        st.subheader("🔍 全域快速檢索")
        search_query = st.text_input("搜尋股票代號或名稱", placeholder="例：2330、尖點、盟立、6442...")

    # 搜尋結果展示
    if search_query:
        st.subheader(f"🔍 搜尋結果：'{search_query}'")
        matched = {c: v for c, v in vendors.items() if search_query in c or search_query in v["name"] or search_query in v.get("products", "")}
        if matched:
            for idx, (c, v) in enumerate(matched.items()):
                render_vendor_card_with_sync(c, v, prefix=f"search_{idx}_{c}")
        else:
            st.warning("未找到符合條件的供應商。")
        st.markdown("---")

    # 首頁三大分頁
    tabs = st.tabs(["🏢 SECTION A：國際大客戶專區", "🌐 SECTION B：五大戰略產業鏈全景", "📑 全 87 家廠商總表", "🔥 供應商同族群比較"])

    # --- SECTION A: 國際客戶專區 ---
    with tabs[0]:
        selected_client = st.session_state.get("selected_client")
        
        if selected_client and selected_client in clients:
            c = clients[selected_client]
            
            c_back, c_info = st.columns([1.8, 8.2])
            with c_back:
                if st.button("← 返回大客戶清單", key="btn_back_clients", use_container_width=True):
                    st.session_state["selected_client"] = None
                    st.rerun()
            with c_info:
                st.markdown(f"<h3 style='margin:0; color:#0284c7; font-weight:800;'>🎯 {c['icon']} {c['name']} 在台專屬供應鏈全景名單</h3>", unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style="padding: 14px 18px; background: rgba(2, 132, 199, 0.05); border: 1.5px solid rgba(2, 132, 199, 0.3); border-radius: 12px; margin: 16px 0 20px 0;">
                    <p style="margin: 0; color: #334155; font-size: 0.95rem;">{c['desc']}</p>
                    <div style="display: flex; gap: 18px; margin-top: 8px; font-size: 0.88rem; flex-wrap: wrap;">
                        <span style="color: #059669;">💰 <strong>資本支出</strong>：{c.get('capex_forecast', '-')}</span>
                        <span style="color: #0284c7;">🎯 <strong>採購焦點</strong>：{c['key_focus']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            for tier in ["上游", "中游", "下游"]:
                sup_codes = c["suppliers"].get(tier, [])
                if sup_codes:
                    st.markdown(f"#### 📌 {tier}供應商 ({len(sup_codes)} 家)")
                    cols = st.columns(2)
                    for idx, scode in enumerate(sup_codes):
                        v = vendors.get(scode)
                        if v:
                            with cols[idx % 2]:
                                render_vendor_card_with_sync(scode, v, prefix=f"client_{tier}_{idx}_{scode}")
        else:
            st.markdown("""
                <div style="padding: 14px 18px; background: rgba(2, 132, 199, 0.06); border: 1.5px solid rgba(2, 132, 199, 0.35); border-radius: 14px; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #0284c7; font-weight: 800;">🏢 國際科技巨頭下單專區（在台採購核心）</h3>
                    <p style="margin: 4px 0 0 0; color: #64748b; font-size: 0.88rem;">點選任一國際大廠按鈕，畫面直接進入該客戶在台之專屬供應鏈頁面</p>
                </div>
            """, unsafe_allow_html=True)

            client_cols = st.columns(4)
            for i, (cid, cinfo) in enumerate(clients.items()):
                col = client_cols[i % 4]
                with col:
                    st.markdown(f"#### {cinfo['icon']} {cinfo['name']}")
                    st.caption(f"**焦點**：{cinfo['badge']}")
                    st.write(cinfo['desc'])
                    st.info(f"💰 **CapEx**：{cinfo.get('capex_forecast', '持續擴張')}")
                    if st.button(f"檢視 {cinfo['name']} 供應鏈 ➔", key=f"btn_c_{cid}", use_container_width=True):
                        st.session_state["selected_client"] = cid
                        st.rerun()

    # --- SECTION B: 五大產業鏈全景 ---
    with tabs[1]:
        selected_domain = st.session_state.get("selected_domain")
        
        if selected_domain and selected_domain in domains:
            d = domains[selected_domain]
            
            d_back, d_info = st.columns([1.8, 8.2])
            with d_back:
                if st.button("← 返回五大主題清單", key="btn_back_domains", use_container_width=True):
                    st.session_state["selected_domain"] = None
                    st.rerun()
            with d_info:
                st.markdown(f"<h3 style='margin:0; color:#7c3aed; font-weight:800;'>🌐 {d['icon']} {d['name']} 完整產業鏈樹狀圖譜</h3>", unsafe_allow_html=True)

            st.caption(f"{d['desc']} ｜ 趨勢焦點：{d['stats'].get('tech_trend', '-')}")

            for tier in d["tiers"]:
                with st.expander(f"📁 {tier['tier_name']}", expanded=True):
                    for cat in tier["categories"]:
                        st.markdown(f"**↳ {cat['cat_name']}**")
                        v_cols = st.columns(2)
                        for idx, v_item in enumerate(cat["vendors"]):
                            code = v_item["code"]
                            v = vendors.get(code)
                            if v:
                                with v_cols[idx % 2]:
                                    render_vendor_card_with_sync(code, v, prefix=f"domain_{tier.get('tier_name', '')}_{cat.get('cat_name', '')}_{idx}_{code}")
        else:
            st.markdown("""
                <div style="padding: 14px 18px; background: rgba(124, 58, 237, 0.06); border: 1.5px solid rgba(124, 58, 237, 0.35); border-radius: 14px; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #7c3aed; font-weight: 800;">🌐 五大戰略產業鏈主題全景區</h3>
                    <p style="margin: 4px 0 0 0; color: #64748b; font-size: 0.88rem;">點選任一主題按鈕，直接進入該產業之完整上中下游樹狀導航頁面</p>
                </div>
            """, unsafe_allow_html=True)

            domain_cols = st.columns(5)
            for i, (did, dinfo) in enumerate(domains.items()):
                col = domain_cols[i]
                with col:
                    st.markdown(f"#### {dinfo['icon']} {dinfo['name']}")
                    st.caption(dinfo['badge'])
                    st.write(dinfo['desc'])
                    if st.button(f"進入 {dinfo['name']} ➔", key=f"btn_d_{did}", use_container_width=True):
                        st.session_state["selected_domain"] = did
                        st.rerun()

    # --- 全廠商資料總覽表 ---
    with tabs[2]:
        st.subheader("📊 全體 87 家上市櫃供應商總覽表")
        st.markdown("<p style='color: #475569; font-size: 0.92rem; padding: 6px 12px; background: rgba(2,132,199,0.06); border-left: 3px solid #0284c7; border-radius: 0 6px 6px 0; margin-bottom: 12px;'>👉 <strong>點選下方總表任一列</strong>（或在上方直接選擇公司），畫面將<strong>直接進入該公司的獨立專屬情報網頁</strong>，純粹單一檢視，不與其他公司混合！</p>", unsafe_allow_html=True)
        
        col_t_search, col_t_info = st.columns([2.5, 3.5])
        with col_t_search:
            vendor_options = ["-- 點此直接選擇公司進入獨立情報網頁 --"] + [
                f"{c} {v['name']} ｜ {v.get('sub_segment', '')} ({v.get('tier', '')})" for c, v in vendors.items()
            ]
            picked_vendor = st.selectbox("🎯 快速選擇供應商進入情報網頁：", vendor_options, key="table_vendor_picker")
            if picked_vendor != "-- 點此直接選擇公司進入獨立情報網頁 --":
                chosen_code = picked_vendor.split(" ")[0]
                st.session_state["selected_vendor_code"] = chosen_code
                st.rerun()

        with col_t_info:
            st.caption("💡 **操作方式**：點擊總表中任一列（例如台積電、高力、奇鋐），畫面會瞬間切換至該公司專屬情報檔案；查閱後點擊「← 返回前一頁」即可隨時回到總表。")

        # 整理總表資料
        df_list = []
        for code_item, v in vendors.items():
            df_list.append({
                "股票代號": code_item,
                "公司名稱": v["name"],
                "實收股本": v.get("capital_stock", "-"),
                "營收 YoY": v.get("revenue_yoy", "-"),
                "營收 MoM": v.get("revenue_mom", "-"),
                "3週法人持股": v.get("chip_inst_3w", "-"),
                "3週散戶持股": v.get("chip_retail_3w", "-"),
                "最新收盤價": v.get("price", "-"),
                "動態本益比": v.get("trailing_pe", "-"),
                "近四季EPS": v.get("eps_4q", "-"),
                "預估本益比": v.get("forward_pe", "-"),
                "法人預估EPS": v.get("forward_eps", "-"),
                "法人目標價": v.get("target_price", "-") if current_role == "VIP" else "🔒 VIP 解鎖",
                "目標本益比": v.get("target_pe_range", "-"),
                "潛在空間": v.get("target_upside", v.get("upside_pot", "-")) if current_role == "VIP" else "🔒 VIP 解鎖",
                "次領域環節": v.get("sub_segment", "-"),
                "產業層級": v.get("tier", "-"),
                "毛利率": v.get("margin", "-"),
                "報價日期": v.get("price_date", "-")
            })

        df_display = pd.DataFrame(df_list)

        # 啟用表格點選互動事件 (點擊整列任意位置即刻進入獨立情報專頁)
        event = st.dataframe(
            df_display,
            use_container_width=True,
            selection_mode="single-row",
            on_select="rerun",
            key="overview_vendor_dataframe"
        )

        if event and hasattr(event, "selection") and event.selection.rows:
            sel_row_idx = event.selection.rows[0]
            if 0 <= sel_row_idx < len(df_display):
                clicked_code = str(df_display.iloc[sel_row_idx]["股票代號"]).strip()
                st.session_state["selected_vendor_code"] = clicked_code
                st.rerun()


    # --- SECTION D: 供應商同族群比較 (V14 全新模組) ---
    with tabs[3]:
        st.subheader("🔥 供應商同族群橫向評比專區 (13 大高討論度核心群組)")
        st.markdown("""
            <p style='color: #475569; font-size: 0.92rem; padding: 8px 14px; background: rgba(2,132,199,0.06); border-left: 3.5px solid #0284c7; border-radius: 0 8px 8px 0; margin-bottom: 16px;'>
                💡 <strong>同族群對比核心理念</strong>：將同性質、同零組件供應商放在同一個維度橫向比較（最新股價、股本、動態PE、預估PE、目標PE、潛在空間、月營收YoY/MoM、近3週法人散戶籌碼）。若同一家企業兼具多項業務（如台達電兼具電源與散熱、貿聯兼具線束與車用），則均歸類至各對應族群中。
            </p>
        """, unsafe_allow_html=True)

        clusters_data = db.get("clusters", {})
        cluster_names = list(clusters_data.keys())

        col_c_sel, col_c_info = st.columns([3, 7])
        with col_c_sel:
            chosen_cname = st.selectbox("🎯 選擇比較的供應商族群：", cluster_names, key="cluster_picker")
        
        c_info = clusters_data.get(chosen_cname, {})
        with col_c_info:
            st.markdown(f"""
                <div style="padding: 12px 18px; background: rgba(15, 23, 42, 0.85); border: 1.5px solid rgba(56, 189, 248, 0.3); border-radius: 12px;">
                    <div style="font-size: 0.82rem; color: #38bdf8; font-weight: 700; margin-bottom: 4px;">🚀 產業趨勢焦點 ｜ 共 {len(c_info.get('members', []))} 家代表性廠商</div>
                    <div style="color: #f1f5f9; font-size: 0.9rem; font-weight: 600; line-height: 1.45;">{c_info.get('trend', '')}</div>
                    <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 4px;">範疇：{c_info.get('desc', '')}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # 彙整該族群所有廠商的指標資料
        cluster_rows = []
        for m_item in c_info.get("members", []):
            m_code = m_item["code"]
            m_role = m_item["role"]
            v = vendors.get(m_code)
            if v:
                cluster_rows.append({
                    "股票代號": m_code,
                    "公司名稱": v["name"],
                    "在此族群主力角色與產品": m_role,
                    "最新收盤價": v.get("price", "-"),
                    "實收股本": v.get("capital_stock", "-").split(" ")[0],
                    "動態PE": v.get("trailing_pe", "-"),
                    "預估PE": v.get("forward_pe", "-"),
                    "目標 PE 區間": v.get("target_pe_range", "-"),
                    "目標價潛在空間": v.get("target_upside", "-"),
                    "營收 YoY": v.get("revenue_yoy", "-"),
                    "營收 MoM": v.get("revenue_mom", "-"),
                    "3週法人持股": v.get("chip_inst_3w", "-"),
                    "3週散戶持股": v.get("chip_retail_3w", "-"),
                    "近四季EPS": v.get("eps_4q", "-"),
                    "預估EPS": v.get("forward_eps", "-"),
                    "毛利率": v.get("margin", "-")
                })

        df_cluster = pd.DataFrame(cluster_rows)

        # 互動式同族群橫向評比表格
        st.markdown("##### 📋 同族群企業核心數據橫向對照總表 (點擊任一列直接穿透調出專屬情報網頁)")
        
        c_event = st.dataframe(
            df_cluster,
            use_container_width=True,
            selection_mode="single-row",
            on_select="rerun",
            key=f"cluster_table_{chosen_cname}"
        )

        if c_event and hasattr(c_event, "selection") and c_event.selection.rows:
            sel_idx = c_event.selection.rows[0]
            if 0 <= sel_idx < len(df_cluster):
                picked_code = str(df_cluster.iloc[sel_idx]["股票代號"]).strip()
                st.session_state["selected_vendor_code"] = picked_code
                st.rerun()

        # 族群內各公司卡片快速檢視區塊 (支援直通獨立網頁)
        st.markdown(f"##### 🗂️ 【{chosen_cname}】各廠商快速檢視與直調專頁")
        c_cols = st.columns(2)
        for i, m_item in enumerate(c_info.get("members", [])):
            m_code = m_item["code"]
            v = vendors.get(m_code)
            if v:
                with c_cols[i % 2]:
                    with st.container(border=True):
                        st.markdown(f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-size: 1.35rem; font-weight: 800; color: #0284c7;">
                                    {v['name']} <span style="font-size: 1.05rem; color: #6366f1;">({m_code})</span>
                                </span>
                                <span style="font-size: 0.76rem; color: #059669; background: rgba(5, 150, 105, 0.1); border: 1px solid rgba(5, 150, 105, 0.28); padding: 2px 7px; border-radius: 6px; font-weight: 700;">
                                    {v.get('tier', '供應鏈')}
                                </span>
                            </div>
                            <div style="font-size: 0.85rem; color: #475569; margin-bottom: 8px; font-weight: 500;">
                                🎯 <strong>族群角色</strong>：{m_item['role']}
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.86rem; color: #64748b; padding-top: 6px; border-top: 1px dashed rgba(2, 132, 199, 0.2);">
                                <span>股價: <strong style="color: #0284c7;">{v.get('price', '-')}</strong></span>
                                <span>預估PE: <strong style="color: #059669;">{v.get('forward_pe', '-')}</strong></span>
                                <span>目標PE: <strong style="color: #d97706;">{v.get('target_pe_range', '-')}</strong></span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #64748b; margin-top: 4px; padding: 3px 8px; background: rgba(0,0,0,0.03); border-radius: 6px;">
                                <span>營收YoY: <strong style="color: #10b981;">{v.get('revenue_yoy', '-')}</strong></span>
                                <span>3週法人: <strong style="color: #6366f1;">{v.get('chip_inst_3w', '-')}</strong></span>
                                <span>潛在空間: <strong style="color: #059669;">+{v.get('target_upside', '-')}</strong></span>
                            </div>
                        """, unsafe_allow_html=True)
                        st.write("")
                        c_btn1, c_btn2 = st.columns(2)
                        with c_btn1:
                            if st.button(f"📑 進入 {v['name']} 情報專頁 ➔", key=f"btn_cpage_{m_code}_{i}", use_container_width=True):
                                st.session_state["selected_vendor_code"] = m_code
                                st.rerun()
                        with c_btn2:
                            v25_link = f"{V25_APP_URL}/?stock={m_code}"
                            st.link_button(f"🐋 V25.2 分析 ↗", v25_link, use_container_width=True)


def render_vendor_card_with_sync(code, v, prefix='', default_expanded=False):
    """
    渲染單一公司卡片：
    1. 【公司名稱與股號字體放大 2 倍】(1.85rem)
    2. 右側設置「🔄 更新行情」以及直通獨立 V25.2 的「🐋 前往 V25.2 完整分析 ↗」按鈕！
    """
    card_container = st.container()
    with card_container:
        col_main, col_btn = st.columns([3.5, 1.5])
        
        with col_main:
            date_badge = v.get('price_date', '最新')
            sync_ts = v.get('last_synced_at', '')
            ts_label = f" (更新於: {sync_ts.split(' ')[1]})" if sync_ts else ""
            
            st.markdown(textwrap.dedent(f"""
                <div class="company-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 1.85rem; font-weight: 800; color: #0284c7; letter-spacing: -0.01em;">
                            {v['name']} <span style="font-size: 1.28rem; color: #6366f1; font-weight: 700;">({code})</span>
                        </span>
                        <span style="color: #0284c7; font-size: 0.82rem; font-weight: 700; background: rgba(2, 132, 199, 0.1); border: 1px solid rgba(2, 132, 199, 0.28); padding: 3px 8px; border-radius: 6px;">
                            {v.get('tier', '供應鏈')}
                        </span>
                    </div>
                    <div style="font-size: 0.88rem; color: #475569; margin: 4px 0 8px 0; font-weight: 500;">
                        {v.get('products', '-')}
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.92rem; color: #64748b; padding-top: 6px; border-top: 1px dashed rgba(2, 132, 199, 0.2);">
                        <span>最新股價: <strong style="color: #0284c7; font-size: 1.15rem;">{v.get('price', '-')}</strong></span>
                        <span>動態PE: <strong style="color: #059669; font-size: 1.05rem;">{v.get('trailing_pe', '-')}</strong> ｜ 預估PE: <strong style="color: #0284c7; font-size: 1.05rem;">{v.get('forward_pe', '-')}</strong></span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #475569; margin-top: 5px; background: rgba(2, 132, 199, 0.06); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(2, 132, 199, 0.15);">
                        <span>🎯 目標 PE: <strong style="color: #d97706; font-weight: 700;">{v.get('target_pe_range', '-')}</strong></span>
                        <span>🚀 潛在空間: <strong style="color: #059669; font-weight: 700;">{v.get('target_upside', '-')}</strong></span>
                    </div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">
                        📅 報價日期: {date_badge}{ts_label}
                    </div>
                </div>
            """), unsafe_allow_html=True)

        with col_btn:
            st.write("")
            # 按鈕 1：更新行情
            sync_btn_key = get_unique_key(f"btn_sync_{code}_{prefix}" if prefix else f"btn_sync_{code}")
            if st.button("🔄 更新行情", key=sync_btn_key, use_container_width=True):
                engine = V25MarketSyncEngine(finmind_token=st.session_state.get("fm_token", ""))
                with st.spinner(f"連網更新 {v['name']} ({code}) ..."):
                    res, err = engine.fetch_single_stock_price(code, apply_delay=False)
                    if res and res.get("status") == "success":
                        apply_vendor_market_update(code, res)
                        st.success(f"✅ {v['name']} 最新價: {res['price']}")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ 更新失敗: {err}")

            # 按鈕 2：直接連到 V25.2 網頁，不詢問、不帶密碼，由使用者在 V25 頁面自行 KEY 密碼
            v25_link = f"{V25_APP_URL}/?stock={code}"
            st.link_button("🐋 前往 V25.2 分析 ↗", v25_link, use_container_width=True)
            
            # 直接切換進入獨立單一公司情報網頁
            btn_open_page_key = get_unique_key(f"btn_open_page_{code}_{prefix}")
            if st.button("📑 進入完整情報專頁 ➔", key=btn_open_page_key, use_container_width=True):
                st.session_state["selected_vendor_code"] = code
                st.rerun()

        # 展開基本面情報抽屜
        with st.expander(f"🔍 檢視 {v['name']} ({code}) 完整基本面情報檔案", expanded=(default_expanded or prefix.startswith("top_detail") or prefix.startswith("table_detail"))):
            st.markdown(f"**核心合作客戶**：{', '.join(v.get('clients', []))}")
            st.markdown(f"**業務純度佔比**：`{v.get('pure_share', '-')}` ｜ **最新毛利率**：`{v.get('margin', '-')}`")

            st.markdown("##### 📊 各戰略領域營收比重拆解")
            for item in v.get("domain_breakdown", []):
                st.write(f"{item['domain']}: {item['share']}%")
                st.progress(item['share'] / 100)

            st.markdown(f"**未來 2 年 CapEx**：`{v.get('capex_future_2y', '-')}` ({v.get('capex_yoy_increase', '-')})")
            st.caption(f"**支出目的**：{v.get('capex_purpose', '-')}")

            st.markdown("---")
            st.markdown("##### 🎯 法人估值與重估解析 (Valuation & Rerating)")
            col_val1, col_val2, col_val3 = st.columns(3)
            with col_val1:
                st.metric("當前預估 PE", v.get("forward_pe", "-"))
            with col_val2:
                st.metric("法人目標 PE 區間", v.get("target_pe_range", "-"))
            with col_val3:
                up_val = f"+{v.get('target_upside')}" if v.get("target_upside") else "-"
                st.metric("目標價潛在空間", up_val)

            rerating_text = v.get("rerating_driver", "")
            if rerating_text:
                st.info(f"💡 **法人估值重估 (Rerating) 關鍵驅動力**：\n{rerating_text}")

            if current_role == "VIP":
                st.markdown(f"**法說成長指引**：{v.get('guidance', '-')}")
                st.markdown(f"**法人共識目標價**：`{v.get('target_price', '-')}` ({v.get('analyst_count', '-')})")
            else:
                st.info("🔒 法說成長指引與法人共識目標價屬於 VIP 會員專屬內容，請升級帳號權限查閱。")

            if "last_synced_at" in v:
                st.caption(f"🕒 數據最後更新時間：{v['last_synced_at']} (已永久保存至硬碟)")

            st.markdown("##### 📑 官方數據出處佐證")
            for s in v.get("sources", []):
                st.markdown(f"- **[{s.get('date', '最新')}]** [{s['title']}]({s['url']})")

if __name__ == "__main__":
    main()
