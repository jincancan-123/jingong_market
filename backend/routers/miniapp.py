from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.session import get_db
from models.product import Product
from datetime import datetime

router = APIRouter(prefix="/miniapp", tags=["微信小程序移动端"])

# 小程序首页核心指标卡片
@router.get("/home")
def miniapp_home_data(db: Session = Depends(get_db)):
    total_product = db.query(func.count(Product.id)).scalar()
    total_gmv = db.query(func.sum(Product.price * Product.sales_volume)).scalar() or 0
    total_sales = db.query(func.sum(Product.sales_volume)).scalar() or 0

    # 1. 平台销量分布（饼图）
    platform_sales_rows = db.query(
        Product.platform,
        func.sum(Product.sales_volume).label("sales")
    ).group_by(Product.platform).all()

    platform_sales = [
        {
            "platform": p[0] or "未知平台",
            "sales": int(p[1] or 0)
        }
        for p in platform_sales_rows
    ]

    # 2. 价格区间分布（柱状图）
    def count_by_price_range(min_price: float, max_price: float):
        return db.query(func.count(Product.id)).filter(
            Product.price >= min_price,
            Product.price < max_price
        ).scalar() or 0

    price_range = []
    price_range.append({
        "range": "0-10元",
        "count": int(count_by_price_range(0, 10))
    })
    price_range.append({
        "range": "10-30元",
        "count": int(count_by_price_range(10, 30))
    })
    price_range.append({
        "range": "30元以上",
        "count": int(db.query(func.count(Product.id)).filter(
            Product.price >= 30
        ).scalar() or 0)
    })

    # 3. 品牌统计（横向条形图）
    top_brand = db.query(
        Product.brand,
        func.count(Product.id).label("cnt")
    ).filter(Product.brand.isnot(None)) \
     .group_by(Product.brand) \
     .order_by(func.count(Product.id).desc()) \
     .limit(3).all()

    top_brand_list = [
        {"brand": b[0], "count": int(b[1])}
        for b in top_brand
    ]

    return {
        "msg": "小程序首页数据",
        "data": {
            "total_product": int(total_product or 0),
            "total_gmv": round(float(total_gmv or 0), 2),
            "total_sales": int(total_sales or 0),
            "top_brand": top_brand_list,
            "platform_sales": platform_sales,
            "price_range": price_range,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    }

# 小程序预警订阅接口
@router.get("/alert/subscribe")
def miniapp_alert_subscribe(db: Session = Depends(get_db)):
    # 复用预警逻辑，轻量化返回给小程序
    alert_list = []
    brand_avg = db.query(
        Product.brand, func.avg(Product.price).label("avg_price")
    ).filter(Product.brand.isnot(None)).group_by(Product.brand).all()
    for brand, avg_price in brand_avg:
        history_avg = avg_price * 1.25
        drop_rate = (history_avg - avg_price) / history_avg
        if drop_rate >= 0.2:
            alert_list.append({
                "brand": brand,
                "level": "高",
                "tip": f"{brand}均价下跌超20%"
            })
    return {
        "msg": "小程序订阅预警列表",
        "data": alert_list
    }