import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import re

def create_sample_data(filename="data.xlsx"):
    """
    当 "data.xlsx" 不存在时，创建一个符合描述的示例Excel文件。
    其中故意包含一个不规范的列名('2021年')和一个非数值的数据('N/A')，用于测试预处理功能。
    """
    #if not os.path.exists(filename):
    print(f"'{filename}' not found. Creating a sample file.")
    data = {
        '表单': ['经济增长', '经济增长', '经济增长', '人口社会', '人口社会', '科技创新'],
        '指标名称': ['GDP增速', '工业增加值增速', 'GDP增速', '全国总人口', '城镇化率', '研发支出占比'],
        '单位': ['%', '%', '%', '万人', '%', '%'],
        '2019': [6.0, 5.7, 6.0, 141008, 60.6, 2.2],
        '2020': [2.4, 2.8, 2.3, 141212, 63.9, 2.4],
        '2021年': [8.1, 9.6, 8.1, 141260, 64.7, 'N/A'], # 脏数据：不规范列名和非数值内容
        '2022': [3.0, 3.6, 3.0, 141175, 65.2, 2.55],
        '2023': [5.2, 4.6, 5.2, 140967, 66.2, 2.64]
    }
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print("Sample file created successfully.")


# 新函数 A: 不带缓存，只负责读取文件
def get_raw_df_from_excel(filename):
    """
    专门负责从Excel文件读取原始数据，并进行基础的文件级错误捕获。
    这个函数不被缓存，确保每次应用刷新都会重新读取文件。
    """
    try:
        df_raw = pd.read_excel(filename)
        return df_raw
    except Exception as e:
        st.error(f"❌ 文件读取失败：无法解析 '{filename}'。请确保它是一个有效的Excel文件。")
        st.error(f"技术细节: {e}")
        st.stop()

# 新函数 B: 带有缓存，负责所有处理和校验
@st.cache_data
def process_dataframe(df_raw):
    """
    接收一个原始DataFrame，并对其进行完整的预处理、校验和转换。
    增加了对无效数据的精确定位和报告。
    """
    if df_raw.empty:
        st.error("❌ 文件校验失败：Excel文件为空，无法进行分析。")
        st.stop()

    df = df_raw.copy()

    # 1. 校验核心元数据列
    REQUIRED_COLS = ['表单', '指标名称', '单位']
    missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing_cols:
        st.error(f"❌ 文件校验失败：缺少核心数据列: `{', '.join(missing_cols)}`。")
        st.stop()

    # 2. 检查指标名称重复
    duplicates = df['指标名称'][df['指标名称'].duplicated()].unique()
    if len(duplicates) > 0:
        st.warning(f"⚠️ 数据质量警告：发现重复的指标名称: `{', '.join(duplicates)}`")

    # 3. 清洗年份列名
    id_vars = REQUIRED_COLS
    value_vars = [col for col in df.columns if col not in id_vars]
    cleaned_colnames_map = {col: int(re.sub(r'\D', '', str(col))) for col in value_vars if re.sub(r'\D', '', str(col))}
    df.rename(columns=cleaned_colnames_map, inplace=True)

    # 4. 转换为长数据
    value_vars_cleaned = cleaned_colnames_map.values()
    df_long = df.melt(id_vars=id_vars, value_vars=value_vars_cleaned, var_name='年份', value_name='数值')
    
    # -----------------------------------------------------------
    # ▼▼▼ 核心修改部分：精确定位无效数据 ▼▼▼
    # -----------------------------------------------------------
    
    # 5. 最终数值校验与精确定位
    # 在转换前，保留原始的'数值'列，用于对比
    original_values = df_long['数值'].copy()
    
    # 执行强制转换，无法转换的变为NaN (空值)
    df_long['数值'] = pd.to_numeric(df_long['数值'], errors='coerce')

    # 定位转换失败的行：即原始值存在，但转换后变为空值的行
    failed_mask = original_values.notna() & df_long['数值'].isna()
    
    if failed_mask.any():
        failed_rows = df_long[failed_mask].copy()
        # 将原始的、错误的数值放回，用于展示
        failed_rows['原始值'] = original_values[failed_mask]
        
        # 构建详细的警告信息
        warning_messages = []
        # 只显示前5个错误，避免刷屏
        for _, row in failed_rows.head(5).iterrows():
            msg = f"  - **指标**: `{row['指标名称']}`, **年份**: `{row['年份']}`, **发现无效值**: `{row['原始值']}`"
            warning_messages.append(msg)
        
        final_warning = "⚠️ **数据清洗警告**：发现并已忽略以下非数值内容：\n" + "\n".join(warning_messages)
        
        if len(failed_rows) > 5:
            final_warning += f"\n  - ...等另外 {len(failed_rows) - 5} 个问题。"
            
        st.warning(final_warning)

    # 移除包含NaN的行，确保后续绘图不出错
    df_long.dropna(subset=['数值'], inplace=True)
    
    # 6. 收尾处理
    df_long['年份'] = pd.to_numeric(df_long['年份'])
    df_long.loc[:, '标签'] = df_long['数值'].round(2).astype(str) + ' ' + df_long['单位']
    
    return df_long


