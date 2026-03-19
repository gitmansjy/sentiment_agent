import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import config
from database import DatabaseManager

# 页面配置
st.set_page_config(page_title="舆情分析看板", layout="wide")
st.title("📊 清洁电器舆情监控系统")

# 初始化数据库连接
db = DatabaseManager(config.DB_CONFIG)

# 侧边栏 - 参数选择
st.sidebar.header("⚙️ 筛选条件")

# 获取所有商品列表（用于下拉框）
products_df = pd.read_sql("SELECT DISTINCT product_id FROM raw_reviews", db.engine)
product_list = products_df["product_id"].tolist()
selected_product = st.sidebar.selectbox("选择商品", product_list)

# 日期范围选择
min_date = pd.read_sql("SELECT MIN(created_at) FROM raw_reviews", db.engine).iloc[0, 0]
max_date = pd.read_sql("SELECT MAX(created_at) FROM raw_reviews", db.engine).iloc[0, 0]
date_range = st.sidebar.date_input(
    "日期范围",
    value=[min_date.date(), max_date.date()],
    min_value=min_date.date(),
    max_value=max_date.date(),
)

# 情感过滤
sentiment_filter = st.sidebar.multiselect(
    "情感标签",
    options=["positive", "neutral", "negative"],
    default=["positive", "neutral", "negative"],
)


# 加载数据的缓存函数
@st.cache_data(ttl=600)  # 缓存10分钟
def load_stats(product, start_date, end_date):
    query = f"""
        SELECT stat_date, total_reviews, positive_count, neutral_count, negative_count
        FROM sentiment_stats
        WHERE product_id = '{product}'
          AND stat_date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY stat_date
    """
    df = pd.read_sql(query, db.engine)
    if not df.empty:
        df["negative_rate"] = df["negative_count"] / df["total_reviews"]
    return df


@st.cache_data(ttl=600)
def load_reviews(product, start_date, end_date, sentiment_list):
    if not sentiment_list:
        sentiment_list = ["positive", "neutral", "negative"]
    sentiment_str = "','".join(sentiment_list)
    query = f"""
        SELECT r.id, r.content, r.like_count, r.created_at,
               a.overall_sentiment, a.sentiment_score, a.aspects, a.key_phrases
        FROM raw_reviews r
        JOIN analysis_results a ON r.id = a.review_id
        WHERE r.product_id = '{product}'
          AND DATE(r.created_at) BETWEEN '{start_date}' AND '{end_date}'
          AND a.overall_sentiment IN ('{sentiment_str}')
        ORDER BY r.created_at DESC
    """
    df = pd.read_sql(query, db.engine)
    return df


@st.cache_data(ttl=600)
def load_alerts(product):
    query = f"""
        SELECT * FROM alerts
        WHERE product_id = '{product}'
        ORDER BY triggered_at DESC
        LIMIT 20
    """
    return pd.read_sql(query, db.engine)


# 加载数据
stats_df = load_stats(selected_product, date_range[0], date_range[1])
reviews_df = load_reviews(
    selected_product, date_range[0], date_range[1], sentiment_filter
)
alerts_df = load_alerts(selected_product)

# ========== 第一行：全局指标卡片 ==========
st.subheader("📌 全局概览")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total = len(reviews_df) if not reviews_df.empty else 0
    st.metric("评论总数", total)

with col2:
    pos = (
        len(reviews_df[reviews_df["overall_sentiment"] == "positive"])
        if not reviews_df.empty
        else 0
    )
    st.metric("正面", pos)

with col3:
    neu = (
        len(reviews_df[reviews_df["overall_sentiment"] == "neutral"])
        if not reviews_df.empty
        else 0
    )
    st.metric("中性", neu)

with col4:
    neg = (
        len(reviews_df[reviews_df["overall_sentiment"] == "negative"])
        if not reviews_df.empty
        else 0
    )
    st.metric("负面", neg)

with col5:
    neg_rate = neg / total if total > 0 else 0
    st.metric("负面率", f"{neg_rate:.2%}")

# ========== 第二行：情感趋势图 ==========
st.subheader("📈 情感趋势")

