import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
# 构建地方企业数据文件的绝对路径
PROVINCE_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'data_province.xlsx')

# --- 核心函数 (无变化) ---
@st.cache_data
def load_data(filename=PROVINCE_DATA_PATH):
    if not os.path.exists(filename):
        st.error(f"❌ 数据文件 '{filename}' 未找到。")
        st.stop()
    excel_sheets = pd.read_excel(filename, sheet_name=None)
    all_data = []
    for sheet_name, df_sheet in excel_sheets.items():
        df_sheet['数据来源'] = sheet_name
        all_data.append(df_sheet)
    df_combined = pd.concat(all_data, ignore_index=True)
    return df_combined

@st.cache_data
def get_china_geojson():
    url = "https://raw.githubusercontent.com/longwosion/geojson-map-china/master/china.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        geojson_data = response.json()
        suffixes_to_remove = ['省', '市', '自治区', '回族', '壮族', '维吾尔']
        for feature in geojson_data['features']:
            prov_name = feature['properties']['name']
            for suffix in suffixes_to_remove:
                prov_name = prov_name.replace(suffix, '')
            feature['properties']['name'] = prov_name
        return geojson_data
    except requests.exceptions.RequestException as e:
        st.error(f"无法加载GeoJSON文件: {e}")
        return None

# --- Streamlit 应用主界面 ---
st.set_page_config(page_title="地方国资监管企业关键指标分析", layout="wide")

def check_password():
    """如果用户已登录，返回 True，否则显示密码输入并返回 False"""
    
    # 如果 session state 中 "password_correct" 不存在或为 False，则显示密码输入
    if not st.session_state.get("password_correct", False):
        # 在一个表单中显示密码输入，这样可以防止每次输入字符时页面都刷新
        with st.form("Credentials"):
            st.text_input("请输入密码", type="password", key="password")
            submitted = st.form_submit_button("确认")
            
            # 如果用户点击了确认按钮
            if submitted:
                # 检查密码是否与 st.secrets 中的密码匹配
                if st.session_state["password"] == st.secrets["password"]:
                    # 如果匹配，将 password_correct 设为 True
                    st.session_state["password_correct"] = True
                    # 删除 session state 中的密码，更安全
                    del st.session_state["password"]
                    # 强制重新运行脚本，以显示主应用内容
                    st.rerun()
                else:
                    # 如果不匹配，显示错误信息
                    st.error("😕 密码不正确，请重试")
        # 因为还没登录，所以返回 False
        return False
    else:
        # 如果已经登录，返回 True
        return True


