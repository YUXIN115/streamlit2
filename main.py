import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import math
import random

# ... 你的其他代码
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import time
from datetime import datetime
import math
import random

st.set_page_config(page_title="无人机航线规划系统", page_icon="🚁", layout="wide")

# ========== 南京科技职业学院坐标（GCJ-02） ==========
SCHOOL_CENTER = {"lat": 32.1978, "lng": 118.7365}
SCHOOL_BOUNDS = {
    "min_lat": 32.1900, "max_lat": 32.2050,
    "min_lng": 118.7250, "max_lng": 118.7480
}

# ========== 坐标系转换函数 ==========
def gcj02_to_wgs84(lng, lat):
    a = 6378245.0
    ee = 0.00669342162296594323
    
    def transform_lat(x, y):
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
        return ret
    
    def transform_lng(x, y):
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
        return ret
    
    dlat = transform_lat(lng - 105.0, lat - 35.0)
    dlng = transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lng - dlng, lat - dlat

def wgs84_to_gcj02(lng, lat):
    a = 6378245.0
    ee = 0.00669342162296594323
    
    def transform_lat(x, y):
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
        return ret
    
    def transform_lng(x, y):
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
        return ret
    
    dlat = transform_lat(lng - 105.0, lat - 35.0)
    dlng = transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lng + dlng, lat + dlat

def convert_coordinate(lng, lat, from_sys, to_sys):
    if from_sys == to_sys:
        return lng, lat
    if from_sys == "GCJ-02" and to_sys == "WGS-84":
        return gcj02_to_wgs84(lng, lat)
    if from_sys == "WGS-84" and to_sys == "GCJ-02":
        return wgs84_to_gcj02(lng, lat)
    return lng, lat

def check_in_school(lat, lng):
    return (SCHOOL_BOUNDS["min_lat"] <= lat <= SCHOOL_BOUNDS["max_lat"] and
            SCHOOL_BOUNDS["min_lng"] <= lng <= SCHOOL_BOUNDS["max_lng"])

# ========== 障碍物生成 ==========
def generate_obstacles():
    return [
        {"name": "教学楼", "bounds": [[32.1945, 118.7330], [32.1965, 118.7355]], "type": "建筑"},
        {"name": "图书馆", "bounds": [[32.1980, 118.7340], [32.1995, 118.7358]], "type": "建筑"},
        {"name": "实验楼", "bounds": [[32.2005, 118.7365], [32.2020, 118.7385]], "type": "建筑"},
        {"name": "体育馆", "bounds": [[32.1968, 118.7380], [32.1982, 118.7395]], "type": "运动场"},
        {"name": "学生宿舍", "bounds": [[32.2010, 118.7310], [32.2030, 118.7335]], "type": "宿舍"},
        {"name": "食堂", "bounds": [[32.1985, 118.7315], [32.1998, 118.7328]], "type": "餐饮"},
    ]

# ========== 初始化 ==========
if 'a_point' not in st.session_state:
    st.session_state.a_point = {"lat": 32.1970, "lng": 118.7320, "set": False}
if 'b_point' not in st.session_state:
    st.session_state.b_point = {"lat": 32.2015, "lng": 118.7375, "set": False}
if 'height' not in st.session_state:
    st.session_state.height = 50
if 'coord_system' not in st.session_state:
    st.session_state.coord_system = "GCJ-02"
if 'heartbeat_data' not in st.session_state:
    st.session_state.heartbeat_data = []

