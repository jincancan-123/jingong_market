from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.session import get_db
from models.product import Product
from utils.ollama_client import generate_ai_analysis

router = APIRouter(prefix="/alert", tags=["异常预警推送"])


@router.get("/list")
def get_alert_list(db: Session = Depends(get_db)):
    alert_list = []

    # 优化点1：统一增加14天时间窗口过滤，避免预警查询扫描历史全量数据。
    cutoff = datetime.now() - timedelta(days=14)
    recent_filter = Product.create_time >= cutoff

    # 1. 按品牌计算均价，检测降价风险
    brand_avg = (
        db.query(
            Product.brand,
            func.avg(Product.price).label("avg_price"),
            func.count(Product.id).label("prod_count"),
        )
        .filter(recent_filter, Product.brand.isnot(None))
        .group_by(Product.brand)
        .all()
    )

    for brand, avg_price, cnt in brand_avg:
        # 模拟历史均价，对比降幅超20%触发预警
        history_avg = avg_price * 1.25 if avg_price else 0
        drop_rate = (history_avg - avg_price) / history_avg if history_avg else 0
        if drop_rate >= 0.2:
            prompt = (
                f"请基于以下商品预警信息，生成一段简洁的中文数据波动归因分析："
                f"品牌={brand}，当前均价={round(avg_price, 2)}元，历史均价={round(history_avg, 2)}元，"
                f"跌幅={round(drop_rate * 100, 1)}%，当前近14天商品数据量={cnt}条。"
                f"请重点说明可能的原因，并给出可执行的运营建议。"
            )
            ai_analysis = generate_ai_analysis(
                prompt,
                fallback=f"{brand}价格下探更可能由竞品促销、渠道补货节奏或品牌侧折扣动作驱动，建议短期内加强价格监控和活动对冲。",
            )
            alert_list.append({
                "alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "brand": brand,
                "risk_level": "高",
                "alert_type": "竞品大幅降价",
                "desc": f"{brand}当前均价{round(avg_price, 2)}元，较往期均价{round(history_avg, 2)}元下跌{round(drop_rate * 100, 1)}%，降幅超20%",
                "suggest": "快速评估自身定价，同步推出满减/优惠券对冲竞品价格冲击",
                "data_ai_analysis": ai_analysis,
            })

    # 2. 检测低价新品激增预警
    low_price_new = (
        db.query(func.count(Product.id))
        .filter(recent_filter, Product.price < 30)
        .scalar()
    )
    if low_price_new > 25:
        prompt = (
            f"请基于以下低价商品激增预警，生成一段简洁的中文数据波动归因分析："
            f"低价区间0-30元商品数量={low_price_new}款，近14天内低价竞争加剧。"
            f"请解释可能的驱动因素，并给出运营或产品建议。"
        )
        ai_analysis = generate_ai_analysis(
            prompt,
            fallback="低价商品激增通常由渠道补货、促销导向和入门级产品扩容共同导致，建议强化价格带分层与流量精准投放。",
        )
        alert_list.append({
            "alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "brand": "全平台",
            "risk_level": "中",
            "alert_type": "低价竞品数量激增",
            "desc": f"0-30元低价区间商品共{low_price_new}款，低价赛道竞争加剧",
            "suggest": "规划入门款平价产品，抢占下沉市场流量",
            "data_ai_analysis": ai_analysis,
        })

    return {
        "msg": "预警列表查询成功",
        "data": {
            "alert_total": len(alert_list),
            "alert_items": alert_list,
        },
    }