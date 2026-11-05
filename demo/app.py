import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from fredapi import Fred
from google import genai  # Google 官方 GenAI SDK

# 1. 頁面基本配置
st.set_page_config(page_title="總體經濟與金融即時儀表板", layout="wide")
st.title("🌐 全球總體經濟與金融指標即時儀表板")

# 2. 側邊欄：設定與金鑰輸入
st.sidebar.header("⚙️ 設定與金鑰")

# 讀取 FRED API Key (優先從 Streamlit Secrets，否則從側邊欄輸入)
if "FRED_API_KEY" in st.secrets:
    fred_key = st.secrets["FRED_API_KEY"]
    st.sidebar.success("已自動讀取 FRED API Key！")
else:
    fred_key = st.sidebar.text_input("請輸入你的 FRED API Key:", type="password")

# 讀取 Gemini API Key (優先從 Streamlit Secrets，否則從側邊欄輸入)
if "GEMINI_API_KEY" in st.secrets:
    gemini_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("已自動讀取 Gemini API Key！")
else:
    gemini_key = st.sidebar.text_input("請輸入你的 Gemini API Key:", type="password")

if st.sidebar.button("手動刷新所有數據"):
    st.cache_data.clear()
    st.success("快取已清除，正在重新抓取資料...")

# 3. 抓取 FRED 數據並計算利差 (設快取 1 小時)
@st.cache_data(ttl=3600)
def get_fred_data(api_key):
    fred = Fred(api_key=api_key)
    data = {
        "CPI 物價指數": fred.get_series("CPIAUCSL"),
        "10年期美債殖利率": fred.get_series("DGS10"),
        "2年期美債殖利率": fred.get_series("DGS2"),
        "美國失業率": fred.get_series("UNRATE"),
        "聯邦基金利率": fred.get_series("FEDFUNDS"),
        "日本10年期公債殖利率": fred.get_series("IRLTLT01JPM156N")
    }
    df = pd.DataFrame(data).ffill().tail(365)
    # 計算 10 年期減 2 年期美債利差
    df["10-2年美債利差"] = df["10年期美債殖利率"] - df["2年期美債殖利率"]
    return df

# 4. 抓取 Market 數據 (設快取 10 分鐘)
@st.cache_data(ttl=600)
def get_market_data():
    tickers = {
        "S&P 500": "^GSPC",
        "台灣加權指數": "^TWII",
        "布蘭特原油": "BZ=F",
        "美元/台幣匯率": "TWD=X",
        "黃金現貨價格": "GC=F"
    }
    raw_data = yf.download(list(tickers.values()), period="1y")
    
    if isinstance(raw_data.columns, pd.MultiIndex):
        df = raw_data["Close"]
    else:
        df = raw_data[["Close"]]
        
    df.rename(columns={v: k for k, v in tickers.items()}, inplace=True)
    return df