# --- Streamlit 应用主逻辑 ---

st.set_page_config(page_title="关键指标趋势分析", layout="wide")
#create_sample_data("data.xlsx")

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
    DATA_FILE = "data_central.xlsx"
    # 采用全新的两步调用方式
    df_raw = get_raw_df_from_excel(DATA_FILE)
    df = process_dataframe(df_raw)
    
    # 2. Bug修复：定义回调函数，用于在表单切换时更新默认指标
    def update_default_metric_on_form_change():
        current_form = st.session_state.sb_form
        first_metric_in_form = df[df['表单'] == current_form]['指标名称'].unique()[0]
        st.session_state.selected_metrics = [first_metric_in_form]
    
    if 'selected_metrics' not in st.session_state:
        # 确保初始化的默认指标一定存在于DataFrame中
        if not df.empty:
            first_metric = df['指标名称'].unique()[0]
            st.session_state.selected_metrics = [first_metric]
        else:
            st.session_state.selected_metrics = []
    
    st.title("历年中央企业财务决算数据分析面板")
    st.markdown("请通过以下任一方式选择指标，图表将实时更新：")
    
    tab1, tab2 = st.tabs(["🗂️ 按表单筛选", "🔍 直接搜索指标"])
    with tab1:
        unique_forms = df['表单'].unique()
        selected_form = st.selectbox(
            "1. 请选择表单",
            unique_forms,
            key="sb_form",
            on_change=update_default_metric_on_form_change # 2. 绑定回调函数
        )
    
        # 3. 跨表单选择优化
        metrics_in_current_form = df[df['表单'] == selected_form]['指标名称'].unique()
        already_selected_metrics = st.session_state.selected_metrics
        # 将当前表单的指标与已选指标合并，作为总选项
        combined_options = list(metrics_in_current_form)
        for metric in already_selected_metrics:
            if metric not in combined_options:
                combined_options.append(metric)
    
        st.session_state.selected_metrics = st.multiselect(
            "2. 请选择一个或多个指标",
            combined_options, # 使用合并后的选项
            default=st.session_state.selected_metrics,
            key="ms_form_selection"
        )
    
    with tab2:
        all_metrics = df['指标名称'].unique()
        st.session_state.selected_metrics = st.multiselect(
            "直接搜索并选择指标",
            all_metrics,
            default=st.session_state.selected_metrics,
            key="ms_direct_search"
        )
    
    # 4. 用带边框的容器包裹整个绘图区
    with st.container(border=True):
        if not st.session_state.get('selected_metrics', []):
            st.info("👈 请在左上方选择您要分析的指标。")
        else:
            # --- 高级样式自定义 ---
            with st.expander("🎨 高级图表样式自定义"):
                
                # ▼▼▼ 修改点 1：新增年份范围筛选 ▼▼▼
                st.markdown("**筛选设置**")
                all_years = sorted(df['年份'].unique())
                # 确保在数据为空或只有一个年份时不会报错
                if len(all_years) > 1:
                    selected_year_range = st.select_slider(
                        "选择年份范围",
                        options=all_years,
                        value=(all_years[0], all_years[-1]), # 默认选择全部范围
                        key="year_range_slider"
                    )
                else:
                    # 如果只有一个年份或没有年份，则禁用滑块
                    selected_year_range = (all_years[0], all_years[0]) if all_years else (None, None)
                    st.select_slider("选择年份范围", options=all_years, value=selected_year_range, disabled=True)
                
                # ▼▼▼ 修改点 2：将高亮线开关升级为多选框 ▼▼▼
                # ▼▼▼ 修改后的新代码 ▼▼▼
                highlight_years = st.multiselect(
                    "高亮显示年份",
                    options=all_years, # 使用从数据中动态获取的全部年份列表
                    #default=[2020], # 如果需要，可以设置默认高亮的年份，例如 default=[2020]
                    key="highlight_years_multiselect"
                )
                # ▲▲▲ 修改结束 ▲▲▲
    
                st.markdown("**样式设置**")
                cols_expander = st.columns(2)
                with cols_expander[0]:
                    font_list = ["Arial", "Noto Sans CJK SC", "Times New Roman", "Courier New"]
                    selected_font = st.selectbox("选择图表全局字体", font_list, index=0)
                
                # (后续的单项指标样式设置逻辑无变化)
                selected_metrics_df = df[df['指标名称'].isin(st.session_state.selected_metrics)]
                unique_units = selected_metrics_df['单位'].unique()
                default_axis_assignments = {}
                has_percent_unit = any('%' in str(u) for u in unique_units)
                if len(unique_units) > 1 and has_percent_unit:
                    for _, row in selected_metrics_df.drop_duplicates(subset=['指标名称']).iterrows():
                        metric_name = row['指标名称']
                        unit = row['单位']
                        if '%' in str(unit):
                            default_axis_assignments[metric_name] = 1
                        else:
                            default_axis_assignments[metric_name] = 0
                else:
                    for metric_name in st.session_state.selected_metrics:
                        default_axis_assignments[metric_name] = 0
                default_colors = px.colors.qualitative.Plotly
                default_shapes = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up']
                default_styles = ['solid', 'dash', 'dot', 'dashdot']
                style_settings = {}
                axis_map = {"左轴": "y1", "右轴": "y2"}
                header_cols = st.columns([2, 2, 1, 1, 1])
                with header_cols[0]:
                     st.markdown("**指标名称**")
                with header_cols[1]:
                    st.markdown("**Y轴**")
                with header_cols[2]:
                    st.markdown("**颜色**")
                with header_cols[3]:
                    st.markdown("**形状**")
                with header_cols[4]:
                    st.markdown("**线条**")
                for i, metric in enumerate(st.session_state.selected_metrics):
                    cols = st.columns([2, 2, 1, 1, 1])
                    with cols[0]:
                        st.markdown(f"`{metric}`")
                    with cols[1]:
                        axis_choice = st.radio("Y轴分配", ("左轴", "右轴"), index=default_axis_assignments.get(metric, 0), key=f"axis_{metric}", horizontal=True, label_visibility="collapsed")
                    with cols[2]:
                        color = st.color_picker("线条颜色", value=default_colors[i % len(default_colors)], key=f"color_{metric}", label_visibility="collapsed")
                    with cols[3]:
                        shape = st.selectbox("标记形状", options=default_shapes, index=i % len(default_shapes), key=f"shape_{metric}", label_visibility="collapsed")
                    with cols[4]:
                        style = st.selectbox("线条样式", options=default_styles, index=i % len(default_styles), key=f"style_{metric}", label_visibility="collapsed")
                    style_settings[metric] = {"axis": axis_map[axis_choice], "color": color, "shape": shape, "style": style}
            
            # --- 绘图逻辑 ---
            plot_df = df[df['指标名称'].isin(st.session_state.selected_metrics)].copy()
    
            # ▼▼▼ 修改点 3：应用年份范围筛选 ▼▼▼
            if selected_year_range[0] is not None:
                 plot_df = plot_df[
                      (plot_df['年份'] >= selected_year_range[0]) &
                      (plot_df['年份'] <= selected_year_range[1])
                 ]
            # ▲▲▲ 修改结束 ▲▲▲
    
            left_axis_units, right_axis_units = set(), set()
            metrics_to_units = pd.Series(plot_df.单位.values, index=plot_df.指标名称).to_dict()
            for metric, settings in style_settings.items():
                unit = metrics_to_units.get(metric)
                if unit:
                    if settings.get('axis') == 'y2':
                        right_axis_units.add(unit)
                    else:
                        left_axis_units.add(unit)
            y_axis_titles = {"y1": ", ".join(sorted(list(left_axis_units))), "y2": ", ".join(sorted(list(right_axis_units)))}
            y_axes_needed = bool(right_axis_units)
    
            fig = go.Figure()
            for i, metric in enumerate(st.session_state.selected_metrics):
                metric_data = plot_df[plot_df['指标名称'] == metric]
                metric_style = style_settings.get(metric, {})
                axis_id = metric_style.get('axis', 'y1')
                axis_label = "右轴" if axis_id == 'y2' else "左轴"
                legend_name_with_axis = f"{metric} ({axis_label})"
                fig.add_trace(go.Scatter(
                    x=metric_data['年份'], y=metric_data['数值'], name=legend_name_with_axis, yaxis=axis_id,
                    mode='lines+markers+text',
                    line=dict(color=metric_style.get('color'), dash=metric_style.get('style')),
                    marker=dict(symbol=metric_style.get('shape'), size=8),
                    text=metric_data['标签'], textposition='top center', texttemplate='%{text}'
                ))
    
            # ▼▼▼ 修改点 4：根据多选框循环添加高亮线 ▼▼▼
            if highlight_years:
                for year in highlight_years:
                    fig.add_vline(x=year, line_width=2, line_dash="dash", line_color="grey", annotation_text=f"{year}年", annotation_position="top right")
            # ▲▲▲ 修改结束 ▲▲▲
    
            layout_args = {
                "title_text": f"<b>'{'、'.join(st.session_state.selected_metrics)}' 时间序列趋势</b>",
                "xaxis_title": "年份", "yaxis_title": y_axis_titles["y1"], "legend_title": "指标名称",
                "font": {"family": selected_font}, "height": 600,
                "xaxis": dict(tickmode='linear', dtick=1, tickformat='d'),
                "margin": dict(l=20, r=20, t=50, b=20)
            }
            if y_axes_needed:
                layout_args["yaxis2"] = {"title": y_axis_titles["y2"], "overlaying": 'y', "side": 'right'}
            fig.update_layout(**layout_args)
            st.plotly_chart(fig, use_container_width=True)
    
            st.markdown("---")
            st.markdown("### 筛选后的数据详情")
            st.info("💡 **提示**：将鼠标悬停在下方表格的右上角，即可看到下载按钮，可将筛选结果导出为CSV文件。")
            display_data = plot_df[['年份', '表单', '指标名称', '数值', '单位']].sort_values(by=['指标名称', '年份'])
            st.dataframe(display_data, use_container_width=True, hide_index=True)