if not stats_df.empty:
    # 使用 Plotly 绘制堆叠面积图
    fig = px.area(
        stats_df,
        x="stat_date",
        y=["positive_count", "neutral_count", "negative_count"],
        title="每日情感数量变化",
        labels={"value": "评论数量", "variable": "情感"},
        color_discrete_map={
            "positive_count": "green",
            "neutral_count": "gray",
            "negative_count": "red",
        },
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("暂无趋势数据")

# ========== 第三行：方面情感雷达图 ==========
st.subheader("🔍 方面级情感评分")

if not reviews_df.empty:
    # 提取所有评论的 aspects JSON 字段，计算每个方面的平均分
    aspect_scores = {}
    aspect_counts = {}
    for _, row in reviews_df.iterrows():
        aspects = row["aspects"]
        if aspects and isinstance(aspects, str):
            aspects = eval(aspects)  # 将字符串转为字典（生产环境可用 json.loads）
        elif isinstance(aspects, dict):
            pass
        else:
            continue
        for k, v in aspects.items():
            score = 1 if v == "positive" else (0.5 if v == "neutral" else 0)
            aspect_scores[k] = aspect_scores.get(k, 0) + score
            aspect_counts[k] = aspect_counts.get(k, 0) + 1

    # 计算平均分
    for k in aspect_scores:
        aspect_scores[k] /= aspect_counts[k]

    if aspect_scores:
        # 转换为 DataFrame 方便绘图
        aspect_df = pd.DataFrame(
            list(aspect_scores.items()), columns=["aspect", "score"]
        )
        fig = px.bar(
            aspect_df,
            x="aspect",
            y="score",
            title="各维度平均分（1=正面,0=负面）",
            range_y=[0, 1],
            color="score",
            color_continuous_scale="RdYlGn",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无方面数据")
else:
    st.info("无评论数据")

# ========== 第四行：高频词云 ==========
st.subheader("☁️ 高频词云")

if not reviews_df.empty:
    # 提取所有关键短语
    all_phrases = []
    for _, row in reviews_df.iterrows():
        phrases = row["key_phrases"]
        if phrases and isinstance(phrases, str):
            phrases = eval(phrases)
        elif isinstance(phrases, list):
            pass
        else:
            continue
        all_phrases.extend(phrases)

    if all_phrases:
        text = " ".join(all_phrases)
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color="white",
            font_path="simhei.ttf",  # 如果有中文字体可指定
            colormap="viridis",
        ).generate(text)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.info("无关键词数据")
else:
    st.info("无评论数据")

# ========== 第五行：预警历史 ==========
st.subheader("⚠️ 预警记录")

if not alerts_df.empty:
    # 显示表格，可展开查看详情
    for _, row in alerts_df.iterrows():
        with st.expander(
            f"{row['triggered_at']} - {row['alert_level']}级预警 (分数: {row['alert_score']:.2f})"
        ):
            st.write(f"**负面率**: {row['negative_ratio']:.2%}")
            if row["sample_reviews"]:
                st.write("**样本评论**:")
                samples = (
                    eval(row["sample_reviews"])
                    if isinstance(row["sample_reviews"], str)
                    else row["sample_reviews"]
                )
                for s in samples:
                    st.write(f"- {s}")
            if row["reply_draft"]:
                st.write("**自动回复草稿**:")
                st.info(row["reply_draft"])
            st.write(f"**解决状态**: {'已解决' if row['resolved'] else '未解决'}")
else:
    st.info("暂无预警记录")

# ========== 第六行：评论明细搜索 ==========
st.subheader("📋 评论明细")

if not reviews_df.empty:
    # 添加搜索框
    search_term = st.text_input("搜索评论内容（支持关键词）")
    filtered_df = reviews_df
    if search_term:
        filtered_df = reviews_df[
            reviews_df["content"].str.contains(search_term, na=False)
        ]

    # 分页显示
    page_size = st.selectbox("每页条数", [10, 20, 50], index=0)
    total_pages = (len(filtered_df) + page_size - 1) // page_size
    page = st.number_input("页码", min_value=1, max_value=total_pages or 1, value=1)
    start = (page - 1) * page_size
    end = start + page_size
    page_df = filtered_df.iloc[start:end]

    # 显示表格
    st.dataframe(
        page_df[
            [
                "created_at",
                "overall_sentiment",
                "sentiment_score",
                "content",
                "like_count",
            ]
        ],
        use_container_width=True,
        column_config={
            "created_at": "发布时间",
            "overall_sentiment": "情感",
            "sentiment_score": "分数",
            "content": "内容",
            "like_count": "点赞",
        },
    )
else:
    st.info("无评论数据")
