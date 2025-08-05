#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  5 22:52:55 2025

@author: zhz
"""

import streamlit as st

# --- 页面配置 ---
# st.set_page_config是第一个需要执行的Streamlit命令（除了注释）
st.set_page_config(
    page_title="国资监管企业数据分析平台",
    page_icon="📊", # 设置一个图标
    layout="wide", # "wide"布局能更好地利用屏幕空间
    initial_sidebar_state="expanded" # 默认展开侧边栏
)

# --- 主页面内容 ---

# 应用主标题
st.title("📊 国资监管企业数据分析平台（仅供内部使用）")

# 欢迎与介绍
st.markdown("---")
st.markdown(
    """
    欢迎使用本数据分析平台。在这里，我们整合了对**中央企业**和**地方国资监管企业**的关键指标数据，
    旨在提供一个直观、可交互的分析工具。
    """
)

# 引导用户使用侧边栏导航
st.info("👈 **请通过左侧的导航栏选择您要分析的板块。**", icon="ℹ️")
st.markdown("---")

# 使用分栏来创建两个导航卡片，让页面更丰富
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.subheader("🏢 中央企业分析面板")
        st.write(
            "深入分析关键指标的时间序列数据，支持多指标在同一图表上进行对比，"
            "并提供丰富的自定义选项。"
        )
        # 使用st.page_link提供一个清晰的跳转按钮
        st.page_link("pages/1_central.py", label="进入分析", icon="➡️")

with col2:
    with st.container(border=True):
        st.subheader("🏙️ 地方企业分析面板")
        st.write(
            "通过交互式地理热力图，直观展示各地区关键指标的分布情况，"
            "并提供多地区、跨年份的趋势对比功能。"
        )
        st.page_link("pages/2_province.py", label="进入分析", icon="➡️")

# 页脚
st.markdown("---")
st.write("技术支持：清华大学现代国企研究院")