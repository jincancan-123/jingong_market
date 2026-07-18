from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.session import get_db
from models.product import Product
from datetime import datetime

router = APIRouter(prefix="/report", tags=["智能营销报告"])

@router.get("/daily")
def generate_daily_report(db: Session = Depends(get_db)):
    # 1. 拉取核心指标
    total_product = db.query(func.count(Product.id)).scalar()
    total_gmv = db.query(func.sum(Product.price * Product.sales_volume)).scalar() or 0
    total_sales = db.query(func.sum(Product.sales_volume)).scalar() or 0

    # 2. 平台维度数据
    platform_stats = db.query(
        Product.platform,
        func.sum(Product.sales_volume).label("sales"),
        func.sum(Product.price * Product.sales_volume).label("gmv")
    ).group_by(Product.platform).all()
    platform_list = [
        {"platform": p[0] or "未知平台", "sales": p[1] or 0, "gmv": p[2] or 0}
        for p in platform_stats
    ]
    # 计算销量最高平台
    top_platform = max(platform_list, key=lambda x: x["sales"])

    # 3. 竞品品牌数据
    brand_stats = db.query(
        Product.brand,
        func.count(Product.id).label("count"),
        func.avg(Product.price).label("avg_price")
    ).filter(Product.brand.isnot(None)).group_by(Product.brand).all()
    brand_list = [
        {"brand": b[0], "count": b[1], "avg_price": round(b[2], 2)}
        for b in brand_stats
    ]

    # 4. 价格带分布
    low_price_cnt = db.query(Product).filter(Product.price < 30).count()
    mid_price_cnt = db.query(Product).filter(Product.price >= 30, Product.price < 80).count()
    high_price_cnt = db.query(Product).filter(Product.price >= 80).count()

    # 5. 【模拟LLM生成】结构化日报内容
    report_content = f"""# 调味品行业营销日报
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 一、核心数据概览
- 监控商品总数：{total_product} 款
- 全平台估算总GMV：{round(total_gmv, 2)} 元
- 累计总销量：{total_sales} 件
- 销量主导平台：{top_platform['platform']}

## 二、平台渠道分析
"""
    for p in platform_list:
        report_content += f"- {p['platform']}：销量{p['sales']}件，贡献GMV {round(p['gmv'],2)} 元\n"

    report_content += f"""
## 三、竞品品牌动态
当前监控 {len(brand_list)} 个核心竞品品牌：
"""
    for b in brand_list:
        report_content += f"- {b['brand']}：在售{b['count']}款，均价 {b['avg_price']} 元\n"

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
            "generate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_type": "每日营销日报",
            "content": report_content,
            "summary": {
                "total_product": total_product,
                "total_gmv": round(total_gmv, 2),
                "total_sales": total_sales,
                "top_platform": top_platform["platform"]
            }
        }
    }