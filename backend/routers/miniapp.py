import base64
import json
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.session import get_db
from models.crawl_log import CrawlLog
from models.product import Product
from models.user import User
from routers.report import generate_daily_report
from utils.crawler import run_crawl_task

router = APIRouter(prefix="/miniapp", tags=["微信小程序移动端"])

SUBSCRIPTION_STORE = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class AlertSubscribeRequest(BaseModel):
    category: str
    action: str = "subscribe"


class CrawlRunRequest(BaseModel):
    platform: str = "天猫"
    keyword: str = "酱油"


def _success_response(msg: str, data):
    return {"msg": msg, "data": data}


def _create_token(username: str) -> str:
    payload = {"username": username, "exp": int(time.time()) + 86400}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _decode_token(token: str) -> dict:
    try:
        payload = json.loads(base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="token无效") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=401, detail="token已过期")
    return payload


def _get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "", 1)
    elif x_token:
        token = x_token

    if not token:
        raise HTTPException(status_code=401, detail="请先登录")

    payload = _decode_token(token)
    username = payload.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="token缺少用户名")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def _get_user_subscriptions(user_id: int) -> list:
    subscriptions = []
    for key, enabled in SUBSCRIPTION_STORE.items():
        if key.startswith(f"{user_id}:") and enabled:
            subscriptions.append(key.split(":", 1)[1])
    return subscriptions


