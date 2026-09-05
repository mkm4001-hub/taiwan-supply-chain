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
    page_title="科技巨頭台灣供應鏈情報庫 (V25.2 直連版)",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        "admin": {"password": "mkm400!!", "role": "VIP", "name": "巨鯨管理員"},
        
    }
}

def load_users_data():
    if os.path.exists(USERS_PATH):
        try:
            with open(USERS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
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

    st.markdown("""
        <div style="max-width: 480px; margin: 50px auto 20px auto; padding: 28px; border-radius: 18px; border: 2px solid #0284c7; background: rgba(2, 132, 199, 0.04); text-align: center;">
            <div style="font-size: 2.8rem; margin-bottom: 8px;">🔐</div>
            <h2 style="color: #0284c7; margin: 0 0 8px 0; font-weight: 800;">科技巨頭台灣供應鏈情報庫</h2>
            <p style="color: #64748b; font-size: 0.92rem; margin: 0;">多使用者身分認證系統 ｜ 權限同步對接 V25.2</p>
        </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1.2, 2, 1.2])
    with col_m:
        user_input = st.text_input("👤 使用者名稱 (帳號)", placeholder="例如: admin、vip 或 user1").strip()
        pwd_input = st.text_input("🔑 登入密碼", type="password", placeholder="請輸入密碼...")
        
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
        
        st.caption("💡 預設測試帳號：`admin` (密碼 `v25`) ｜ `vip` (密碼 `v25`) ｜ `user1` (密碼 `123`)")
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

def apply_vendor_market_update(code, res):
    v = st.session_state["db"]["vendors"][code]
    raw_price = res["raw_price"]
    v["price"] = res["price"]
    v["price_date"] = res.get("date", datetime.now().strftime("%Y-%m-%d"))
    v["last_synced_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        raw_eps = float(str(v.get("eps_4q", "0")).replace("元", "").replace(",", "").strip())
        if raw_eps > 0:
            v["trailing_pe"] = f"{round(raw_price / raw_eps, 1)} 倍"
    except Exception:
        pass

    try:
        target_str = str(v.get("target_price", "0")).split("~")[0].replace("元", "").replace(",", "").strip()
        raw_target = float(target_str)
        if raw_target > 0:
            upside = round(((raw_target - raw_price) / raw_price) * 100, 1)
            v["upside_pot"] = f"{'+' if upside >= 0 else ''}{upside}%"
    except Exception:
        pass

    st.session_state["db"]["last_global_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(st.session_state["db"], f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"本地存檔警示: {e}")

# ==============================================================================
# 主程式介面
# ==============================================================================
def main():
    last_sync_info = db.get("last_global_sync", "2026-09-04 08:30:00")
    user_name = st.session_state.get("user_name", "會員")
    role_badge = "👑 VIP 尊榮權限" if current_role == "VIP" else "👤 一般會員權限"
    
    st.markdown(f"""
        <div class="hero-banner">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <h1 class="hero-title">🌐 科技巨頭台灣供應鏈情報庫</h1>
                    <p class="hero-sub">AI 算力 ＆ 低軌衛星 ＆ 車用電子 ＆ 光通訊 ＆ 智慧機器人 ｜ 整合巨鯨 V25.2 系統直連</p>
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
        # V25.2 網址設定（自動保存）
        st.subheader("🔗 巨鯨 V25.2 網頁直連網址")
        saved_v25_url = users_payload.get("settings", {}).get("v25_default_url", "")
        v25_ext_url = st.text_input(
            "貼上你的 V25.2 網頁網址",
            value=st.session_state.get("v25_ext_url", saved_v25_url),
            placeholder="例如: https://xxx.streamlit.app"
        ).strip()
        
        if v25_ext_url != saved_v25_url:
            st.session_state["v25_ext_url"] = v25_ext_url
            users_payload.setdefault("settings", {})["v25_default_url"] = v25_ext_url
            save_users_data(users_payload)
            st.success("✅ V25.2 網址已儲存更新！")

        if not v25_ext_url:
            st.warning("⚠️ 尚未設定 V25 網址，請先打開你的 V25.2 網頁並將網址複製貼在此處，按鈕即可自動連動！")
        else:
            st.caption(f"🎯 已綁定目標：`{v25_ext_url}`")

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
            for c, v in matched.items():
                render_vendor_card_with_sync(c, v)
        else:
            st.warning("未找到符合條件的供應商。")
        st.markdown("---")

    # 首頁三大分頁
    tabs = st.tabs(["🏢 SECTION A：國際大客戶專區", "🌐 SECTION B：五大戰略產業鏈全景", "📑 全 87 家廠商總表"])

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
                                render_vendor_card_with_sync(scode, v)
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
                                    render_vendor_card_with_sync(code, v)
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
        df_list = []
        for code, v in vendors.items():
            df_list.append({
                "股票代號": code,
                "公司名稱": v["name"],
                "次領域環節": v.get("sub_segment", "-"),
                "產業層級": v.get("tier", "-"),
                "最新收盤價": v.get("price", "-"),
                "動態本益比": v.get("trailing_pe", "-"),
                "近四季EPS": v.get("eps_4q", "-"),
                "法人目標價": v.get("target_price", "-") if current_role == "VIP" else "🔒 VIP 解鎖",
                "潛在空間": v.get("upside_pot", "-") if current_role == "VIP" else "🔒 VIP 解鎖",
                "毛利率": v.get("margin", "-"),
                "報價日期": v.get("price_date", "-")
            })
        st.dataframe(pd.DataFrame(df_list), use_container_width=True)

def render_vendor_card_with_sync(code, v):
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
            
            st.markdown(f"""
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
                        <span>動態本益比: <strong style="color: #059669; font-size: 1.15rem;">{v.get('trailing_pe', '-')}</strong></span>
                    </div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">
                        📅 報價日期: {date_badge}{ts_label}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_btn:
            st.write("")
            # 按鈕 1：更新行情
            if st.button("🔄 更新行情", key=f"btn_sync_{code}", use_container_width=True):
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

            # 按鈕 2：直通 V25.2 獨立網頁完整分析（依使用者要求，絕不跳 404）
            v25_url = st.session_state.get("v25_ext_url", "").strip()
            
            if v25_url and v25_url.startswith("http"):
                # 確保網址格式正確（去除結尾斜線，再加參數）
                clean_base_url = v25_url.rstrip("/")
                cur_user = st.session_state.get("current_user", "vip")
                cur_pwd = st.session_state.get("user_pwd", "")
                target_link = f"{clean_base_url}?stock={code}&user={cur_user}&pwd={cur_pwd}&role={current_role}"
                st.link_button("🐋 前往 V25.2 分析 ↗", target_link, use_container_width=True)
            else:
                if st.button("🐋 前往 V25.2 分析", key=f"btn_v25_alert_{code}", use_container_width=True):
                    st.info(f"💡 請先在左側側邊欄「🔗 巨鯨 V25.2 網頁直連網址」貼上你的 V25.2 真實網址，即可一鍵跳轉至該網頁為 {v['name']} ({code}) 進行完整分析！")

        # 展開基本面情報抽屜
        with st.expander(f"🔍 檢視 {v['name']} ({code}) 完整基本面情報檔案"):
            st.markdown(f"**核心合作客戶**：{', '.join(v.get('clients', []))}")
            st.markdown(f"**業務純度佔比**：`{v.get('pure_share', '-')}` ｜ **最新毛利率**：`{v.get('margin', '-')}`")

            st.markdown("##### 📊 各戰略領域營收比重拆解")
            for item in v.get("domain_breakdown", []):
                st.write(f"{item['domain']}: {item['share']}%")
                st.progress(item['share'] / 100)

            st.markdown(f"**未來 2 年 CapEx**：`{v.get('capex_future_2y', '-')}` ({v.get('capex_yoy_increase', '-')})")
            st.caption(f"**支出目的**：{v.get('capex_purpose', '-')}")

            if current_role == "VIP":
                st.markdown(f"**法說成長指引**：{v.get('guidance', '-')}")
                st.markdown(f"**法人共識目標價**：`{v.get('target_price', '-')}` ({v.get('analyst_count', '-')})")
                if "upside_pot" in v:
                    st.markdown(f"**距離目標價空間**：`{v['upside_pot']}`")
            else:
                st.info("🔒 法說成長指引與法人共識目標價屬於 VIP 會員專屬內容，請升級帳號權限查閱。")

            if "last_synced_at" in v:
                st.caption(f"🕒 數據最後更新時間：{v['last_synced_at']} (已永久保存至硬碟)")

            st.markdown("##### 📑 官方數據出處佐證")
            for s in v.get("sources", []):
                st.markdown(f"- **[{s.get('date', '最新')}]** [{s['title']}]({s['url']})")

if __name__ == "__main__":
    main()
