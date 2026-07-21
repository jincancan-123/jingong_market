import os
from typing import Optional

import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
# 切换为轻量级通用模型 qwen2.5:1.5b，适配本地轻量推理
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")


def generate_ai_analysis(prompt: str, fallback: Optional[str] = None, model: str = OLLAMA_MODEL) -> str:
    """轻量化调用本地 Ollama qwen2.5:1.5b，失败时自动返回兜底文案。"""
    if not prompt:
        return fallback or "当前数据波动较小，建议继续关注竞品与价格带变化。"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 200,
        },
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        text = (data.get("response") or "").strip()
        if text:
            return text
    except Exception as exc:
        print(f"[ollama] 调用失败: {exc}")

    return fallback or "当前数据波动主要由竞品促销、价格带重叠与渠道流量变化共同驱动，建议关注短期价格与库存节奏。"