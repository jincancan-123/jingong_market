from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
from models.product import Product
from models.crawl_log import CrawlLog

# -------------------------- 1. 数据清洗看板：统计数据质量 --------------------------
def get_data_clean_board(db: Session):
    # 读取全部商品数据转为DataFrame
    prod_list = db.query(Product).all()
    df = pd.DataFrame([
        {"id": p.id, "title": p.title, "price": p.price, "platform": p.platform, "stock": p.stock, "link": p.link}
        for p in prod_list
    ])
    total_cnt = len(df)
    if total_cnt == 0:
        return {"msg": "暂无商品数据", "data": {}}

    # 1. 去重率（标题重复数量）
    dup_title = df["title"].duplicated().sum()
    dup_rate = round(dup_title / total_cnt, 4)

    # 2. 异常值占比（价格<=0 视为异常）
    abnormal_price = len(df[df["price"] <= 0])
    abnormal_rate = round(abnormal_price / total_cnt, 4)

    # 3. 字段填充率（link不为空比例）
    fill_link = len(df[df["link"].notna()])
    fill_rate = round(fill_link / total_cnt, 4)

    return {
        "total_data": total_cnt,
        "dup_title_count": int(dup_title),
        "dup_rate": dup_rate,
        "abnormal_price_count": abnormal_price,
        "abnormal_rate": abnormal_rate,
        "link_fill_rate": fill_rate
    }

# -------------------------- 2. 智能标签体系：自动给商品打标签 --------------------------
def add_product_label(db: Session, product_id: int):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        return {"msg": "商品不存在"}
    # 情感倾向
    if prod.price < 50:
        sentiment = "正面"
    elif prod.price < 300:
        sentiment = "中性"
    else:
        sentiment = "负面"
    # 内容类型标签
    if "促销" in prod.title or "特惠" in prod.title:
        content_type = "促销"
    elif "测评" in prod.title:
        content_type = "测评"
    else:
        content_type = "recipe"
    label_info = {
        "product_id": prod.id,
        "title": prod.title,
        "sentiment": sentiment,
        "content_type": content_type
    }
    return label_info

# -------------------------- 3. 归因分析模型：各平台销量贡献权重 --------------------------
def platform_contribution_analysis(db: Session):
    prod_list = db.query(Product).all()
    df = pd.DataFrame([
        {"platform": p.platform, "sales": p.stock}
        for p in prod_list
    ])
    platform_group = df.groupby("platform")["sales"].sum()
    total_sales = platform_group.sum()
    result = []
    for plat, sale in platform_group.items():
        weight = round(sale / total_sales, 4)
        result.append({
            "platform": plat,
            "total_sales": int(sale),
            "contribution_weight": weight
        })
    return {
        "total_all_sales": int(total_sales),
        "platform_contribution": result
    }

# -------------------------- 4. 数据血缘追溯：单条商品完整加工链路 --------------------------
def get_data_trace(db: Session, product_id: int):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        return {"msg": "无此商品"}
    # 追溯采集日志
    log = db.query(CrawlLog).filter(CrawlLog.target_platform == prod.platform).order_by(CrawlLog.crawl_time.desc()).first()
    trace_chain = [
        {"step": 1, "source": "爬虫原始采集", "info": f"{prod.platform}批量采集任务"},
        {"step": 2, "source": "数据入库", "info": f"商品{prod.id}存入product表"},
        {"step": 3, "source": "清洗过滤", "info": "过滤价格异常、重复标题"},
        {"step": 4, "source": "标签加工", "info": "自动生成情感、内容分类标签"},
        {"step": 5, "source": "指标计算", "info": "计入平台销量归因权重"}
    ]
    return {
        "product_id": prod.id,
        "platform": prod.platform,
        "origin_crawl_log_id": log.id if log else None,
        "data_trace_chain": trace_chain
    }