# 5. 主頁面渲染邏輯
if fred_key:
    try:
        macro_df = get_fred_data(fred_key)
        market_df = get_market_data()

        # 取得最新各項數據數值（供 KPI 與 AI 摘要使用）
        latest_cpi = macro_df["CPI 物價指數"].dropna().iloc[-1]
        latest_rate = macro_df["10年期美債殖利率"].dropna().iloc[-1]
        rate_prev = macro_df["10年期美債殖利率"].dropna().iloc[-2]
        latest_unemp = macro_df["美國失業率"].dropna().iloc[-1]
        latest_fed = macro_df["聯邦基金利率"].dropna().iloc[-1]
        latest_spread = macro_df["10-2年美債利差"].dropna().iloc[-1]
        latest_jp = macro_df["日本10年期公債殖利率"].dropna().iloc[-1]
        jp_prev = macro_df["日本10年期公債殖利率"].dropna().iloc[-2]
        jp_diff = latest_jp - jp_prev

        # 顯示美債利差警示燈號
        if latest_spread < 0:
            st.warning(f"🚨 **【經濟衰退警示】美國公債殖利率曲線發生倒掛！** 當前 10 年期與 2 年期美債利差為 **{latest_spread:.2f}%**（小於 0）。")
        else:
            st.success(f"✅ 當前 10 年期與 2 年期美債利差為 **{latest_spread:.2f}%**（維持正常正斜率）。")

        # 第一區塊：核心 KPI 卡片 (5 等分)
        st.subheader("📊 關鍵總體經濟指標 (FRED)")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        col1.metric("CPI 物價指數", f"{latest_cpi:.1f}")
        col2.metric("10年美債殖利率", f"{latest_rate:.2f}%", f"{latest_rate - rate_prev:+.2f}%")
        col3.metric("美國失業率", f"{latest_unemp:.1f}%")
        col4.metric("聯邦基金利率", f"{latest_fed:.2f}%")
        
        if abs(jp_diff) < 0.005:
            col5.metric("日本10年期公債殖利率", f"{latest_jp:.2f}%")
        else:
            col5.metric("日本10年期公債殖利率", f"{latest_jp:.2f}%", f"{jp_diff:+.2f}%")

        # 第二區塊：互動式圖表 (Tabs)
        st.write("---")
        st.subheader("📈 市場走勢與總體指標折線圖")
        
        tab1, tab2 = st.tabs(["金融市場走勢 (yfinance)", "總體經濟趨勢 (FRED)"])
        
        with tab1:
            market_choice = st.selectbox("選擇金融市場標的：", market_df.columns, key="market_select")
            fig1 = px.line(market_df, y=market_choice, title=f"{market_choice} 近一年走勢")
            st.plotly_chart(fig1, use_container_width=True)
            
        with tab2:
            macro_choice = st.selectbox("選擇總體經濟指標：", macro_df.columns, key="macro_select")
            fig2 = px.line(macro_df, y=macro_choice, title=f"{macro_choice} 近一年走勢")
            st.plotly_chart(fig2, use_container_width=True)

        # 第三區塊：AI 總體經濟智慧摘要按鈕與介面
        st.write("---")
        st.subheader("🤖 AI 總體經濟智慧摘要")
        st.write("點擊下方按鈕，將自動調用 Gemini API 分析當前的 CPI、失業率、利率與殖利率狀態，為您產出一份 200 字左右的總體經濟專業短評。")

        if st.button("✨ 產生 AI 總體經濟摘要", type="primary"):
            if not gemini_key:
                st.error("❌ 偵測不到 Gemini API Key！請先在側邊欄輸入您的 Gemini API Key，或設定在 Streamlit Secrets 中。")
            else:
                with st.spinner("🚀 Gemini 正在分析當前總體經濟數據並撰寫短評..."):
                    try:
                        # 初始化 Google GenAI 客戶端
                        client = genai.Client(api_key=gemini_key)
                        
                        # 組合傳給 AI 的上下文提示詞
                        prompt_text = f"""
                        請根據以下最新抓取的全球總體經濟數據，撰寫一份約 200 字的專業總體經濟短評（繁體中文）：
                        - CPI 物價指數: {latest_cpi:.1f}
                        - 10 年期美債殖利率: {latest_rate:.2f}%
                        - 2 年期美債殖利率: {macro_df['2年期美債殖利率'].dropna().iloc[-1]:.2f}%
                        - 10-2年美債利差: {latest_spread:.2f}%
                        - 美國失業率: {latest_unemp:.1f}%
                        - 聯邦基金利率: {latest_fed:.2f}%
                        - 日本 10 年期公債殖利率: {latest_jp:.2f}%
                        
                        請精煉分析目前的通膨、利率環境以及殖利率曲線狀況對市場或投資人可能帶來的影響。
                        """
                        
                        # 呼叫 gemini-2.5-flash 模型
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=prompt_text,
                        )
                        
                        st.success("✅ AI 總體經濟摘要生成完畢：")
                        st.info(response.text)
                        
                    except Exception as ai_err:
                        st.error(f"⚠️ 呼叫 Gemini API 時發生錯誤: {ai_err}")

    except Exception as e:
        st.error(f"⚠️ 數據讀取失敗，請確認 FRED API Key 是否正確或網路連線是否正常。錯誤訊息: {e}")

else:
    st.info("👈 請先在左側側邊欄輸入您的 **FRED API Key**，儀表板與 AI 按鈕即會自動解鎖展開！")
    
