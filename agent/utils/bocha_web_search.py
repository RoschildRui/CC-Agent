import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


# API key and endpoint should be configured via environment variables
# See env_example.txt for configuration template
DEFAULT_BOCHA_API_KEY = ""  # Set via BOCHA_API_KEY environment variable
DEFAULT_BOCHA_ENDPOINT = "https://api.bocha.cn/v1/web-search"


@dataclass
class WebDoc:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    published_at: str = ""


def _get_bocha_api_key() -> str:
    # Prefer environment variable; fallback is provided by the user to keep the app working out-of-the-box.
    return (os.getenv("BOCHA_API_KEY") or "").strip() or DEFAULT_BOCHA_API_KEY


def bocha_web_search(
    query: str,
    *,
    count: int = 5,
    freshness: str = "noLimit",  # 修正: 文档仅支持 "noLimit" 或 "oneDay"
    summary: bool = True,
    timeout: int = 30,
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call Bocha Web Search API.
    Returns raw JSON from the API (and includes some meta fields for debugging).
    """
    endpoint = endpoint or (os.getenv("BOCHA_WEB_SEARCH_ENDPOINT") or "").strip() or DEFAULT_BOCHA_ENDPOINT
    api_key = (api_key or "").strip() or _get_bocha_api_key()

    payload: Dict[str, Any] = {
        "query": query,
        "count": int(count),
        "freshness": freshness,
        "summary": bool(summary),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print(f"🔍 Bocha API调用: query='{query}', count={count}")
    t0 = time.time()
    resp = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
    dt_ms = int((time.time() - t0) * 1000)

    try:
        data = resp.json()
    except Exception:
        data = {"_raw_text": resp.text}

    print(f"✓ Bocha响应: status={resp.status_code}, 耗时={dt_ms}ms")

    return {
        "_meta": {
            "endpoint": endpoint,
            "status_code": resp.status_code,
            "elapsed_ms": dt_ms,
            "query": query,
        },
        "data": data,
    }


def normalize_bocha_results(raw: Dict[str, Any]) -> List[WebDoc]:
    """
    Best-effort normalization across possible response shapes.
    根据Bocha API实际响应格式解析。
    响应格式: {code: 200, data: {webPages: {value: [...]}}}
    """
    # Bocha API 响应有两层: raw["data"]["data"]["webPages"]["value"]
    data = raw.get("data", raw)
    # 如果外层data包含code字段，说明还需要再取一层
    if isinstance(data, dict) and "code" in data:
        data = data.get("data", data)

    candidates: List[Any] = []
    if isinstance(data, dict):
        # Bocha API 的标准格式: data.webPages.value[]
        if "webPages" in data and isinstance(data["webPages"], dict):
            value = data["webPages"].get("value", [])
            if isinstance(value, list):
                candidates = value
        # 兼容其他可能的格式
        if not candidates:
            for path in (
                ("data", "results"),
                ("results",),
                ("data",),
                ("items",),
            ):
                cur: Any = data
                ok = True
                for k in path:
                    if isinstance(cur, dict) and k in cur:
                        cur = cur[k]
                    else:
                        ok = False
                        break
                if ok and isinstance(cur, list):
                    candidates = cur
                    break

    docs: List[WebDoc] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        # Bocha API 字段: name, url, snippet, siteName, datePublished
        title = str(item.get("title") or item.get("name") or "").strip()
        url = str(item.get("url") or item.get("link") or item.get("sourceUrl") or "").strip()
        snippet = str(item.get("snippet") or item.get("summary") or item.get("description") or "").strip()
        source = str(item.get("source") or item.get("site") or item.get("siteName") or "").strip()
        published_at = str(item.get("published_at") or item.get("date") or item.get("publishedAt") or item.get("datePublished") or "").strip()
        if not url and not title:
            continue
        docs.append(WebDoc(title=title or url, url=url or "", snippet=snippet, source=source, published_at=published_at))
    return docs


