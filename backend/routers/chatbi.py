from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from utils.sql_bi import chat_bi_service

router = APIRouter(prefix="/chatbi", tags=["ChatBI"])


@router.post("/ask")
def ask_chatbi(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    session_id = str(payload.get("session_id", "default")).strip() or "default"
    history = payload.get("history")

    if not question:
        raise HTTPException(status_code=400, detail="question 不能为空")

    try:
        return chat_bi_service.ask(question, db, session_id=session_id, history=history)
    except Exception as exc:
        print(f"[chatbi] 处理失败: {exc}")
        return {
            "answer": "抱歉，当前查询暂时无法完成，请稍后再试。",
            "sql": None,
            "rows": [],
            "row_count": 0,
            "session_id": session_id,
            "history": history or [],
        }
