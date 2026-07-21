from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from database.session import get_db
from models.product import Product
from datetime import datetime, timedelta
import time
from threading import RLock
from typing import Any, Dict, Optional

from utils.ollama_client import generate_ai_analysis

router = APIRouter(prefix="/report", tags=["智能营销报告"])

# 优化点3：全局内存缓存，缓存有效期5分钟，重复请求直接命中缓存，跳过SQL聚合
_DAILY_REPORT_CACHE: Dict[str, Dict[str, Any]] = {}
_DAILY_REPORT_CACHE_LOCK = RLock()
_CACHE_TTL_SECONDS = 300


def _build_daily_report_payload(db: Session, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now()
    cutoff_time = now - timedelta(days=14)

    # 优化点1：统一增加14天时间窗口过滤，避免对8万条商品数据做全表扫描
    time_filter = Product.create_time >= cutoff_time

    # 优化点2：单次聚合查询，合并总指标、平台分组与价格区间统计，减少数据库往返
    platform_stats = db.query(
        Product.platform.label("platform"),
        func.count(Product.id).label("product_count"),
        func.sum(Product.sales_volume).label("sales"),
        func.sum(Product.price * Product.sales_volume).label("gmv"),
        func.sum(case(((Product.price < 30), 1), else_=0)).label("low_price_cnt"),
        func.sum(case(((Product.price >= 30) & (Product.price < 80), 1), else_=0)).label("mid_price_cnt"),
        func.sum(case(((Product.price >= 80), 1), else_=0)).label("high_price_cnt"),
    ).filter(time_filter).group_by(Product.platform).all()

    total_product = sum(int(row.product_count or 0) for row in platform_stats)
    total_gmv = sum(float(row.gmv or 0) for row in platform_stats)
    total_sales = sum(int(row.sales or 0) for row in platform_stats)
    low_price_cnt = sum(int(row.low_price_cnt or 0) for row in platform_stats)
    mid_price_cnt = sum(int(row.mid_price_cnt or 0) for row in platform_stats)
    high_price_cnt = sum(int(row.high_price_cnt or 0) for row in platform_stats)

    platform_list = [
        {
            "platform": row.platform or "未知平台",
            "sales": int(row.sales or 0),
            "gmv": float(row.gmv or 0),
        }
        for row in platform_stats
    ]

    top_platform = (
        max(platform_list, key=lambda item: item["sales"])
        if platform_list
        else {"platform": "暂无数据", "sales": 0, "gmv": 0}
    )

    # 竞品品牌数据仍然单独查询，但也加上14天过滤；避免全量品牌统计
    brand_stats = db.query(
        Product.brand,
        func.count(Product.id).label("count"),
        func.avg(Product.price).label("avg_price"),
    ).filter(Product.brand.isnot(None), time_filter).group_by(Product.brand).all()
    brand_list = [
        {"brand": brand[0], "count": int(brand[1] or 0), "avg_price": round(float(brand[2] or 0), 2)}
        for brand in brand_stats
    ]

    # 结构化日报内容保持与前端完全兼容，不改返回结构
    market_prompt = (
        f"请基于以下当日全平台市场数据，生成一段简洁的中文大盘数据变化解读："
        f"监控商品总数={total_product}款，估算总GMV={round(total_gmv, 2)}元，累计销量={total_sales}件，"
        f"销量主导平台={top_platform['platform']}，低价区间={low_price_cnt}款，中端区间={mid_price_cnt}款，高端区间={high_price_cnt}款。"
        f"请说明本日市场变化的主因、潜在风险和建议。"
    )
    global_data_analysis = generate_ai_analysis(
        market_prompt,
        fallback="整体市场表现呈现价格带分化与渠道集中度上升特征，建议优先强化高销渠道与中端价格带的活动组合。",
    )

    report_content = f"""# 调味品行业营销日报
生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}

## 一、核心数据概览
- 监控商品总数：{total_product} 款
- 全平台估算总GMV：{round(total_gmv, 2)} 元
- 累计总销量：{total_sales} 件
- 销量主导平台：{top_platform['platform']}

## 二、平台渠道分析
"""
    for platform in platform_list:
        report_content += f"- {platform['platform']}：销量{platform['sales']}件，贡献GMV {round(platform['gmv'], 2)} 元\n"

    report_content += f"""
## 三、竞品品牌动态
当前监控 {len(brand_list)} 个核心竞品品牌：
"""
    for brand in brand_list:
        report_content += f"- {brand['brand']}：在售{brand['count']}款，均价 {brand['avg_price']} 元\n"

    report_content += f"""
## 四、价格带分布
- 低价区间(0-30元)：{low_price_cnt} 款
- 中端区间(30-80元)：{mid_price_cnt} 款
- 高端区间(80元以上)：{high_price_cnt} 款

## 五、营销行动建议
1. 重点倾斜资源至 {top_platform['platform']} 渠道，该平台贡献最高销量；
2. 中端价格带商品数量最多，可作为主力促销档位，搭配满减活动提升转化；
3. 持续监控头部竞品价格变动，及时跟进竞品促销节奏；
4. 高端价位商品数量较少，可作为品牌形象款补充产品矩阵。

---
注：本报告由AI基于规则模板自动生成，生产环境可接入大模型API生成自然语言深度分析。
"""

    return {
        "msg": "日报生成成功",
        "data": {
            "generate_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "report_type": "每日营销日报",
            "content": report_content,
            "summary": {
                "total_product": total_product,
                "total_gmv": round(total_gmv, 2),
                "total_sales": total_sales,
                "top_platform": top_platform["platform"],
            },
            "global_data_analysis": global_data_analysis,
        }
    }


def _get_cached_daily_report_payload() -> Optional[Dict[str, Any]]:
    with _DAILY_REPORT_CACHE_LOCK:
        cache_entry = _DAILY_REPORT_CACHE.get("daily_report")
        if not cache_entry:
            return None
        if cache_entry["expires_at"] > time.time():
            return cache_entry["payload"]
        _DAILY_REPORT_CACHE.pop("daily_report", None)
        return None


def _set_daily_report_cache(payload: Dict[str, Any]) -> None:
    with _DAILY_REPORT_CACHE_LOCK:
        _DAILY_REPORT_CACHE["daily_report"] = {
            "payload": payload,
            "expires_at": time.time() + _CACHE_TTL_SECONDS,
        }


def warm_daily_report_cache() -> Dict[str, Any]:
    db = next(get_db())
    try:
        payload = _build_daily_report_payload(db)
        _set_daily_report_cache(payload)
        return payload
    finally:
        db.close()


@router.get("/daily")
def generate_daily_report(db: Session = Depends(get_db)):
    cached_payload = _get_cached_daily_report_payload()
    if cached_payload is not None:
        return cached_payload

    payload = _build_daily_report_payload(db)
    _set_daily_report_cache(payload)
    return payload