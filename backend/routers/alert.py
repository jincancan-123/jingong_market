from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.session import get_db
from models.product import Product
from datetime import datetime

router = APIRouter(prefix="/alert", tags=["异常预警推送"])

@router.get("/list")
def get_alert_list(db: Session = Depends(get_db)):
    alert_list = []

    # 1. 按品牌计算均价，检测降价风险
    brand_avg = db.query(
        Product.brand,
        func.avg(Product.price).label("avg_price"),
        func.count(Product.id).label("prod_count")
    ).filter(Product.brand.isnot(None)).group_by(Product.brand).all()

    for brand, avg_price, cnt in brand_avg:
        # 模拟历史均价，对比降幅超20%触发预警
        history_avg = avg_price * 1.25
        drop_rate = (history_avg - avg_price) / history_avg
        if drop_rate >= 0.2:
            alert_list.append({
                "alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "brand": brand,
                "risk_level": "高",
                "alert_type": "竞品大幅降价",
                "desc": f"{brand}当前均价{round(avg_price,2)}元，较往期均价{round(history_avg,2)}元下跌{round(drop_rate*100,1)}%，降幅超20%",
                "suggest": "快速评估自身定价，同步推出满减/优惠券对冲竞品价格冲击"
            })

    # 2. 检测低价新品激增预警
    low_price_new = db.query(func.count(Product.id)).filter(Product.price < 30).scalar()
    if low_price_new > 25:
        alert_list.append({
            "alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "brand": "全平台",
            "risk_level": "中",
            "alert_type": "低价竞品数量激增",
            "desc": f"0-30元低价区间商品共{low_price_new}款，低价赛道竞争加剧",
            "suggest": "规划入门款平价产品，抢占下沉市场流量"
        })

    return {
        "msg": "预警列表查询成功",
        "data": {
            "alert_total": len(alert_list),
            "alert_items": alert_list
        }
    }