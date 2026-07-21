from datetime import datetime, timedelta
import threading
import time
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from database.session import get_db
from models.product import Product
from routers.alert import get_alert_list as get_full_alert_list
from routers.crawl import crawl_competitor_products, crawl_public_opinion, run_crawl_task
from routers.crawl_log import get_all_logs

router = APIRouter(prefix="/miniapp", tags=["微信小程序移动端"])

# 优化点3：增加线程安全的全局内存缓存，5分钟TTL，重复打开首页直接命中缓存，避免重复聚合SQL。
_HOME_CACHE_TTL_SECONDS = 300
_home_cache: Dict[str, Tuple[float, dict]] = {}
_home_cache_lock = threading.Lock()


def _get_home_cache() -> Optional[dict]:
    now = time.time()
    with _home_cache_lock:
        cached = _home_cache.get("miniapp_home")
        if cached and now - cached[0] < _HOME_CACHE_TTL_SECONDS:
            return cached[1]
    return None


def _set_home_cache(payload: dict) -> None:
    with _home_cache_lock:
        _home_cache["miniapp_home"] = (time.time(), payload)


# 小程序首页核心指标卡片
@router.get("/home")
def miniapp_home_data(db: Session = Depends(get_db)):
    cached_payload = _get_home_cache()
    if cached_payload is not None:
        return cached_payload

    # 优化点1：增加14天时间窗口过滤，只统计近期增量商品，显著缩小扫描行数。
    cutoff = datetime.now() - timedelta(days=14)
    recent_filter = Product.create_time >= cutoff

    # 优化点2：单条聚合SQL同时返回总指标、平台分组和价格区间统计，减少重复扫表与多次count。
    platform_rows = (
        db.query(
            Product.platform.label("platform"),
            func.count(Product.id).label("product_count"),
            func.coalesce(func.sum(Product.price * Product.sales_volume), 0).label("gmv"),
            func.coalesce(func.sum(Product.sales_volume), 0).label("sales"),
            func.coalesce(
                func.sum(case((and_(Product.price >= 0, Product.price < 10), 1), else_=0)),
                0,
            ).label("price_0_10_count"),
            func.coalesce(
                func.sum(case((and_(Product.price >= 10, Product.price < 30), 1), else_=0)),
                0,
            ).label("price_10_30_count"),
            func.coalesce(
                func.sum(case((Product.price >= 30, 1), else_=0)),
                0,
            ).label("price_30_up_count"),
        )
        .filter(recent_filter)
        .group_by(Product.platform)
        .all()
    )

    total_product = int(sum(int(row.product_count or 0) for row in platform_rows))
    total_gmv = round(float(sum(float(row.gmv or 0) for row in platform_rows)), 2)
    total_sales = int(sum(int(row.sales or 0) for row in platform_rows))

    platform_sales = [
        {
            "platform": row.platform or "未知平台",
            "sales": int(row.sales or 0),
        }
        for row in sorted(platform_rows, key=lambda item: (item.sales or 0), reverse=True)
    ]

    price_range = [
        {
            "range": "0-10元",
            "count": int(sum(int(row.price_0_10_count or 0) for row in platform_rows)),
        },
        {
            "range": "10-30元",
            "count": int(sum(int(row.price_10_30_count or 0) for row in platform_rows)),
        },
        {
            "range": "30元以上",
            "count": int(sum(int(row.price_30_up_count or 0) for row in platform_rows)),
        },
    ]

    # 优化点1：品牌统计也加入14天过滤，避免对历史数据做无意义聚合。
    top_brand_rows = (
        db.query(
            Product.brand,
            func.count(Product.id).label("cnt"),
        )
        .filter(recent_filter, Product.brand.isnot(None))
        .group_by(Product.brand)
        .order_by(func.count(Product.id).desc())
        .limit(3)
        .all()
    )
    top_brand_list = [
        {"brand": brand, "count": int(count)}
        for brand, count in top_brand_rows
    ]

    payload = {
        "msg": "小程序首页数据",
        "data": {
            "total_product": total_product,
            "total_gmv": total_gmv,
            "total_sales": total_sales,
            "top_brand": top_brand_list,
            "platform_sales": platform_sales,
            "price_range": price_range,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
    }
    _set_home_cache(payload)
    return payload


# 小程序预警列表接口，新增路由，直接复用完整预警逻辑。
@router.get("/alert/list")
def miniapp_alert_list(db: Session = Depends(get_db)):
    # 优化点1：统一使用14天窗口过滤，避免预警查询再次扫全表。
    return get_full_alert_list(db)


# 小程序预警订阅接口，兼容旧代码，但返回与/alert/list一致的分层结构。
@router.get("/alert/subscribe")
@router.post("/alert/subscribe")
def miniapp_alert_subscribe(db: Session = Depends(get_db)):
    # 优化点1：保留兼容路由，但内部复用完整预警逻辑，避免旧简易逻辑造成空白。
    return get_full_alert_list(db)


class MiniappCrawlRunRequest(BaseModel):
    platform: str = "天猫"
    keyword: str = "酱油"


class MiniappCompetitorRequest(BaseModel):
    platform: str = "天猫"
    brand_keywords: list[str] = ["海天", "千禾"]


class MiniappOpinionRequest(BaseModel):
    hot_keywords: list[str] = ["零添加", "有机酱油"]


@router.post("/crawl/run")
def miniapp_run_crawl(payload: MiniappCrawlRunRequest, db: Session = Depends(get_db)):
    # 优化点：小程序直接转发后台通用爬虫任务，保持原始接口返回格式不变。
    result = run_crawl_task(db, payload.platform, payload.keyword)
    return {"msg": "采集任务执行完成", "data": result}


@router.post("/crawl/competitor")
def miniapp_run_competitor_crawl(payload: MiniappCompetitorRequest, db: Session = Depends(get_db)):
    # 优化点：小程序直接转发后台竞品监控任务，确保 JSON body 参数正确进入底层函数并返回结构化结果。
    result = crawl_competitor_products(db, payload.brand_keywords, payload.platform)
    return {"msg": "竞品采集完成", "data": result}


@router.post("/crawl/opinion")
def miniapp_run_opinion_crawl(payload: MiniappOpinionRequest, db: Session = Depends(get_db)):
    # 优化点：小程序直接转发后台舆情采集任务，保持原始接口返回格式不变。
    result = crawl_public_opinion(db, payload.hot_keywords)
    return {"msg": "舆情采集完成", "data": result}


@router.get("/crawl/log")
def miniapp_get_crawl_logs(db: Session = Depends(get_db)):
    # 优化点：复用后台日志查询逻辑，给小程序页面渲染任务记录。
    logs = get_all_logs(db)
    return {"msg": "采集日志查询成功", "data": logs}