# ========== 创建地图 ==========
def create_map():
    m = folium.Map(
        location=[SCHOOL_CENTER["lat"], SCHOOL_CENTER["lng"]],
        zoom_start=17,
        control_scale=True
    )
    
    # 高德地图瓦片
    folium.TileLayer(
        tiles='https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
        attr='高德地图',
        name='高德地图'
    ).add_to(m)
    
    # 学校边界
    folium.Rectangle(
        bounds=[[SCHOOL_BOUNDS["min_lat"], SCHOOL_BOUNDS["min_lng"]],
                [SCHOOL_BOUNDS["max_lat"], SCHOOL_BOUNDS["max_lng"]]],
        color='green', weight=2, fill=True, fill_color='green', fill_opacity=0.1,
        popup="南京科技职业学院", tooltip="学校范围"
    ).add_to(m)
    
    # 障碍物
    for obs in generate_obstacles():
        color = 'red' if obs["type"] == "建筑" else 'orange'
        folium.Rectangle(
            bounds=obs["bounds"],
            color=color, weight=2, fill=True, fill_color=color, fill_opacity=0.4,
            popup=f"{obs['name']}", tooltip=obs["name"]
        ).add_to(m)
    
    # A点
    if st.session_state.a_point["set"]:
        folium.Marker(
            [st.session_state.a_point["lat"], st.session_state.a_point["lng"]],
            popup=f"起点 A", icon=folium.Icon(color="green", icon="play", prefix='fa')
        ).add_to(m)
    
    # B点
    if st.session_state.b_point["set"]:
        folium.Marker(
            [st.session_state.b_point["lat"], st.session_state.b_point["lng"]],
            popup=f"终点 B", icon=folium.Icon(color="red", icon="flag-checkered", prefix='fa')
        ).add_to(m)
    
    # 航线
    if st.session_state.a_point["set"] and st.session_state.b_point["set"]:
        folium.PolyLine(
            [[st.session_state.a_point["lat"], st.session_state.a_point["lng"]],
             [st.session_state.b_point["lat"], st.session_state.b_point["lng"]]],
            color="blue", weight=3, opacity=0.8, popup="规划航线"
        ).add_to(m)
    
    folium.LayerControl().add_to(m)
    return m

def simulate_heartbeat():
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "battery": random.randint(70, 100),
        "signal": random.randint(60, 100),
        "gps": f"{32.1978 + random.random()*0.008:.6f}, {118.7365 + random.random()*0.008:.6f}",
        "altitude": random.randint(40, 60),
        "speed": random.randint(0, 15)
    }

# ========== 页面标题 ==========
st.title("🚁 无人机航线规划系统")

# ========== 侧边栏 ==========
with st.sidebar:
    st.header("🎮 控制面板")
    
    # 坐标系设置
    st.subheader("📐 坐标系统设置")
    input_coord = st.radio("输入坐标系", ["WGS-84", "GCJ-02 (高德/百度)"], index=1)
    st.session_state.coord_system = "GCJ-02" if "GCJ" in input_coord else "WGS-84"
    st.divider()
    
    # 起点 A
    st.subheader("📍 起点 A")
    col1, col2 = st.columns(2)
    with col1:
        a_lat = st.number_input("纬度", value=32.1970, format="%.6f")
    with col2:
        a_lng = st.number_input("经度", value=118.7320, format="%.6f")
    
    if st.button("✅ 设置A点", key="set_a"):
        if check_in_school(a_lat, a_lng):
            st.session_state.a_point = {"lat": a_lat, "lng": a_lng, "set": True}
            st.success(f"A点已设置: ({a_lat}, {a_lng})")
        else:
            st.error("❌ 坐标不在学校范围内！请重新输入")
    
    st.divider()
    
    # 终点 B
    st.subheader("🏁 终点 B")
    col1, col2 = st.columns(2)
    with col1:
        b_lat = st.number_input("纬度", value=32.2015, format="%.6f", key="b_lat")
    with col2:
        b_lng = st.number_input("经度", value=118.7375, format="%.6f", key="b_lng")
    
    if st.button("✅ 设置B点", key="set_b"):
        if check_in_school(b_lat, b_lng):
            st.session_state.b_point = {"lat": b_lat, "lng": b_lng, "set": True}
            st.success(f"B点已设置: ({b_lat}, {b_lng})")
        else:
            st.error("❌ 坐标不在学校范围内！请重新输入")
    
    st.divider()
    
    # 飞行参数
    st.subheader("✈️ 飞行参数")
    st.session_state.height = st.slider("设定飞行高度 (m)", 10, 200, 50, 5)
    
    st.divider()
    
    # 系统状态
    st.subheader("📊 系统状态")
    if st.session_state.a_point["set"]:
        st.success("✅ A点已设")
    else:
        st.warning("❌ A点未设")
    
    if st.session_state.b_point["set"]:
        st.success("✅ B点已设")
    else:
        st.warning("❌ B点未设")
    
    st.info(f"✈️ 飞行高度: {st.session_state.height} m")

