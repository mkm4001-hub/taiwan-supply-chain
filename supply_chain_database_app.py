"""
================================================================================
科技巨頭台灣供應鏈情報庫 - Streamlit 旗艦正式版 (第 3 次深度升級)
根據使用者最新反饋全面升級：
1. 【公司名稱與股號字體放大 2 倍】：
   - 全面修復淺色/深色模式配色衝突，公司名稱與股號放大至 1.85rem (約2倍大)，加粗呈現「公司名稱 (股號)」，保證在白底與黑底均清晰醒目！
2. 【全站密碼登入保護機制】：
   - 內建密碼驗證閘門，需輸入與 V25.2 相同的密碼方可解鎖，未授權者無法存取。
3. 【直通獨立 V25.2 程式進行完整分析】：
   - 在「更新行情」正下方設置「🐋 V25.2 完整分析 ↗」按鈕，點擊後直接新開分頁跳轉至你的獨立 V25.2 網頁，
     並於網址自動附帶股票代號與授權金鑰 (?stock=2330&auth=...)，無縫啟動完整大局透視分析！
4. 【永久磁碟保存與資料日期】：
   - 更新資料即刻寫入硬碟 JSON 檔保存，標註精確報價日期與更新時間，明日開啟絕不流失。
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
    page_title="科技巨頭台灣供應鏈情報庫 (V25.2 整合版)",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 系統預設存取密碼（使用者可隨時在此修改為與 V25.2 相同之密碼）
DEFAULT_SYSTEM_PASSWORD = "pwd001!"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_supply_chain_db.json")

# ==============================================================================
# 全域自訂 CSS（適應深色/淺色主題，字體放大與選中標籤加粗）
# ==============================================================================
st.markdown("""
<style>
    /* 1. 分頁標籤欄字體放大 1.22 倍 */
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
    /* 當前選中的標籤頁：字體變粗體 (800) + 高亮 + 底部線 */
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

    /* 頂部橫幅樣式 */
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

    /* 廠商卡片專屬樣式 (自適應雙色模式) */
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
# 密碼驗證閘門（只有輸入正確密碼才可存取整個情報庫）
# ==============================================================================
def check_password_auth():
    """系統密碼驗證閘門，未授權者無法查看與存取資料庫"""
    if st.session_state.get("authenticated", False):
        return True

    st.markdown("""
        <div style="max-width: 520px; margin: 50px auto 24px auto; padding: 28px; border-radius: 18px; border: 2px solid #0284c7; background: rgba(2, 132, 199, 0.04); text-align: center;">
            <div style="font-size: 2.8rem; margin-bottom: 10px;">🔒</div>
            <h2 style="color: #0284c7; margin: 0 0 8px 0; font-weight: 800;">科技巨頭台灣供應鏈情報庫</h2>
            <p style="color: #64748b; font-size: 0.92rem; margin: 0;">請輸入系統存取密碼以進行身分認證（可與 V25.2 設定相同）</p>
        </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1.2, 2, 1.2])
    with col_m:
        entered_pwd = st.text_input("存取密碼", type="password", key="input_system_pwd", placeholder="請輸入授權密碼...")
        if st.button("🔐 驗證登入 ➔", use_container_width=True):
            # 支援從 Streamlit Secrets 或預設變數比對
            correct_pwd = st.secrets.get("PASSWORD", DEFAULT_SYSTEM_PASSWORD)
            if entered_pwd == correct_pwd:
                st.session_state["authenticated"] = True
                st.session_state["user_pwd"] = entered_pwd
                st.success("✅ 認證成功，正在載入資料庫...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 密碼錯誤！未獲授權無法存取情報庫。")
    return False

# 執行驗證閘門
if not check_password_auth():
    st.stop()

# ==============================================================================
# 資料庫載入與 Session State 管理
# ==============================================================================
def init_database():
    if "db" not in st.session_state:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r", encoding="utf-8") as f:
                st.session_state["db"] = json.load(f)
        else:
            st.error(f"找不到資料庫母檔 {DB_PATH}，請確認檔案與此程式在同一資料夾。")
            st.stop()

init_database()
db = st.session_state["db"]
clients = db["clients"]
domains = db["domains"]
vendors = db["vendors"]

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
        
        # 1. 擬真隨機安全延遲
        if apply_delay:
            delay_time = random.uniform(1.5, 3.0)
            if status_placeholder:
                status_placeholder.text(f"⏳ 正在載入 {stock_id} ... (擬真防爬安全延遲 {delay_time:.2f} 秒)")
            time.sleep(delay_time)

        # 2. yfinance 雙軌切換
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

        # 3. 台灣證交所/櫃買中心官方 MIS API 備援 (免 Token 即時線路)
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

        # 4. FinMind 免費版備援
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

        return None, "所有資料管道皆無法連線或查無此代碼資料"

def apply_vendor_market_update(code, res):
    v = st.session_state["db"]["vendors"][code]
    raw_price = res["raw_price"]
    v["price"] = res["price"]
    v["price_date"] = res.get("date", datetime.now().strftime("%Y-%m-%d"))
    v["last_synced_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 動態本益比重算
    try:
        raw_eps = float(str(v.get("eps_4q", "0")).replace("元", "").replace(",", "").strip())
        if raw_eps > 0:
            v["trailing_pe"] = f"{round(raw_price / raw_eps, 1)} 倍"
    except Exception:
        pass

    # 2. 距離目標價空間重算
    try:
        target_str = str(v.get("target_price", "0")).split("~")[0].replace("元", "").replace(",", "").strip()
        raw_target = float(target_str)
        if raw_target > 0:
            upside = round(((raw_target - raw_price) / raw_price) * 100, 1)
            v["upside_pot"] = f"{'+' if upside >= 0 else ''}{upside}%"
    except Exception:
        pass

    st.session_state["db"]["last_global_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 寫入磁碟保存
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(st.session_state["db"], f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"本地磁碟存檔警示: {e}")

# ==============================================================================
# V25.2 量化分析模組
# ==============================================================================
def run_v25_analysis(stock_id):
    try:
        import v25_engine_core as v25
        fm_token = st.session_state.get("fm_token", "")
        whale_eng = v25.WhaleEngine(token=fm_token)
        res = whale_eng.analyze(stock_id=stock_id, mode='after_market')
        return res, None
    except Exception as e:
        return None, str(e)

# ==============================================================================
# 主程式介面
# ==============================================================================
def main():
    last_sync_info = db.get("last_global_sync", "2026-09-04 08:30:00")
    
    st.markdown(f"""
        <div class="hero-banner">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h1 class="hero-title">🌐 科技巨頭台灣供應鏈情報庫</h1>
                    <p class="hero-sub">AI 算力 ＆ 低軌衛星 ＆ 車用電子 ＆ 光通訊 ＆ 智慧機器人 ｜ 整合 V25.2 實戰大局引擎</p>
                </div>
                <div style="font-size: 0.86rem; color: #94a3b8; background: rgba(0,0,0,0.3); padding: 8px 14px; border-radius: 8px;">
                    🕒 行情基準日：<strong style="color: #38bdf8;">{last_sync_info}</strong>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 側邊欄控制台
    with st.sidebar:
        st.header("⚙️ 系統設定與 V25.2 連動")
        
        # 登入狀態與登出
        st.success("✅ 存取授權狀態：已安全登入")
        if st.button("🔒 登出系統", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

        st.markdown("---")
        st.subheader("🔗 獨立 V25.2 網頁網址設定")
        v25_ext_url = st.text_input(
            "輸入你的獨立 V25.2 網址",
            value=st.session_state.get("v25_ext_url", "https://whale-engine-web.streamlit.app"),
            placeholder="例如: https://whale-engine-web.streamlit.app"
        )
        st.session_state["v25_ext_url"] = v25_ext_url.strip()

        st.markdown("---")
        st.subheader("🔑 FinMind 免費版 Token")
        fm_token = st.text_input("FinMind Token (選填，留空為免費模式)", type="password")
        st.session_state["fm_token"] = fm_token
        
        st.markdown("---")
        st.subheader("🔄 全體批次行情同步")
        batch_count = st.slider("單次更新數量", min_value=5, max_value=len(vendors), value=15, step=5)
        
        if st.button("🚀 啟動 V25.2 批次擬真安全同步", use_container_width=True):
            engine = V25MarketSyncEngine(finmind_token=fm_token)
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

    # 首頁分頁
    tabs = st.tabs(["🏢 SECTION A：國際大客戶專區", "🌐 SECTION B：五大戰略產業鏈全景", "📑 全 87 家廠商總表"])

    # --- SECTION A: 國際客戶專區 (分層穿透架構) ---
    with tabs[0]:
        selected_client = st.session_state.get("selected_client")
        
        if selected_client and selected_client in clients:
            c = clients[selected_client]
            
            # 頂部返回按鈕列
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

    # --- SECTION B: 五大產業鏈全景 (分層穿透架構) ---
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
        st.subheader("📊 全體 87 家上市櫃供應商總覽表 (含最新股價與即時本益比)")
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
                "法人目標價": v.get("target_price", "-"),
                "潛在空間": v.get("upside_pot", "-"),
                "毛利率": v.get("margin", "-"),
                "報價日期": v.get("price_date", "-"),
                "最後更新時間": v.get("last_synced_at", "初始資料")
            })
        st.dataframe(pd.DataFrame(df_list), use_container_width=True)

