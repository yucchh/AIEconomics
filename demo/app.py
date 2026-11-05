import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from fredapi import Fred

# 頁面基本配置
st.set_page_config(page_title="總體經濟與金融即時儀表板", layout="wide")
st.title("🌐 全球總體經濟與金融指標即時儀表板")

# 側邊欄：輸入 API Key 與刷新控制
st.sidebar.header("⚙️ 設定與金鑰")

# 優先使用 Streamlit Secrets，若無則讓學生在側邊欄輸入
if "FRED_API_KEY" in st.secrets:
    fred_key = st.secrets["FRED_API_KEY"]
    st.sidebar.success("已自動讀取 Secrets 中的 API Key！")
else:
    fred_key = st.sidebar.text_input("請輸入你的 FRED API Key:", type="password")

if st.sidebar.button("手動刷新數據"):
    st.cache_data.clear()

# 1. 抓取 FRED 數據並計算利差 (設快取 1 小時)
@st.cache_data(ttl=3600)
def get_fred_data(api_key):
    fred = Fred(api_key=api_key)
    data = {
        "CPI 物價指數": fred.get_series("CPIAUCSL"),
        "10年期美債殖利率": fred.get_series("DGS10"),
        "2年期美債殖利率": fred.get_series("DGS2"),  # 新增：2年期美債
        "美國失業率": fred.get_series("UNRATE"),
        "聯邦基金利率": fred.get_series("FEDFUNDS"),
        "日本10年期公債殖利率": fred.get_series("IRLTLT01JPM156N")
    }
    df = pd.DataFrame(data).ffill().tail(365)
    
    # 計算 10 年期美債減去 2 年期美債利差
    df["10-2年美債利差"] = df["10年期美債殖利率"] - df["2年期美債殖利率"]
    return df

# 2. 抓取 Market 數據 (設快取 10 分鐘)
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

# 頁面渲染邏輯
if fred_key:
    try:
        macro_df = get_fred_data(fred_key)
        market_df = get_market_data()

        # 檢查最新利差並顯示警示燈號
        latest_spread = macro_df["10-2年美債利差"].dropna().iloc[-1]
        if latest_spread < 0:
            st.warning(f"🚨 **【經濟衰退警示】美國公債殖利率曲線發生倒掛！** 當前 10 年期與 2 年期美債利差為 **{latest_spread:.2f}%**（小於 0）。歷史經驗顯示，這通常是經濟衰退的前兆訊號。")
        else:
            st.success(f"✅ 當前 10 年期與 2 年期美債利差為 **{latest_spread:.2f}%**（維持正常正斜率）。")

        # 第一區塊：核心 KPI 卡片 (5 等分欄位)
        st.subheader("📊 關鍵總體經濟指標 (FRED)")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        latest_cpi = macro_df["CPI 物價指數"].dropna().iloc[-1]
        col1.metric("CPI 物價指數", f"{latest_cpi:.1f}")
        
        latest_rate = macro_df["10年期美債殖利率"].dropna().iloc[-1]
        rate_prev = macro_df["10年期美債殖利率"].dropna().iloc[-2]
        col2.metric("10年美債殖利率", f"{latest_rate:.2f}%", f"{latest_rate - rate_prev:+.2f}%")
        
        latest_unemp = macro_df["美國失業率"].dropna().iloc[-1]
        col3.metric("美國失業率", f"{latest_unemp:.1f}%")
        
        latest_fed = macro_df["聯邦基金利率"].dropna().iloc[-1]
        col4.metric("聯邦基金利率", f"{latest_fed:.2f}%")
        
        latest_jp = macro_df["日本10年期公債殖利率"].dropna().iloc[-1]
        jp_prev = macro_df["日本10年期公債殖利率"].dropna().iloc[-2]
        jp_diff = latest_jp - jp_prev
        if abs(jp_diff) < 0.005:
            col5.metric("日本10年期公債殖利率", f"{latest_jp:.2f}%")
        else:
            col5.metric("日本10年期公債殖利率", f"{latest_jp:.2f}%", f"{jp_diff:+.2f}%")

        # 第二區塊：互動式圖表
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

    except Exception as e:
        st.error(f"數據讀取失敗，請確認 FRED API Key 是否正確或網路連線。錯誤訊息: {e}")
else:
    st.info("👈 請在左側輸入您的 FRED API Key 以開啟儀表板。")