# ========== 主页面标签页 ==========
tab1, tab2 = st.tabs(["🗺️ 航线规划", "📡 飞行监控"])

# Tab 1: 航线规划
with tab1:
    st.header("🗺️ 航线规划地图")
    m = create_map()
    st_folium(m, width=900, height=600, returned_objects=[])
    
    # 坐标转换信息
    if st.session_state.a_point["set"] or st.session_state.b_point["set"]:
        st.subheader("📍 坐标信息")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.a_point["set"]:
                lat, lng = st.session_state.a_point["lat"], st.session_state.a_point["lng"]
                st.write("**起点 A**")
                st.write(f"输入坐标 ({st.session_state.coord_system}): {lat:.6f}, {lng:.6f}")
                if st.session_state.coord_system == "GCJ-02":
                    wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
                    st.write(f"WGS-84: {wgs_lat:.6f}, {wgs_lng:.6f}")
        
        with col2:
            if st.session_state.b_point["set"]:
                lat, lng = st.session_state.b_point["lat"], st.session_state.b_point["lng"]
                st.write("**终点 B**")
                st.write(f"输入坐标 ({st.session_state.coord_system}): {lat:.6f}, {lng:.6f}")
                if st.session_state.coord_system == "GCJ-02":
                    wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
                    st.write(f"WGS-84: {wgs_lat:.6f}, {wgs_lng:.6f}")
    
    # 障碍物说明
    with st.expander("📌 障碍物列表"):
        for obs in generate_obstacles():
            st.write(f"🔴 **{obs['name']}** ({obs['type']})")
            st.write(f"   范围: {obs['bounds'][0]} → {obs['bounds'][1]}")
        st.warning("⚠️ 规划航线时请避开红色/橙色障碍物区域")

# Tab 2: 飞行监控
with tab2:
    st.header("📡 飞行实时监控")
    
    # 心跳包控制
    auto_refresh = st.checkbox("自动刷新 (每2秒)", value=True)
    refresh_btn = st.button("🔄 手动刷新")
    
    # 模拟心跳包
    if auto_refresh or refresh_btn:
        heartbeat = simulate_heartbeat()
        st.session_state.heartbeat_data.insert(0, heartbeat)
        if len(st.session_state.heartbeat_data) > 20:
            st.session_state.heartbeat_data.pop()
    
    # 显示最新心跳包
    st.subheader("💓 当前心跳包")
    if st.session_state.heartbeat_data:
        latest = st.session_state.heartbeat_data[0]
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("⏰ 时间", latest["timestamp"])
        with col2:
            st.metric("🔋 电量", f"{latest['battery']}%")
        with col3:
            st.metric("📶 信号", f"{latest['signal']}%")
        with col4:
            st.metric("🏔️ 高度", f"{latest['altitude']} m")
        with col5:
            st.metric("⚡ 速度", f"{latest['speed']} m/s")
        
        st.info(f"📍 GPS位置 (GCJ-02): {latest['gps']}")
    
    # 历史记录
    st.subheader("📋 心跳包历史记录")
    if st.session_state.heartbeat_data:
        df = pd.DataFrame(st.session_state.heartbeat_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("点击刷新按钮获取心跳包数据")
    
    # 自动刷新
    if auto_refresh:
        time.sleep(2)
        st.rerun()