def render_vendor_card_with_sync(code, v):
    """
    渲染單一公司卡片：
    1. 【公司名稱與股號字體放大 2 倍】(1.85rem)，無論深色淺色模式皆醒目！
    2. 右側設置「🔄 更新行情」以及緊接著正下方的「🐋 V25.2 完整分析 ↗」按鈕！
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

            # 按鈕 2：V25.2 完整分析按鈕（依需求緊接在更新按鈕正下方！）
            v25_url = st.session_state.get("v25_ext_url", "https://whale-engine-web.streamlit.app")
            user_pwd = st.session_state.get("user_pwd", DEFAULT_SYSTEM_PASSWORD)
            target_link = f"{v25_url}/?stock={code}&auth={user_pwd}"

            # 直通跳轉至你的獨立 V25.2 網頁！
            st.link_button("🐋 V25.2 分析 ↗", target_link, use_container_width=True)

        # 展開深度情報抽屜（公司名與股號同樣放大且清晰）
        with st.expander(f"🔍 檢視 {v['name']} ({code}) 完整基本面情報檔案"):
            st.markdown(f"**核心合作客戶**：{', '.join(v.get('clients', []))}")
            st.markdown(f"**業務純度佔比**：`{v.get('pure_share', '-')}` ｜ **最新毛利率**：`{v.get('margin', '-')}`")

            st.markdown("##### 📊 各戰略領域營收比重拆解")
            for item in v.get("domain_breakdown", []):
                st.write(f"{item['domain']}: {item['share']}%")
                st.progress(item['share'] / 100)

            st.markdown(f"**未來 2 年 CapEx**：`{v.get('capex_future_2y', '-')}` ({v.get('capex_yoy_increase', '-')})")
            st.caption(f"**支出目的**：{v.get('capex_purpose', '-')}")

            st.markdown(f"**法說成長指引**：{v.get('guidance', '-')}")
            st.markdown(f"**法人共識目標價**：`{v.get('target_price', '-')}` ({v.get('analyst_count', '-')})")
            if "upside_pot" in v:
                st.markdown(f"**距離目標價空間**：`{v['upside_pot']}`")

            if "last_synced_at" in v:
                st.caption(f"🕒 數據最後更新時間：{v['last_synced_at']} (已永久保存至硬碟)")

            st.markdown("##### 📑 官方數據出處佐證")
            for s in v.get("sources", []):
                st.markdown(f"- **[{s.get('date', '最新')}]** [{s['title']}]({s['url']})")

if __name__ == "__main__":
    main()
