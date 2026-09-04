"""
================================================================================
科技巨頭台灣供應鏈情報庫 - Streamlit 旗艦正式版 (第 2 次深度優化)
根據使用者反饋升級：
1. 頂部標籤頁 (Tabs) 字體放大 1.22 倍，且當前選中頁面加粗體 (800) 並高亮顯示！
2. 點擊「檢視供應鏈」或「進入產業鏈」按鈕後，直接穿透進入下一層專屬獨立頁面（隱藏上層卡片），
   並於頂部設置清晰的「← 返回清單」按鈕，徹底告別下方堆疊排版的混亂感！
3. 永久磁碟保存機制：每次單股更新或批次更新，資料與精確日期時間（price_date、last_synced_at）
   立即寫入 master_supply_chain_db.json 保存，明日開啟絕不流失！
4. 保留每家廠商專屬的「🔄 更新行情」按鈕，以及正下方的「🐋 V25.2 分析」按鈕與獨立網頁跳轉！
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

# 使用絕對路徑以確保本地或雲端環境皆能準確寫入磁碟保存
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_supply_chain_db.json")

# ==============================================================================
# 注入全域自訂 CSS：分頁字體放大 1.22 倍、選中標籤加粗高亮
# ==============================================================================
st.markdown("""
<style>
    /* 1. 分頁標籤欄字體放大 1.22 倍 */
    div[data-baseweb="tab-list"] {
        gap: 12px !important;
        margin-bottom: 24px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    div[data-baseweb="tab-list"] button[role="tab"] {
        font-size: 1.22rem !important;
        padding: 12px 26px !important;
        letter-spacing: 0.02em !important;
        border-radius: 10px 10px 0 0 !important;
        transition: all 0.25s ease !important;
    }
    /* 當前選中的標籤頁：字體變粗體 (800) + 高亮亮藍 + 底部邊框 */
    div[data-baseweb="tab-list"] button[aria-selected="true"] {
        font-weight: 800 !important;
        color: #38bdf8 !important;
        border-bottom: 3.5px solid #38bdf8 !important;
        background: rgba(56, 189, 248, 0.08) !important;
    }
    /* 未選中的標籤頁：中等字重 + 灰階 */
    div[data-baseweb="tab-list"] button[aria-selected="false"] {
        font-weight: 500 !important;
        color: #94a3b8 !important;
    }
    div[data-baseweb="tab-list"] button[role="tab"]:hover {
        color: #f1f5f9 !important;
        background: rgba(255, 255, 255, 0.04) !important;
    }

    /* 頂部橫幅微光樣式 */
    .hero-banner {
        padding: 18px 24px;
        background: linear-gradient(135deg, #0b1329 0%, #1e1b4b 100%);
        border-radius: 18px;
        border: 1px solid rgba(56,189,248,0.28);
        margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(2, 132, 199, 0.2);
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

    /* 廠商卡片專屬樣式 */
    .company-card {
        padding: 12px 16px;
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        background: rgba(255,255,255,0.025);
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 資料庫載入與 Session State 管理（無快取，磁碟持久化）
# ==============================================================================
def init_database():
    """初始化並將資料庫置入 session_state，確保所有修改立即連動至畫面上"""
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
        
        # 1. 擬真隨機安全延遲 (V25.2 防爬設定)
        if apply_delay:
            delay_time = random.uniform(1.5, 3.0)
            if status_placeholder:
                status_placeholder.text(f"⏳ 正在載入 {stock_id} ... (擬真防爬安全延遲 {delay_time:.2f} 秒)")
            time.sleep(delay_time)

        # 2. 方案 A：yfinance (優先，支援上市櫃自動重試)
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
                            "source": f"yfinance ({code})",
                            "status": "success"
                        }, None
                except Exception:
                    continue
        except Exception:
            pass

        # 3. 方案 B：台灣證交所/櫃買中心官方 MIS API 備援 (免 Token、即時穩定)
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
                            "source": "TWSE/TPEx MIS 官方即時接口",
                            "status": "success"
                        }, None
        except Exception:
            pass

        # 4. 方案 C：FinMind 免費版備援
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
                        "source": "FinMind 免費版",
                        "status": "success"
                    }, None
            except Exception:
                pass

        return None, "所有資料管道皆無法連線或查無此代碼資料"

def apply_vendor_market_update(code, res):
    """
    更新數值並永久保存至磁碟 JSON 檔案中，確保明日開啟時資料不流失
    """
    v = st.session_state["db"]["vendors"][code]
    raw_price = res["raw_price"]
    v["price"] = res["price"]
    v["price_date"] = res.get("date", datetime.now().strftime("%Y-%m-%d"))
    v["last_synced_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 自動重算動態本益比：PE = 當日最新價 / 近四季 EPS
    try:
        raw_eps = float(str(v.get("eps_4q", "0")).replace("元", "").replace(",", "").strip())
        if raw_eps > 0:
            v["trailing_pe"] = f"{round(raw_price / raw_eps, 1)} 倍"
    except Exception:
        pass

    # 2. 自動重算距離法人目標價潛在空間
    try:
        target_str = str(v.get("target_price", "0")).split("~")[0].replace("元", "").replace(",", "").strip()
        raw_target = float(target_str)
        if raw_target > 0:
            upside = round(((raw_target - raw_price) / raw_price) * 100, 1)
            v["upside_pot"] = f"{'+' if upside >= 0 else ''}{upside}%"
    except Exception:
        pass

    # 3. 記錄全域最後更新時間戳記
    st.session_state["db"]["last_global_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 4. 永久寫入硬碟 JSON 檔保存！
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(st.session_state["db"], f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"本地磁碟存檔警示: {e}")

# ==============================================================================
# V25.2 量化分析引擎執行模組 (WhaleEngine 整合)
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
# 主程式畫面佈局
# ==============================================================================
def main():
    last_sync_info = db.get("last_global_sync", "2026-09-04 08:30:00")
    
    st.markdown(f"""
        <div class="hero-banner">
            <h1 class="hero-title">🌐 科技巨頭台灣供應鏈情報庫</h1>
            <p class="hero-sub">
                AI 算力 ＆ 低軌衛星 ＆ 車用電子 ＆ 光通訊 ＆ 智慧機器人 ｜ 整合 V25.2 籌碼量價實戰引擎 ｜ 
                <span style="color: #38bdf8; font-weight: 600;">🕒 全庫行情基準日：{last_sync_info}</span>
            </p>
        </div>
    """, unsafe_allow_html=True)

    # 側邊欄控制台
    with st.sidebar:
        st.header("⚙️ 系統設定與連網同步")
        
        st.subheader("🔗 獨立 V25.2 網頁跳轉設定")
        v25_ext_url = st.text_input(
            "輸入你的獨立 V25.2 網址 (選填)",
            value=st.session_state.get("v25_ext_url", ""),
            placeholder="例如: https://whale-engine-web.streamlit.app"
        )
        st.session_state["v25_ext_url"] = v25_ext_url.strip()
        if v25_ext_url:
            st.caption("✅ 已設定！點擊各股「V25.2 分析」可直接跳轉至你的獨立網頁。")

        st.markdown("---")
        st.subheader("🔑 FinMind 免費版設定")
        fm_token = st.text_input("FinMind Token (選填，留空使用免費免登入模式)", type="password")
        st.session_state["fm_token"] = fm_token
        
        st.markdown("---")
        st.subheader("🔄 批次即時行情對齊")
        st.caption("💡 內建 V25.2 擬真延遲 (1.5~3.0秒)，模擬真人看盤，防爬蟲封鎖。")
        batch_count = st.slider("單次更新個股數量", min_value=5, max_value=len(vendors), value=15, step=5)
        
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
            
            status_box.success(f"✅ 成功完成 {success_count} 檔個股最新行情與動態本益比更新，已永久保存至硬碟！")
            time.sleep(1)
            st.rerun()

        st.markdown("---")
        st.subheader("🔍 全域快速檢索")
        search_query = st.text_input("搜尋股票代號或名稱", placeholder="例：2330、尖點、盟立、6442...")

    # 搜尋結果優先呈現
    if search_query:
        st.subheader(f"🔍 搜尋結果：'{search_query}'")
        matched = {c: v for c, v in vendors.items() if search_query in c or search_query in v["name"] or search_query in v.get("products", "")}
        if matched:
            for c, v in matched.items():
                render_vendor_card_with_sync(c, v)
        else:
            st.warning("未找到符合條件的供應商。")
        st.markdown("---")

    # ==========================================================================
    # 首頁分頁（自訂 CSS 放大 1.22 倍並加粗當前選中項）
    # ==========================================================================
    tabs = st.tabs(["🏢 SECTION A：國際大客戶專區", "🌐 SECTION B：五大戰略產業鏈全景", "📑 全 87 家廠商總表"])

    # --- SECTION A: 國際客戶專區 (分層穿透架構) ---
    with tabs[0]:
        selected_client = st.session_state.get("selected_client")
        
        # 依反饋 2：若點選客戶，直接進入下一層專屬頁面，不堆疊在下方！
        if selected_client and selected_client in clients:
            c = clients[selected_client]
            
            # 頂部導航返回列
            c_back, c_info = st.columns([1.8, 8.2])
            with c_back:
                if st.button("← 返回大客戶清單", key="btn_back_clients", use_container_width=True):
                    st.session_state["selected_client"] = None
                    st.rerun()
            with c_info:
                st.markdown(f"<h3 style='margin:0; color:#38bdf8;'>🎯 {c['icon']} {c['name']} 在台專屬供應鏈全景名單</h3>", unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style="padding: 14px 18px; background: rgba(15,23,42,0.6); border: 1px solid rgba(56,189,248,0.3); border-radius: 12px; margin: 16px 0 20px 0;">
                    <p style="margin: 0; color: #cbd5e1; font-size: 0.95rem;">{c['desc']}</p>
                    <div style="display: flex; gap: 18px; margin-top: 8px; font-size: 0.88rem; flex-wrap: wrap;">
                        <span style="color: #6ee7b7;">💰 <strong>資本支出</strong>：{c.get('capex_forecast', '-')}</span>
                        <span style="color: #38bdf8;">🎯 <strong>採購焦點</strong>：{c['key_focus']}</span>
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
            # 第一層：展示 8 大客戶卡片總覽
            st.markdown("""
                <div style="padding: 14px 18px; background: rgba(12, 22, 42, 0.85); border: 1.5px solid rgba(56, 189, 248, 0.4); border-radius: 14px; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #38bdf8;">🏢 國際科技巨頭下單專區（在台採購核心）</h3>
                    <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 0.88rem;">點選任一國際大廠按鈕，畫面直接進入該客戶之在台專屬供應鏈頁面</p>
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
        
        # 依反饋 2：若點選產業鏈，直接進入下一層樹狀圖，不堆疊在下方！
        if selected_domain and selected_domain in domains:
            d = domains[selected_domain]
            
            # 頂部導航返回列
            d_back, d_info = st.columns([1.8, 8.2])
            with d_back:
                if st.button("← 返回五大主題清單", key="btn_back_domains", use_container_width=True):
                    st.session_state["selected_domain"] = None
                    st.rerun()
            with d_info:
                st.markdown(f"<h3 style='margin:0; color:#c084fc;'>🌐 {d['icon']} {d['name']} 完整產業鏈樹狀圖譜</h3>", unsafe_allow_html=True)

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
            # 第一層：展示 5 大產業鏈入口卡片
            st.markdown("""
                <div style="padding: 14px 18px; background: rgba(26, 17, 46, 0.85); border: 1.5px solid rgba(192, 132, 252, 0.4); border-radius: 14px; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #c084fc;">🌐 五大戰略產業鏈主題全景區</h3>
                    <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 0.88rem;">點選任一主題按鈕，直接進入該產業之完整上中下游樹狀導航頁面</p>
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
    1. 卡片旁設置「🔄 更新行情」按鈕
    2. 下方緊接著設置「🐋 V25.2 分析」按鈕
    """
    card_container = st.container()
    with card_container:
        col_main, col_btn = st.columns([3.6, 1.4])
        
        with col_main:
            date_badge = v.get('price_date', '最新')
            sync_ts = v.get('last_synced_at', '')
            ts_label = f" (更新於: {sync_ts.split(' ')[1]})" if sync_ts else ""
            
            st.markdown(f"""
                <div class="company-card">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <span style="font-size: 1.15rem; font-weight: 700; color: #ffffff;">{v['name']} ({code})</span>
                        <span style="color: #38bdf8; font-size: 0.8rem; background: rgba(56,189,248,0.15); padding: 2px 6px; border-radius: 4px;">{v.get('tier', '供應鏈')}</span>
                    </div>
                    <div style="font-size: 0.84rem; color: #cbd5e1; margin: 4px 0;">{v.get('products', '-')}</div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #94a3b8; margin-top: 6px;">
                        <span>最新股價: <strong style="color: #38bdf8; font-size: 1.05rem;">{v.get('price', '-')}</strong></span>
                        <span>動態本益比: <strong style="color: #34d399; font-size: 1.05rem;">{v.get('trailing_pe', '-')}</strong></span>
                    </div>
                    <div style="font-size: 0.73rem; color: #64748b; margin-top: 4px;">
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

            # 按鈕 2：V25.2 分析按鈕（置於更新按鈕正下方！）
            if st.button("🐋 V25.2 分析", key=f"btn_v25_{code}", use_container_width=True):
                st.session_state[f"show_v25_{code}"] = not st.session_state.get(f"show_v25_{code}", False)

        # 展開 V25.2 深度分析面板（點擊按鈕後於卡片下方展開）
        if st.session_state.get(f"show_v25_{code}", False):
            render_v25_analysis_panel(code, v)

        # 展開基本面情報抽屜
        with st.expander(f"🔍 檢視 {v['name']} 完整基本面情報檔案"):
            st.markdown(f"**核心合作客戶**：{', '.join(v.get('clients', []))}")
            st.markdown(f"**業務純度佔比**：`{v.get('pure_share', '-')}` ｜ **最新毛利率**：`{v.get('margin', '-')}`")

            # 業務領域營收比重進度條
            st.markdown("##### 📊 各戰略領域營收比重拆解")
            for item in v.get("domain_breakdown", []):
                st.write(f"{item['domain']}: {item['share']}%")
                st.progress(item['share'] / 100)

            # 資本支出
            st.markdown(f"**未來 2 年 CapEx**：`{v.get('capex_future_2y', '-')}` ({v.get('capex_yoy_increase', '-')})")
            st.caption(f"**支出目的**：{v.get('capex_purpose', '-')}")

            # 法說展望與目標價
            st.markdown(f"**法說成長指引**：{v.get('guidance', '-')}")
            st.markdown(f"**法人共識目標價**：`{v.get('target_price', '-')}` ({v.get('analyst_count', '-')})")
            if "upside_pot" in v:
                st.markdown(f"**距離目標價空間**：`{v['upside_pot']}`")

            if "last_synced_at" in v:
                st.caption(f"🕒 數據最後更新時間：{v['last_synced_at']} (已保存至硬碟)")

            # 官方佐證連結
            st.markdown("##### 📑 官方數據出處佐證")
            for s in v.get("sources", []):
                st.markdown(f"- **[{s.get('date', '最新')}]** [{s['title']}]({s['url']})")

def render_v25_analysis_panel(code, v):
    """渲染 V25.2 實盤量化診斷卡片與獨立網頁跳轉"""
    st.markdown(f"""
        <div style="padding: 14px; background: rgba(30, 27, 75, 0.55); border: 1.5px solid #818cf8; border-radius: 12px; margin: 10px 0 16px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h4 style="margin: 0; color: #c7d2fe;">🐋 V25.2 PRO 實戰量化診斷：{v['name']} ({code})</h4>
                <span style="font-size: 0.8rem; color: #a5b4fc;">大鯨魚多因子決策系統</span>
            </div>
    """, unsafe_allow_html=True)

    # 1. 外部獨立網頁跳轉
    v25_url = st.session_state.get("v25_ext_url", "")
    if v25_url:
        target_link = f"{v25_url}/?stock={code}"
        st.link_button(f"🌐 在獨立 V25.2 網頁開啟 {v['name']} ({code}) ➔", target_link, use_container_width=True)

    # 2. 本地執行 V25.2 模組
    if f"v25_res_{code}" not in st.session_state:
        with st.spinner(f"正在啟動 V25.2 量化引擎分析 {v['name']} (擬真防爬安全延遲)..."):
            res, err = run_v25_analysis(code)
            if res:
                st.session_state[f"v25_res_{code}"] = res
            else:
                st.error(f"V25.2 本地運算警示: {err}")
                st.info("提示：若本地資料不足，亦可直接使用上方按鈕跳轉至你的獨立 V25.2 網頁查看！")

    res = st.session_state.get(f"v25_res_{code}")
    if res:
        f_info = res.get("fish", {})
        r_info = res.get("retreat", {})
        d_info = res.get("defense", {})
        p_info = res.get("position", {})
        w_info = res.get("warning", {})
        fund_info = res.get("fundamental", {})

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🐟 魚頭分數", f"{f_info.get('fish_score', 0)} 分", delta=f"健康: {f_info.get('health_grade', '-')}")
        with c2:
            st.metric("🚨 撤退風險", f_info.get('trend_status', r_info.get('risk_status', '正常')), delta_color="inverse")
        with c3:
            st.metric("🛡️ 實戰防守價 (ATR)", f"{d_info.get('defense_price', 0)} 元")
        with c4:
            st.metric("⚓ 主力加權均價 (60日)", f"{d_info.get('vwap60', 0)} 元")

        st.markdown(f"**魚體位置**：`{p_info.get('position_desc', '主升初期')}` ｜ **保守目標區**：`{d_info.get('target_low', '-')} ~ {d_info.get('target_high', '-')}`")
        st.markdown(f"**基本面營收狀態**：`{fund_info.get('revenue_tag', '-')}` (YoY: {fund_info.get('yoy', '-')})")
        st.markdown(f"**綜合預警提示**：`{w_info.get('warning_state', '正常')}`")

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
