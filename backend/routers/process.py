from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from utils.data_process import get_data_clean_board, add_product_label, platform_contribution_analysis, get_data_trace

router = APIRouter(prefix="/process", tags=["数据加工工厂"])

# 1. 数据清洗看板接口
@router.get("/clean-board")
def get_clean_board(db: Session = Depends(get_db)):
    data = get_data_clean_board(db)
    return {"msg": "数据质量统计完成", "data": data}

# 2. 商品智能标签生成接口
@router.get("/label/{product_id}")
def gen_product_label(product_id: int, db: Session = Depends(get_db)):
    label = add_product_label(db, product_id)
    return {"msg": "标签生成成功", "data": label}

# 3. 平台销量归因分析接口
@router.get("/attribution")
def get_platform_attribution(db: Session = Depends(get_db)):
    res = platform_contribution_analysis(db)
    return {"msg": "归因分析完成", "data": res}

# 4. 数据血缘追溯接口
@router.get("/trace/{product_id}")
def get_data_lineage(product_id: int, db: Session = Depends(get_db)):
    trace = get_data_trace(db, product_id)
    return {"msg": "数据血缘链路查询完成", "data": trace}