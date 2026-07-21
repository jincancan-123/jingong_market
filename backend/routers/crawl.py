from enum import Enum
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from utils.crawler import run_crawl_task, crawl_competitor_products, crawl_public_opinion

class CrawlPlatform(str, Enum):
    TMALL = "天猫"
    TAOBAO = "淘宝"
    JD = "京东"
    PINDUODUO = "拼多多"
    DOUYIN = "抖音电商"
    XIAOHONGSHU = "小红书"
    SUNING = "苏宁易购"

router = APIRouter(prefix="/crawl", tags=["爬虫任务管理"])

# 1. 通用商品采集接口
@router.post("/run")
def start_crawl(
    platform: CrawlPlatform = Query(..., description="采集平台名称"),
    keyword: str = Query(default="酱油", description="商品关键词"),
    db: Session = Depends(get_db)
):
    result = run_crawl_task(db, platform.value, keyword)
    return {"msg": "采集任务执行完成", "data": result}

# 2. 竞品监控采集接口
@router.post("/competitor")
def start_competitor_crawl(
    platform: CrawlPlatform = Query(default=CrawlPlatform.TMALL, description="采集平台"),
    brand_keywords: List[str] = Query(default=["海天", "千禾"], description="竞品品牌关键词"),
    db: Session = Depends(get_db)
):
    result = crawl_competitor_products(db, brand_keywords, platform.value)
    return {"msg": "竞品采集完成", "data": result}

# 3. 舆情关键词采集接口
@router.post("/opinion")
def start_opinion_crawl(
    hot_keywords: List[str] = Query(default=["零添加", "有机酱油"], description="行业热词"),
    db: Session = Depends(get_db)
):
    result = crawl_public_opinion(db, hot_keywords)
    return {"msg": "舆情采集完成", "data": result}