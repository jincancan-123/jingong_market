from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.session import get_db
from models.product import Product
from models.crawl_log import CrawlLog

router = APIRouter(prefix="/dashboard", tags=["数据可视化大屏"])

@router.get("/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    # 1. 核心总指标
    total_product = db.query(func.count(Product.id)).scalar()
    total_gmv = db.query(func.sum(Product.price * Product.sales_volume)).scalar() or 0
    total_sales = db.query(func.sum(Product.sales_volume)).scalar() or 0

    # 2. 平台销量分布
    platform_stats = db.query(
        Product.platform,
        func.sum(Product.sales_volume).label("sales"),
        func.count(Product.id).label("count")
    ).group_by(Product.platform).all()
    platform_list = [
        {"platform": p[0] or "未知平台", "sales": p[1] or 0, "count": p[2]}
        for p in platform_stats
    ]

    # 3. 价格带分布（低价/中端/高端）
    price_ranges = [
        ("0-30元", 0, 30),
        ("30-80元", 30, 80),
        ("80-150元", 80, 150),
        ("150元以上", 150, 99999)
    ]
    price_dist = []
    for name, min_p, max_p in price_ranges:
        cnt = db.query(Product).filter(
            Product.price >= min_p,
            Product.price < max_p
        ).count()
        price_dist.append({"range": name, "count": cnt})

    # 4. 竞品品牌分布
    brand_stats = db.query(
        Product.brand,
        func.count(Product.id).label("count")
    ).filter(Product.brand.isnot(None)).group_by(Product.brand).all()
    brand_list = [{"brand": b[0], "count": b[1]} for b in brand_stats]

    # 5. 安全获取最新采集时间，字段名修正为 crawl_time
    latest_log = db.query(CrawlLog).order_by(CrawlLog.crawl_time.desc()).first()
    if latest_log:
        latest_update = latest_log.crawl_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        latest_update = "暂无采集记录"

    return {
        "msg": "大屏数据获取成功",
        "data": {
            "overview": {
                "total_product": total_product,
                "total_gmv": round(total_gmv, 2),
                "total_sales": total_sales,
                "latest_update": latest_update
            },
            "platform_dist": platform_list,
            "price_dist": price_dist,
            "brand_dist": brand_list
        }
    }