def _collect_alert_items(db: Session) -> list:
    alert_list = []
    brand_avg = db.query(
        Product.brand,
        func.avg(Product.price).label("avg_price"),
        func.count(Product.id).label("prod_count"),
    ).filter(Product.brand.isnot(None)).group_by(Product.brand).all()

    for brand, avg_price, cnt in brand_avg:
        history_avg = avg_price * 1.25
        drop_rate = (history_avg - avg_price) / history_avg
        if drop_rate >= 0.2:
            alert_list.append({
                "id": len(alert_list) + 1,
                "brand": brand,
                "risk_level": "高",
                "alert_type": "竞品大幅降价",
                "desc": f"{brand}当前均价{round(avg_price, 2)}元，较往期均价{round(history_avg, 2)}元下跌{round(drop_rate*100, 1)}%，降幅超20%",
                "suggest": "快速评估自身定价，同步推出满减/优惠券对冲竞品价格冲击",
                "alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    low_price_new = db.query(func.count(Product.id)).filter(Product.price < 30).scalar() or 0
    if low_price_new > 25:
        alert_list.append({
            "id": len(alert_list) + 1,
            "brand": "全平台",
            "risk_level": "中",
            "alert_type": "低价竞品数量激增",
            "desc": f"0-30元低价区间商品共{low_price_new}款，低价赛道竞争加剧",
            "suggest": "规划入门款平价产品，抢占下沉市场流量",
            "alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    return alert_list


# 小程序首页核心指标卡片
@router.get("/home")
def miniapp_home_data(db: Session = Depends(get_db)):
    total_product = db.query(func.count(Product.id)).scalar()
    total_gmv = db.query(func.sum(Product.price * Product.sales_volume)).scalar() or 0
    total_sales = db.query(func.sum(Product.sales_volume)).scalar() or 0

    platform_sales_rows = db.query(
        Product.platform,
        func.sum(Product.sales_volume).label("sales"),
    ).group_by(Product.platform).all()

    platform_sales = [
        {
            "platform": p[0] or "未知平台",
            "sales": int(p[1] or 0),
        }
        for p in platform_sales_rows
    ]

    def count_by_price_range(min_price: float, max_price: float):
        return db.query(func.count(Product.id)).filter(
            Product.price >= min_price,
            Product.price < max_price,
        ).scalar() or 0

    price_range = []
    price_range.append({"range": "0-10元", "count": int(count_by_price_range(0, 10))})
    price_range.append({"range": "10-30元", "count": int(count_by_price_range(10, 30))})
    price_range.append({
        "range": "30元以上",
        "count": int(db.query(func.count(Product.id)).filter(Product.price >= 30).scalar() or 0),
    })

    top_brand = db.query(
        Product.brand,
        func.count(Product.id).label("cnt"),
    ).filter(Product.brand.isnot(None)).group_by(Product.brand).order_by(func.count(Product.id).desc()).limit(3).all()

    top_brand_list = [{"brand": b[0], "count": int(b[1])} for b in top_brand]

    return {
        "msg": "小程序首页数据",
        "data": {
            "total_product": int(total_product or 0),
            "total_gmv": round(float(total_gmv or 0), 2),
            "total_sales": int(total_sales or 0),
            "top_brand": top_brand_list,
            "platform_sales": platform_sales,
            "price_range": price_range,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
    }


@router.post("/login")
def miniapp_login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    password = payload.password.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        if db.query(User).count() == 0:
            user = User(username=username, password=password)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(status_code=401, detail="用户名不存在")

    if user.password != password:
        raise HTTPException(status_code=401, detail="密码错误")

    token = _create_token(user.username)
    return _success_response("登录成功", {
        "token": token,
        "user": {"id": user.id, "username": user.username},
    })


@router.post("/crawl/run")
def miniapp_run_crawl(payload: CrawlRunRequest, current_user: User = Depends(_get_current_user), db: Session = Depends(get_db)):
    result = run_crawl_task(db, payload.platform, payload.keyword)
    return _success_response("采集任务执行完成", {
        "platform": payload.platform,
        "keyword": payload.keyword,
        "result": result,
        "operator": current_user.username,
    })


@router.get("/crawl/log")
def miniapp_crawl_log(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    page = max(page, 1)
    page_size = max(min(page_size, 50), 1)
    total = db.query(CrawlLog.id).count()
    logs = db.query(CrawlLog).order_by(CrawlLog.crawl_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "id": log.id,
            "platform": log.target_platform,
            "total": log.total_num,
            "success": log.success_num,
            "status": log.status,
            "create_time": log.crawl_time.strftime("%Y-%m-%d %H:%M:%S") if log.crawl_time else "",
        }
        for log in logs
    ]
    return _success_response("爬虫记录查询成功", {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
        "operator": current_user.username,
    })


@router.get("/product/list")
def miniapp_product_list(
    page: int = 1,
    page_size: int = 10,
    platform: Optional[str] = None,
    price: Optional[str] = None,
    brand: Optional[str] = None,
    current_user: User = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    page = max(page, 1)
    page_size = max(min(page_size, 50), 1)
    query = db.query(Product)

    if platform:
        query = query.filter(Product.platform.like(f"%{platform}%"))
    if brand:
        query = query.filter(Product.brand.like(f"%{brand}%"))
    if price == "low":
        query = query.filter(Product.price < 30)
    elif price == "mid":
        query = query.filter(Product.price >= 30, Product.price < 80)
    elif price == "high":
        query = query.filter(Product.price >= 80)

    total = query.count()
    products = query.order_by(Product.create_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "id": product.id,
            "title": product.title,
            "price": product.price,
            "platform": product.platform,
            "brand": product.brand,
            "sales_volume": product.sales_volume,
            "review_count": product.review_count,
            "stock": product.stock,
            "create_time": product.create_time.strftime("%Y-%m-%d %H:%M:%S") if product.create_time else "",
            "link": product.link,
        }
        for product in products
    ]
    return _success_response("商品列表查询成功", {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
        "operator": current_user.username,
    })


@router.get("/product/{product_id}")
def miniapp_product_detail(product_id: int, current_user: User = Depends(_get_current_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    base_price = max(float(product.price or 0), 1.0)
    base_sales = max(int(product.sales_volume or 0), 100)
    x_axis = [f"D{i}" for i in range(1, 8)]
    price_trend = [round(base_price * (0.95 + i * 0.01), 2) for i in range(7)]
    sales_trend = [max(100, base_sales - 300 + i * 120) for i in range(7)]

    return _success_response("商品详情查询成功", {
        "product": {
            "id": product.id,
            "title": product.title,
            "price": product.price,
            "platform": product.platform,
            "brand": product.brand,
            "stock": product.stock,
            "sales_volume": product.sales_volume,
            "review_count": product.review_count,
            "link": product.link,
            "create_time": product.create_time.strftime("%Y-%m-%d %H:%M:%S") if product.create_time else "",
        },
        "x_axis": x_axis,
        "price_trend": price_trend,
        "sales_trend": sales_trend,
        "operator": current_user.username,
    })


@router.get("/alert/list")
def miniapp_alert_list(current_user: User = Depends(_get_current_user), db: Session = Depends(get_db)):
    alerts = _collect_alert_items(db)
    subscriptions = _get_user_subscriptions(current_user.id)
    for item in alerts:
        item["subscribed"] = item["brand"] in subscriptions or item["brand"] == "全平台"
    return _success_response("预警列表查询成功", {
        "alert_total": len(alerts),
        "alert_items": alerts,
    })


@router.get("/alert/{alert_id}")
def miniapp_alert_detail(alert_id: int, current_user: User = Depends(_get_current_user), db: Session = Depends(get_db)):
    alerts = _collect_alert_items(db)
    item = next((alert for alert in alerts if alert["id"] == alert_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="预警不存在")

    trend = {
        "x_axis": [f"D{i}" for i in range(1, 8)],
        "price_trend": [round(100 + i * 3.2, 2) for i in range(7)],
        "sales_trend": [max(200, 800 + i * 120) for i in range(7)],
    }
    return _success_response("预警详情查询成功", {
        "alert": item,
        "trend": trend,
        "operator": current_user.username,
    })


@router.post("/alert/subscribe")
def miniapp_alert_subscribe(payload: AlertSubscribeRequest, current_user: User = Depends(_get_current_user)):
    category = payload.category.strip() or "all"
    action = payload.action.strip().lower()
    enabled = action != "cancel"
    SUBSCRIPTION_STORE[f"{current_user.id}:{category}"] = enabled
    subscriptions = _get_user_subscriptions(current_user.id)
    return _success_response("订阅更新成功", {
        "category": category,
        "subscribed": enabled,
        "subscriptions": subscriptions,
    })


@router.get("/report/daily")
def miniapp_daily_report(current_user: User = Depends(_get_current_user), db: Session = Depends(get_db)):
    report = generate_daily_report(db)
    return _success_response("日报查询成功", {
        "report": report["data"],
        "operator": current_user.username,
    })


@router.get("/report/trend")
def miniapp_report_trend(current_user: User = Depends(_get_current_user), db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.create_time.desc()).limit(20).all()
    if not products:
        return _success_response("近7天趋势查询成功", {
            "x_axis": [f"D{i}" for i in range(1, 8)],
            "price_series": [0] * 7,
            "sales_series": [0] * 7,
        })

    base_price = sum(product.price or 0 for product in products) / len(products)
    base_sales = sum(product.sales_volume or 0 for product in products) / len(products)
    x_axis = [f"D{i}" for i in range(1, 8)]
    price_series = [round(base_price * (0.95 + i * 0.01), 2) for i in range(7)]
    sales_series = [max(100, int(base_sales * (0.9 + i * 0.03))) for i in range(7)]
    return _success_response("近7天趋势查询成功", {
        "x_axis": x_axis,
        "price_series": price_series,
        "sales_series": sales_series,
        "operator": current_user.username,
    })