if check_password():
    
    st.title("历年地方国资监管企业数据分析面板")
    
    df = load_data()
    geojson = get_china_geojson()
    
    if '地区' in df.columns:
        df = df[df['地区'] != '台湾'].copy()
    
    # --- 盒子1：全国数据热力图 & 排名 ---
    with st.container(border=True):
        st.markdown("## 全国数据热力图")
        
        st.markdown("#### 数据筛选")
        source_options = df['数据来源'].unique()
        selected_source = st.selectbox("1. 请选择数据来源", options=source_options)
        
        cols_filter = st.columns(2)
        with cols_filter[0]:
            year_options = sorted(df[df['数据来源'] == selected_source]['年份'].unique(), reverse=True)
            selected_year = st.selectbox("2. 请选择年份", options=year_options)
        with cols_filter[1]:
            metric_options = sorted(df['指标名称'].unique())
            selected_metric = st.selectbox("3. 请选择指标", options=metric_options)
    
        df_filtered = df[
            (df['数据来源'] == selected_source) &
            (df['年份'] == selected_year) &
            (df['指标名称'] == selected_metric)
        ]
        
        st.divider()
    
        if df_filtered.empty or not geojson:
            st.warning("当前筛选条件下无数据或地图文件加载失败。")
        else:
            geojson_provinces_set = {feature['properties']['name'] for feature in geojson['features']}
            national_level_regions = {'全国平均', '全国中位数'}
            df_ranked = df_filtered[~df_filtered['地区'].isin(national_level_regions)].sort_values(
                by='数值', ascending=False
            ).reset_index(drop=True)
            df_ranked['排名'] = df_ranked.index + 1
            df_ranked['@'] = df_ranked['地区'].apply(lambda x: '@' if x not in geojson_provinces_set else '')
    
            cols_map_rank = st.columns([3, 2])
            with cols_map_rank[0]:
                unit = df_filtered['单位'].iloc[0] if not df_filtered.empty else ""
                all_geojson_provinces = list(geojson_provinces_set)
                df_map_data = df_ranked[df_ranked['地区'].isin(geojson_provinces_set)]
                fig_map = go.Figure()
                fig_map.add_trace(go.Choroplethmapbox(
                    geojson=geojson, locations=all_geojson_provinces, featureidkey="properties.name",
                    z=[0] * len(all_geojson_provinces), colorscale=[[0, '#cccccc'], [1, '#cccccc']],
                    showscale=False, hoverinfo='none', marker_opacity=0.7, marker_line_width=0.5
                ))
                fig_map.add_trace(go.Choroplethmapbox(
                    geojson=geojson, locations=df_map_data['地区'], featureidkey="properties.name",
                    z=df_map_data['数值'], colorscale="Spectral_r",
                    zmin=df_map_data['数值'].min(), zmax=df_map_data['数值'].max(),
                    showscale=True, hoverinfo='text',
                    hovertemplate='<b>%{location}</b><br>数值: %{z:.2f}<br>排名: %{customdata[0]}<extra></extra>',
                    customdata=df_map_data[['排名']],
                    marker_opacity=0.7, marker_line_width=0.5
                ))
                fig_map.update_layout(
                    mapbox_style="white-bg", mapbox_zoom=3, mapbox_center={"lat": 35.8617, "lon": 104.1954},
                    margin={"r":0,"t":0,"l":0,"b":0}, height=600, showlegend=False
                )
                st.plotly_chart(fig_map, use_container_width=True)
            with cols_map_rank[1]:
                st.subheader("各地区排名")
                st.dataframe(
                    df_ranked[['排名', '地区', '数值', '单位', '@']],
                    use_container_width=True, height=600, hide_index=True
                )
                st.caption(" @ 表示新疆兵团或计划单列市，未在地图中渲染。")
    
    # --- 盒子2：多地区历年趋势对比 ---
    with st.container(border=True):
        st.header("多地区历年趋势对比")
        
        ts_all_years = sorted(df[df['数据来源'] == selected_source]['年份'].unique())
        if len(ts_all_years) > 1:
            ts_selected_year_range = st.select_slider(
                "选择趋势图的年份范围",
                options=ts_all_years,
                value=(ts_all_years[0], ts_all_years[-1])
            )
        else:
            ts_selected_year_range = (ts_all_years[0], ts_all_years[0]) if ts_all_years else (None, None)
        
        ts_cols = st.columns(2)
        with ts_cols[0]:
            ts_metric_options = sorted(df[df['数据来源'] == selected_source]['指标名称'].unique())
            ts_metric = st.selectbox(
                "选择趋势指标", options=ts_metric_options,
                index=ts_metric_options.index(selected_metric) if selected_metric in ts_metric_options else 0,
                key='ts_metric_selector'
            )
        with ts_cols[1]:
            # 从df_ranked获取地区选项，以确保只包含省级地区且已排序
            region_options = df_ranked['地区'].unique().tolist()
            default_regions = df_ranked.head(3)['地区'].tolist()
            ts_regions = st.multiselect(
                "选择对比地区（可多选）",
                options=region_options,
                default=default_regions
            )
        
        if ts_selected_year_range[0] is not None and ts_regions:
            df_ts_filtered = df[
                (df['数据来源'] == selected_source) &
                (df['指标名称'] == ts_metric) &
                (df['年份'] >= ts_selected_year_range[0]) &
                (df['年份'] <= ts_selected_year_range[1])
            ]
            df_ts_regions = df_ts_filtered[df_ts_filtered['地区'].isin(ts_regions)]
            df_ts_national = df_ts_filtered[df_ts_filtered['地区'].isin(['全国平均', '全国中位数'])]
            df_ts_plot = pd.concat([df_ts_regions, df_ts_national])
            
            if df_ts_plot.empty:
                st.info("在当前筛选条件下，趋势图无可用数据。")
            else:
                unit_ts = df_ts_plot['单位'].iloc[0] if not df_ts_plot.empty else ""
                fig_ts = px.line(
                    df_ts_plot, x='年份', y='数值', color='地区', markers=True,
                    title=f"'{ts_metric}' 历年趋势对比",
                    labels={'数值': f'数值 ({unit_ts})', '地区': '地区/类型'}
                )
                fig_ts.update_traces(text=df_ts_plot['数值'].round(2), textposition='top center')
                fig_ts.update_layout(
                    xaxis=dict(tickmode='linear', dtick=1, tickformat='d')
                )
                st.plotly_chart(fig_ts, use_container_width=True)
    
                st.markdown("##### 趋势图数据详情")
                df_display_ts = df_ts_plot.sort_values(by=['地区', '年份'])
                st.dataframe(
                    df_display_ts[['年份', '地区', '数值', '单位']],
                    use_container_width=True, hide_index=True
                )
        else:
            st.info("请至少选择一个地区以绘制趋势图。")