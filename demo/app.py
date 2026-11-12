import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from google import genai

# 設定網頁版面與標題 (必須是第一個執行的 streamlit 指令)
st.set_page_config(
    page_title="智能金融與總經 AI 分析平台",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 智能金融、總經數據與 Gemini AI 鷹鴿分析平台")
st.markdown("本系統整合了 **yfinance 即時走勢**、**FRED 總經指標**、**動態關鍵字標的搜尋** 以及 **Gemini AI 貨幣政策情緒分析**。")

# 側邊欄設定
st.sidebar.header("⚙️ 參數與 API 設定")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="請輸入你的 Google Gemini API Key 以啟用 AI 鷹鴿分析")

st.sidebar.divider()
st.sidebar.header("🔍 動態標的搜尋")
search_query = st.sidebar.text_input("輸入股票/期貨代號 (例如: 2330.TW, AAPL, ^TWII)", value="2330.TW")

st.sidebar.divider()
st.sidebar.header("🌐 總經數據來源 (FRED)")
fred_series = st.sidebar.selectbox(
    "選擇總經指標",
    [
        "DFEDTARU (聯準會聯邦基金利率目標)",
        "CPIAUCSL (美國消費者物價指數 CPI)",
        "UNRATE (美國失業率)",
        "T10Y2Y (10年期減2年期公債利差 - 經濟衰退指標)"
    ]
)

# 初始化 Gemini Client
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"Gemini 初始化失敗: {e}")

# 主頁籤介面
tab1, tab2, tab3 = st.tabs(["📊 金融市場走勢", "🌐 FRED 總經數據庫", "🤖 Gemini AI 鷹鴿情緒分析"])

# Tab 1: yfinance 金融走勢
with tab1:
    st.subheader(f"標的即時與歷史走勢：{search_query.upper()}")
    
    if search_query:
        try:
            with st.spinner(f"正在從 Yahoo Finance 抓取 {search_query} 數據..."):
                ticker_obj = yf.Ticker(search_query)
                df_hist = ticker_obj.history(period="1y")
                
                if not df_hist.empty:
                    col1, col2, col3 = st.columns(3)
                    latest_price = df_hist['Close'].iloc[-1]
                    prev_price = df_hist['Close'].iloc[-2]
                    price_change = latest_price - prev_price
                    pct_change = (price_change / prev_price) * 100
                    
                    col1.metric("最新收盤價", f"{latest_price:.2f}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
                    col2.metric("全年最高價", f"{df_hist['High'].max():.2f}")
                    col3.metric("全年最低價", f"{df_hist['Low'].min():.2f}")
                    
                    st.line_chart(df_hist['Close'])
                    
                    with st.expander("查看詳細歷史數據表"):
                        st.dataframe(df_hist.tail(10))
                else:
                    st.warning("查無此標的數據，請確認代號是否正確（例如台股請加 .TW，如 2330.TW；美股直接輸入代號如 AAPL）。")
        except Exception as e:
            st.error(f"載入 yfinance 資料發生錯誤: {e}")

# Tab 2: FRED 總經數據
with tab2:
    series_id = fred_series.split()[0]
    st.subheader(f"美國聯準會經濟數據 (FRED): {fred_series}")
    
    try:
        with st.spinner(f"正在載入 FRED 指標 {series_id}..."):
            fred_csv_url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
            df_fred = pd.read_csv(fred_csv_url, index_col=0, parse_dates=True)
            df_fred = df_fred.dropna()
            
            st.line_chart(df_fred)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("最新數據紀錄：")
                st.dataframe(df_fred.tail(5), use_container_width=True)
            with col_b:
                st.info("💡 **小知識**：FRED（Federal Reserve Economic Data）是由聖路易斯聯邦儲備銀行維護的權威總經數據庫。")
    except Exception as e:
        st.error(f"無法載入 FRED 數據，可能是網路連線或代號有誤: {e}")

# Tab 3: Gemini AI 鷹鴿情緒分析
with tab3:
    st.subheader("🤖 聯準會 / 財經談話鷹鴿傾向 AI 分析")
    st.markdown("貼上最新的聯準會主席演講、FOMC 會議聲明或財經新聞，讓 Gemini AI 進行專業的鷹派與鴿派情緒評估。")
    
    default_text = (
        "Federal Reserve Chair Jerome Powell stated during the press conference that inflation has eased "
        "significantly over the past year, but remains somewhat elevated. We do not expect it will be "
        "appropriate to reduce the target range until we have gained greater confidence that inflation "
        "is moving sustainably down toward 2 percent."
    )
    
    news_input = st.text_area("輸入分析文本（英文或中文皆可）：", value=default_text, height=150)
    
    if st.button("🚀 開始 Gemini AI 深度分析", type="primary"):
        if not client:
            st.warning("⚠️ 請先在左側欄位輸入您的 **Gemini API Key**！")
        else:
            with st.spinner("Gemini AI 正在解讀政策立場與情緒..."):
                try:
                    prompt = f"""
                    你是一位頂尖的華爾街總經分析師。請針對以下財經文字進行分析：
                    1. **政策立場判定**：嚴格判斷其傾向「鷹派 (Hawkish)」、「鴿派 (Dovish)」還是「中性 (Neutral)」。
                    2. **信心指數**：給出 0 到 100 的信心分數。
                    3. **核心理由**：條列式說明文字中支持該判斷的關鍵字句與經濟邏輯。
                    
                    分析文字：
                    {news_input}
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    
                    st.success("分析完成！")
                    st.markdown("### 📊 AI 分析報告")
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"呼叫 Gemini API 時發生錯誤: {e}")
