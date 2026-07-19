from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from datetime import datetime

from utils.crawler import run_crawl_task, crawl_competitor_products
from database.session import get_db

# 初始化定时任务调度器
scheduler = BackgroundScheduler()

# 定时任务：每天凌晨2点执行全平台商品采集
def scheduled_product_crawl():
    db: Session = next(get_db())
    try:
        run_crawl_task(db, target_platform="天猫", keyword="酱油")
        run_crawl_task(db, target_platform="京东", keyword="酱油")
        print(f"[{datetime.now()}] 定时商品采集任务执行完成")
    finally:
        db.close()

# 定时任务：每6小时执行一次竞品监控
def scheduled_competitor_crawl():
    db: Session = next(get_db())
    try:
        crawl_competitor_products(db, brand_keywords=["海天", "千禾"], platform="天猫")
        print(f"[{datetime.now()}] 定时竞品监控任务执行完成")
    finally:
        db.close()

# 启动调度器
def start_scheduler():
    # 服务启动时立即执行一次采集，快速验证效果
    # scheduled_product_crawl()
    # scheduled_competitor_crawl()

    # 每天凌晨2点执行全平台商品采集
    scheduler.add_job(scheduled_product_crawl, "cron", hour=2, minute=0)
    # 每6小时执行一次竞品监控
    scheduler.add_job(scheduled_competitor_crawl, "interval", hours=6)
    scheduler.start()
    print("定时任务调度器已启动")