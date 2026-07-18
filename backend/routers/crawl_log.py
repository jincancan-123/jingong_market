from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from models.crawl_log import CrawlLog
from schemas.crawl_log import CrawlLogCreate, CrawlLogResponse

router = APIRouter(prefix="/crawl_log", tags=["爬虫日志管理"])

# 新增爬取记录
@router.post("/", response_model=CrawlLogResponse)
def create_log(log: CrawlLogCreate, db: Session = Depends(get_db)):
    db_log = CrawlLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

# 根据id查询单条日志
@router.get("/{id}", response_model=CrawlLogResponse)
def get_log(id: int, db: Session = Depends(get_db)):
    log = db.query(CrawlLog).filter(CrawlLog.id == id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    return log

# 查询全部日志
@router.get("/", response_model=List[CrawlLogResponse])
def get_all_logs(db: Session = Depends(get_db)):
    return db.query(CrawlLog).order_by(CrawlLog.crawl_time.desc()).all()