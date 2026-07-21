import re
import traceback
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from utils.ollama_client import generate_ai_analysis


class ChatBIService:
    """轻量级自然语言查数服务：自然语言 -> 安全SQL -> 查询 -> 摘要。"""

    def __init__(self) -> None:
        self.max_rows = 10
        self.allowed_tables = {"product", "crawl_log", "user"}
        self.history_cache: Dict[str, List[Dict[str, str]]] = {}

    def ask(
        self,
        question: str,
        db: Session,
        session_id: str = "default",
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        if not question or not question.strip():
            return self._build_result(
                answer="请给我一个明确的业务问题，例如“上周海天酱油销量走势”。",
                sql=None,
                rows=[],
                session_id=session_id,
                history=self._get_history(session_id, history),
            )

        conversation_history = self._get_history(session_id, history)
        sql_text = self._generate_safe_sql(question, conversation_history, relax=False)
        sql_text = self._sanitize_sql(sql_text)

        rows: List[Dict[str, Any]] = []
        row_count = 0
        used_relaxed_retry = False
        try:
            result = db.execute(text(sql_text))
            rows = [dict(row._mapping) for row in result]
            row_count = len(rows)
        except Exception as exc:
            print(f"[chatbi] SQL 执行失败: {exc}")
            print(traceback.format_exc())
            answer = (
                "当前查询没有得到有效结果，通常是字段名或条件表达不匹配。"
                "请换一个更明确的表述，例如“最近7天商品销量趋势”。"
            )
            return self._build_result(
                answer=answer,
                sql=sql_text,
                rows=[],
                session_id=session_id,
                history=self._append_history(conversation_history, question, answer),
            )

        if not rows:
            relaxed_sql = self._generate_safe_sql(question, conversation_history, relax=True)
            relaxed_sql = self._sanitize_sql(relaxed_sql)
            try:
                result = db.execute(text(relaxed_sql))
                rows = [dict(row._mapping) for row in result]
                row_count = len(rows)
                sql_text = relaxed_sql
                used_relaxed_retry = True
            except Exception as exc:
                print(f"[chatbi] 宽松 SQL 重试失败: {exc}")
                print(traceback.format_exc())

        if not rows:
            answer = self._build_empty_answer(question, sql_text, used_relaxed_retry)
            return self._build_result(
                answer=answer,
                sql=sql_text,
                rows=[],
                row_count=0,
                session_id=session_id,
                history=self._append_history(conversation_history, question, answer),
            )

        summary_prompt = self._build_summary_prompt(question, sql_text, rows)
        try:
            summary = generate_ai_analysis(
                summary_prompt,
                fallback="当前数据已返回，但模型摘要暂时不可用。",
            )
        except Exception as exc:
            print(f"[chatbi] 生成业务总结异常: {exc}")
            print(traceback.format_exc())
            summary = "当前数据已返回，但模型摘要暂时不可用。"
        summary = self._clean_output(summary)

        history_with_turn = self._append_history(conversation_history, question, summary)
        return self._build_result(
            answer=summary,
            sql=sql_text,
            rows=rows[: self.max_rows],
            row_count=row_count,
            session_id=session_id,
            history=history_with_turn,
        )

    def _generate_safe_sql(self, question: str, history: List[Dict[str, str]], relax: bool = False) -> str:
        prompt = self._build_sql_prompt(question, history, relax=relax)
        try:
            raw_text = generate_ai_analysis(
                prompt,
                fallback="SELECT * FROM product ORDER BY create_time DESC LIMIT 10",
            )
        except Exception as exc:
            print(f"[chatbi] 生成 SQL 异常: {exc}")
            print(traceback.format_exc())
            return "SELECT * FROM product ORDER BY create_time DESC LIMIT 10"

        extracted = self._extract_sql(raw_text)
        if extracted:
            return extracted
        return "SELECT * FROM product ORDER BY create_time DESC LIMIT 10"

    def _build_sql_prompt(self, question: str, history: List[Dict[str, str]], relax: bool = False) -> str:
        history_text = ""
        if history:
            recent = history[-4:]
            history_text = "\n".join(
                f"Q: {item.get('question','')}\nA: {item.get('answer','')}" for item in recent
            )

        relax_instruction = ""
        if relax:
            relax_instruction = "\n宽松版：时间范围尽量放宽到近30天。"

        return f"""
请生成一条安全的 SELECT SQL。
表：product(id, title, price, platform, link, stock, sales_volume, review_count, create_time, brand)

要求：
1. 只输出 SQL。
2. 只查单表，LIMIT {self.max_rows}。
3. 品牌/品类用 title LIKE '%关键词%'，不要用 brand 条件。
4. 平台优先用 title LIKE '%天猫%' 或 platform = '天猫'。
5. 上周/最近7天用 create_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)。{relax_instruction}

问题：{question}
历史：{history_text}

返回 SQL。
""".strip()

    def _build_summary_prompt(self, question: str, sql_text: str, rows: List[Dict[str, Any]]) -> str:
        row_text = "\n".join(str(row) for row in rows[: self.max_rows])
        return f"""
请用简短中文总结结果。
要求：
1. 先给结论，再给 1-2 条关键观察。
2. 不要只列表格，要讲业务含义。
3. 数据为空时，礼貌说明当前数据不足。
4. 只基于下面的少量数据，不要猜测。

问题：{question}
SQL：{sql_text}
数据：
{row_text}
""".strip()

    def _build_empty_answer(self, question: str, sql_text: str, used_relaxed_retry: bool) -> str:
        if used_relaxed_retry:
            return (
                "当前查询没有命中相关记录，已按更宽松条件再试一次。"
                "这更像是“无匹配数据”而不是 SQL 语法问题。"
                "建议把时间范围扩大到近 30 天，或换成更常见的品牌/平台关键词后再试。"
            )
        return (
            "当前查询没有命中相关记录，可能是关键词或时间范围过窄。"
            "如果你确定输入是正确的，请先检查是否是 SQL 条件写法不兼容，例如品牌/平台字段筛选不当。"
            "建议优先使用商品标题里的关键词进行检索，并把时间范围扩大到近 30 天。"
        )

    def _sanitize_sql(self, sql_text: str) -> str:
        sql_text = (sql_text or "").strip()
        if not sql_text:
            return f"SELECT * FROM product ORDER BY create_time DESC LIMIT {self.max_rows}"

        original_sql = sql_text
        sql_text = self._clean_output(sql_text)
        sql_text = sql_text.strip()

        if ";" in sql_text:
            raise ValueError("SQL 中不允许包含多条语句")

        if not re.search(r"^select\b", sql_text, re.I):
            raise ValueError("只允许 SELECT 查询")

        forbidden = re.compile(
            r"\b(delete|drop|update|insert|alter|truncate|create|replace|merge|grant|revoke|exec|execute)\b",
            re.I,
        )
        if forbidden.search(sql_text):
            raise ValueError("包含不安全的 SQL 关键字")

        text_lower = sql_text.lower()
        if text_lower.count(" from ") != 1:
            raise ValueError("只允许单表查询")

        table_match = re.search(r"\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql_text, re.I)
        if not table_match:
            raise ValueError("缺少 FROM 子句")
        table_name = table_match.group(1).lower()
        if table_name not in self.allowed_tables:
            raise ValueError("查询表不在允许列表中")

        rewritten = False

        def rewrite_equal_condition(match: re.Match[str]) -> str:
            nonlocal rewritten
            rewritten = True
            field_name = match.group(1).lower()
            value = match.group(2).strip().strip("'\"")
            if field_name in {"brand", "platform", "target_platform"}:
                if field_name == "brand":
                    return f"title LIKE '%{value}%'"
                return f"title LIKE '%{value}%'"
            return match.group(0)

        sql_text = re.sub(
            r"\b(brand|platform|target_platform)\s*=\s*'([^']*)'",
            rewrite_equal_condition,
            sql_text,
            flags=re.I,
        )
        sql_text = re.sub(
            r'\b(brand|platform|target_platform)\s*=\s*"([^"]*)"',
            rewrite_equal_condition,
            sql_text,
            flags=re.I,
        )

        if rewritten:
            print(f"[chatbi] SQL 改写: {original_sql} -> {sql_text}")

        if re.search(r"\blimit\b", text_lower):
            sql_text = re.sub(
                r"\blimit\s+(\d+)",
                lambda m: f"LIMIT {min(self.max_rows, int(m.group(1)))}",
                sql_text,
                flags=re.I,
            )
        else:
            sql_text = f"{sql_text} LIMIT {self.max_rows}"

        return sql_text

    def _extract_sql(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        text = self._clean_output(raw_text)
        match = re.search(r"<tool_call>(.*?)</tool_call>", text, flags=re.S | re.I)
        if match:
            return match.group(1).strip()

        match = re.search(r"```sql\s*(.*?)```", text, flags=re.S | re.I)
        if match:
            return match.group(1).strip()

        for match in re.finditer(r"\bselect\b", text, flags=re.I):
            start = match.start()
            end = text.find(";", start)
            if end == -1:
                end = len(text)
            candidate = text[start:end].strip()
            if candidate:
                return candidate

        return ""

    def _clean_output(self, text: str) -> str:
        if not text:
            return ""
        cleaned = text.strip()
        cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.S | re.I)
        cleaned = re.sub(r"<\/think>", "", cleaned, flags=re.I)
        cleaned = re.sub(r"<thinking>.*?</thinking>", "", cleaned, flags=re.S | re.I)
        cleaned = re.sub(r"\[\/?.*?思考.*?\]", "", cleaned, flags=re.I)
        cleaned = re.sub(r"```(?:sql|json|text)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"```", "", cleaned)
        cleaned = re.sub(r"\n+", "\n", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _get_history(self, session_id: str, history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        if history:
            return history
        return self.history_cache.get(session_id, [])

    def _append_history(self, history: List[Dict[str, str]], question: str, answer: str) -> List[Dict[str, str]]:
        history = list(history or [])
        history.append({"question": question, "answer": answer})
        if len(history) > 8:
            history = history[-8:]
        return history

    def _build_result(
        self,
        answer: str,
        sql: Optional[str],
        rows: List[Dict[str, Any]],
        session_id: str,
        history: List[Dict[str, str]],
        row_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        result = {
            "answer": answer,
            "sql": sql,
            "rows": rows,
            "row_count": row_count if row_count is not None else len(rows),
            "session_id": session_id,
            "history": history,
        }
        self.history_cache[session_id] = history
        return result


chat_bi_service = ChatBIService()
