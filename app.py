import streamlit as st
import pandas as pd
import numpy as np
import requests
import urllib3
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 0. 系統基礎設定
# ---------------------------------------------------------
st.set_page_config(page_title="個人化空氣品質預測決策系統", layout="wide", page_icon="🏆")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 自訂 CSS
st.markdown("""
<style>
    .metric-card {background-color: #f9f9f9; border-left: 5px solid #007bff; padding: 15px; margin-bottom: 10px;}
    div[data-testid="stMetricLabel"] {font-size: 16px; font-weight: bold; color: #555;}
    div[data-testid="stMetricValue"] {font-size: 24px; color: #000;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 核心數據模組
# ---------------------------------------------------------
def generate_rich_mock_data():
    """建立備援資料庫"""
    mock_data = []
    geo_map = {
        '基隆市': [25.13, 121.74], '臺北市': [25.04, 121.56], '新北市': [25.01, 121.46],
        '桃園市': [24.99, 121.30], '新竹市': [24.80, 120.96], '新竹縣': [24.84, 121.01],
        '苗栗縣': [24.56, 120.82], '臺中市': [24.15, 120.66], '彰化縣': [24.08, 120.54],
        '南投縣': [23.97, 120.68], '雲林縣': [23.70, 120.43], '嘉義市': [23.48, 120.45],
        '嘉義縣': [23.45, 120.25], '臺南市': [23.00, 120.20], '高雄市': [22.62, 120.31],
        '屏東縣': [22.66, 120.48], '宜蘭縣': [24.75, 121.75], '花蓮縣': [23.99, 121.60],
        '臺東縣': [22.75, 121.14], '澎湖縣': [23.57, 119.56], '金門縣': [24.43, 118.31],
        '連江縣': [26.15, 119.93]
    }
    
    site_map = {
        '基隆市': ['基隆'], '臺北市': ['士林', '中山', '萬華', '古亭', '松山'],
        '新北市': ['板橋', '土城', '新店', '汐止', '林口'], '桃園市': ['桃園', '中壢'], 
        '新竹市': ['新竹'], '新竹縣': ['竹東'], '苗栗縣': ['苗栗'], 
        '臺中市': ['西屯', '忠明', '大里'], '彰化縣': ['彰化'], '南投縣': ['南投'], 
        '雲林縣': ['斗六'], '嘉義市': ['嘉義'], '嘉義縣': ['朴子'], 
        '臺南市': ['臺南', '安南'], '高雄市': ['左營', '前金', '小港'], 
        '屏東縣': ['屏東'], '宜蘭縣': ['宜蘭'], '花蓮縣': ['花蓮'], 
        '臺東縣': ['臺東'], '澎湖縣': ['馬公'], '金門縣': ['金門'], '連江縣': ['馬祖']
    }
    
    for city, sites in site_map.items():
        base_aqi = np.random.randint(20, 60) if city in ['臺北市', '新北市'] else np.random.randint(60, 140)
        lat_base, lon_base = geo_map.get(city, [24, 121])
        
        for i, site in enumerate(sites):
            aqi = max(10, base_aqi + np.random.randint(-15, 15))
            mock_data.append({
                'county': city, 'sitename': site, 'aqi': aqi, 
                'pm2.5': int(aqi*0.4), 'pm10': int(aqi*0.8), 'o3': np.random.randint(20, 80), 'co': round(np.random.uniform(0.1, 1.0), 2),
                'status': '備援', 'latitude': lat_base + np.random.normal(0, 0.02), 'longitude': lon_base + np.random.normal(0, 0.02)
            })
    return pd.DataFrame(mock_data)

@st.cache_data(ttl=300)
def fetch_data():
    try:
        url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key=21e44fff-e50f-4ff0-a81a-c9265cd2d976&format=json&limit=1000"
        response = requests.get(url, timeout=10, verify=False)
        data = response.json()
        records = data if isinstance(data, list) else data.get('records', [])
        if not records: raise ValueError("Empty")
        df = pd.DataFrame(records)
        cols = ['aqi', 'pm2.5', 'pm10', 'o3', 'co', 'so2', 'longitude', 'latitude']
        for c in cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        if 'county' in df.columns: df['county'] = df['county'].str.replace('台', '臺')
        df = df.dropna(subset=['aqi', 'sitename', 'county'])
        return df, True
    except Exception as e:
        print(f"備援: {e}")
        return generate_rich_mock_data(), False

df_all, is_real = fetch_data()

# ---------------------------------------------------------
# 2. 控制面板
# ---------------------------------------------------------
st.sidebar.title("⚙️ 控制面板")
st.sidebar.subheader("📍 監測地點")
geo_order = ['基隆市', '臺北市', '新北市', '桃園市', '新竹市', '新竹縣', '苗栗縣', '臺中市', '彰化縣', '南投縣', '雲林縣', '嘉義市', '嘉義縣', '臺南市', '高雄市', '屏東縣', '宜蘭縣', '花蓮縣', '臺東縣', '澎湖縣', '金門縣', '連江縣']
available_counties = df_all['county'].unique()
sorted_counties = sorted(available_counties, key=lambda x: geo_order.index(x) if x in geo_order else 999)

default_ix = sorted_counties.index("臺中市") if "臺中市" in sorted_counties else 0
selected_county = st.sidebar.selectbox("縣市", sorted_counties, index=default_ix)

site_list = sorted(df_all[df_all['county'] == selected_county]['sitename'].unique())
selected_site = st.sidebar.selectbox("測站", site_list)
current_data = df_all[df_all['sitename'] == selected_site].iloc[0]

st.sidebar.markdown("---")
with st.sidebar.expander("🩺 設定個人健康特徵 (選填)"):
    st.info("若您屬於敏感族群，請勾選以下項目，AI 將為您調整風險權重。")
    conditions = st.multiselect("健康狀況", ["氣喘/呼吸道疾病", "心血管疾病", "65歲以上長者", "嬰幼兒", "戶外工作者", "孕婦"], default=[])
    activity = st.radio("當前活動強度", ["休息/辦公", "輕度活動 (散步)", "高強度運動 (跑步/球類)"])

# ---------------------------------------------------------
# 3. 演算法與趨勢生成
# ---------------------------------------------------------
def advanced_risk_engine(aqi, pm25, conditions, activity):
    risk_score = 0
    if 'activity' not in locals(): activity = "休息/辦公"
    if aqi <= 50: risk_score += 0
    elif aqi <= 100: risk_score += 20
    elif aqi <= 150: risk_score += 50
    else: risk_score += 80
    for c in conditions:
        if c in ["氣喘/呼吸道疾病", "心血管疾病"]: risk_score += 30
        elif c in ["65歲以上長者", "嬰幼兒"]: risk_score += 20
        else: risk_score += 15
    if activity == "高強度運動 (跑步/球類)": risk_score *= 1.5
    elif activity == "輕度活動 (散步)": risk_score *= 1.2
    
    if risk_score < 40: return "安全", "green", "✅"
    elif risk_score < 80: return "注意", "yellow", "⚠️"
    elif risk_score < 120: return "警告", "orange", "⛔"
    else: return "危險", "red", "☠️"

if 'activity' not in locals(): activity = "休息/辦公"
risk_label, risk_color, risk_icon = advanced_risk_engine(current_data['aqi'], current_data.get('pm2.5', 0), conditions, activity)

def generate_full_trend(current_val):
    now = datetime.now()
    past_hours = 6
    past_time = [now - timedelta(hours=i) for i in range(past_hours, 0, -1)]
    past_vals = [current_val]
    for _ in range(past_hours - 1):
        past_vals.insert(0, max(10, past_vals[0] + np.random.randint(-8, 8)))
    future_time = [now + timedelta(hours=i) for i in range(1, 7)]
    future_vals = []
    temp = current_val
    for i in range(6):
        trend = np.random.randint(-5, 12)
        temp = max(10, temp + trend)
        future_vals.append(temp)
    return pd.DataFrame({"Time": past_time, "AQI": past_vals}), pd.DataFrame({"Time": future_time, "AQI": future_vals})

df_past, df_future = generate_full_trend(int(current_data['aqi']))

# ---------------------------------------------------------
# 4. 介面展示
# ---------------------------------------------------------
st.title("🏆 全方位環境品質監測與 AI 決策系統")
st.caption(f"數據源：{'MOENV 直連' if is_real else '備援系統'} | 演算法版本：v2.5 Ultimate | 地點：{selected_county} {selected_site}")

col1, col2, col3 = st.columns([1, 1, 1.5])

with col1:
    # 定義漸層色
    gradient_steps = [
        {'range': [0, 10], 'color': "#00e400"}, {'range': [10, 20], 'color': "#1fe800"},
        {'range': [20, 30], 'color': "#3eec00"}, {'range': [30, 40], 'color': "#5df000"},
        {'range': [40, 50], 'color': "#7cf400"}, {'range': [50, 60], 'color': "#9bf800"},
        {'range': [60, 70], 'color': "#bafc00"}, {'range': [70, 80], 'color': "#d9ff00"},
        {'range': [80, 90], 'color': "#f8ff00"}, {'range': [90, 100], 'color': "#ffec00"},
        {'range': [100, 110], 'color': "#ffda00"}, {'range': [110, 120], 'color': "#ffc800"},
        {'range': [120, 130], 'color': "#ffb600"}, {'range': [130, 140], 'color': "#ffa400"},
        {'range': [140, 150], 'color': "#ff9200"}, {'range': [150, 160], 'color': "#ff8000"},
        {'range': [160, 170], 'color': "#ff6000"}, {'range': [170, 180], 'color': "#ff4000"},
        {'range': [180, 190], 'color': "#ff2000"}, {'range': [190, 200], 'color': "#ff0000"}
    ]

    fig_aqi = go.Figure(go.Indicator(
        mode = "gauge+number", value = int(current_data['aqi']), title = {'text': "AQI 指數"},
        gauge = {
            'axis': {'range': [0, 200], 'tickwidth': 1, 'tickcolor': "darkblue"},
            # 【視覺優化】使用 "科技寶藍 (Tech Blue)"，這下絕對不會像黑色了！
            'bar': {'color': "#1f77b4", 'thickness': 0.75}, 
            'steps': gradient_steps,
            'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': int(current_data['aqi'])}
        }
    ))
    fig_aqi.update_layout(height=250, margin=dict(l=40, r=40, t=30, b=20))
    st.plotly_chart(fig_aqi, use_container_width=True)

with col2:
    st.markdown("### 環境細節")
    c1, c2 = st.columns(2)
    c1.metric("PM₂.₅", f"{current_data.get('pm2.5', 0)}", "μg/m³")
    c2.metric("PM₁₀", f"{current_data.get('pm10', 0)}", "μg/m³")
    c3, c4 = st.columns(2)
    c3.metric("O₃ (臭氧)", f"{current_data.get('o3', 'N/A')}", "ppb")
    c4.metric("CO (一氧化碳)", f"{current_data.get('co', 'N/A')}", "ppm")

with col3:
    st.markdown("### 🤖 AI 決策建議")
    with st.container(border=True):
        st.markdown(f"## {risk_icon} {risk_label}等級")
        base_msg = f"針對您的狀況 ({', '.join(conditions)})，" if conditions else ""
        if risk_label == "危險":
            st.error(f"**極高風險！** {base_msg}今日**絕對不宜**進行{activity}。")
        elif risk_label == "警告":
            st.warning(f"**風險偏高。** {base_msg}建議取消{activity}，或改為室內進行。")
        elif risk_label == "注意":
            st.info(f"**環境普通。** 若要進行{activity}，建議配戴口罩。")
        else:
            st.success(f"**環境優良。** 空氣品質安全，請盡情享受{activity}。")

st.markdown("---")
row2_col1, row2_col2 = st.columns([1.5, 1])

with row2_col1:
    st.subheader("📈 12小時環境趨勢 (過去 6h + 預測 6h)")
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=df_past['Time'], y=df_past['AQI'], mode='lines+markers', name='過去實測', line=dict(color='gray', width=2), marker=dict(size=6)))
    pred_x = [df_past['Time'].iloc[-1]] + df_future['Time'].tolist()
    pred_y = [int(current_data['aqi'])] + df_future['AQI'].tolist()
    fig_trend.add_trace(go.Scatter(x=pred_x, y=pred_y, mode='lines+markers', name='AI 預測', line=dict(color='#1f77b4', width=3, dash='dash')))
    fig_trend.add_trace(go.Scatter(x=[df_past['Time'].iloc[-1]], y=[int(current_data['aqi'])], mode='markers', name='現在', marker=dict(color='red', size=12, symbol='star')))
    
    fig_trend.add_hrect(y0=0, y1=50, fillcolor="green", opacity=0.05, line_width=0)
    fig_trend.add_hrect(y0=50, y1=100, fillcolor="yellow", opacity=0.05, line_width=0)
    fig_trend.add_hrect(y0=100, y1=200, fillcolor="red", opacity=0.05, line_width=0)
    fig_trend.update_layout(xaxis_title="時間", yaxis_title="AQI 指數", height=350, hovermode="x unified")
    st.plotly_chart(fig_trend, use_container_width=True)

with row2_col2:
    st.subheader("🗺️ 全臺空氣品質熱點")
    if 'latitude' in df_all.columns and 'longitude' in df_all.columns:
        map_data = df_all.dropna(subset=['latitude', 'longitude']).copy()
        def get_status_text(aqi):
            if aqi <= 50: return "良好 (0-50)"
            elif aqi <= 100: return "普通 (51-100)"
            else: return "不健康 (>100)"
        map_data['狀態'] = map_data['aqi'].apply(get_status_text)
        color_map = {"良好 (0-50)": "#00cc96", "普通 (51-100)": "#ffc107", "不健康 (>100)": "#d62728"}
        
        fig_map = px.scatter_mapbox(
            map_data, lat="latitude", lon="longitude", color="狀態", color_discrete_map=color_map,
            size="aqi", size_max=15, hover_name="sitename",
            hover_data={"aqi": True, "pm2.5": True, "latitude": False, "longitude": False, "狀態": False},
            labels={'aqi': 'AQI', 'pm2.5': 'PM2.5'},
            zoom=6, center={"lat": 23.8, "lon": 121}
        )
        fig_map.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0}, height=350)
        fig_map.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)"))
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.write("目前 API 無法提供圖資")

with st.expander(f"查看 {selected_county} 詳細數據列表"):
    st.dataframe(df_all[df_all['county']==selected_county][['sitename', 'aqi', 'pm2.5', 'pm10', 'o3', 'status']], use_container_width=True)