import json
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .api_utils import call_ai_api
from .bocha_web_search import WebDoc, bocha_web_search, normalize_bocha_results


@dataclass
class WebSearchQueryRun:
    query: str
    docs: List[WebDoc] = field(default_factory=list)
    per_query_summary: str = ""


@dataclass
class WebSearchSession:
    runs: List[WebSearchQueryRun] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def all_docs(self) -> List[WebDoc]:
        docs: List[WebDoc] = []
        for r in self.runs:
            docs.extend(r.docs)
        return docs

    def references_markdown(self, *, include_per_query_summaries: bool = True) -> str:
        """
        Return a ChatGPT-style web-search appendix that renders reliably in marked.js:
        - Web search (per-query summaries)
        - References (summarized): each reference includes its snippet/summary
        """
        docs = self.all_docs()
        if not docs:
            return ""

        lines: List[str] = []
        # lines.append("### Web search")

        if include_per_query_summaries:
            for idx, r in enumerate(self.runs, start=1):
                if not r.docs:
                    continue
                summary = (r.per_query_summary or "").strip() or "No summary available."
                lines.append(f"**Query {idx}**: {r.query}")
                lines.append(summary)
                lines.append("")

        lines.append("### References (summarized)")
        for i, d in enumerate(docs, start=1):
            title = (d.title or "").strip() or d.url or f"Source {i}"
            if d.url:
                lines.append(f"[{i}] **{title}** — `{d.url}`")
            else:
                lines.append(f"[{i}] **{title}**")

            snippet = (d.snippet or "").strip()
            if snippet:
                snippet = " ".join(snippet.split())
                lines.append(f"> {snippet}")
            lines.append("")

        return "\n".join(lines).strip()


def _doc_ref_index(all_docs: List[WebDoc], d: WebDoc) -> int:
    try:
        return all_docs.index(d) + 1
    except ValueError:
        return 1


def decide_web_search_queries(
    *,
    user_intent: str,
    model_pool=None,
    model_name: Optional[str] = None,
    max_queries: int = 3,
) -> Tuple[bool, List[str], str]:
    """
    Use the LLM to decide whether to web search and propose queries.
    Returns: (should_search, queries, reason)
    """
    planner_system = (
        "You are a web-search planner. Decide if web search is needed to answer accurately.\n"
        "Return ONLY valid JSON: "
        "{\"should_search\": boolean, \"queries\": [string], \"reason\": string}.\n"
        f"Constraints: queries length <= {max_queries}. Queries must be concrete and searchable."
    )
    messages = [
        {"role": "system", "content": planner_system},
        {"role": "user", "content": user_intent.strip()[:6000]},
    ]

    raw = call_ai_api(messages, response_format="json_object", temp=0.2, model_name=model_name, model_pool=model_pool)
    try:
        obj = json.loads(raw)
    except Exception:
        return False, [], "planner_parse_error"

    should = bool(obj.get("should_search", False))
    queries = obj.get("queries") or []
    if not isinstance(queries, list):
        queries = []
    queries = [str(q).strip() for q in queries if str(q).strip()][:max_queries]
    reason = str(obj.get("reason") or "").strip()
    return should and len(queries) > 0, queries, reason


def run_web_search_session(
    queries: List[str],
    *,
    count: int = 5,
    freshness: str = "noLimit",  # 修正: 文档仅支持 "noLimit" 或 "oneDay"
    summary: bool = True,
) -> WebSearchSession:
    """
    Execute Bocha web search for each query; produce lightweight per-query summaries from snippets.
    """
    session = WebSearchSession()
    for q in queries:
        raw = bocha_web_search(q, count=count, freshness=freshness, summary=summary)
        docs = normalize_bocha_results(raw)
        print(f"📄 解析得到 {len(docs)} 个文档")
        per_query_summary = _heuristic_summary_from_docs(docs)
        session.runs.append(WebSearchQueryRun(query=q, docs=docs, per_query_summary=per_query_summary))
    return session


def build_web_context_block(session: WebSearchSession, *, max_docs: int = 8) -> str:
    """
    Compact evidence block to inject into prompts.
    """
    docs = session.all_docs()[:max_docs]
    if not docs:
        return ""

    lines: List[str] = []
    lines.append("### Web search evidence")
    for i, d in enumerate(docs, start=1):
        snippet = (d.snippet or "").strip()
        snippet = snippet.replace("\n", " ").strip()
        if len(snippet) > 280:
            snippet = snippet[:277] + "..."
        if d.url:
            lines.append(f"[{i}] {d.title} — `{d.url}`")
        else:
            lines.append(f"[{i}] {d.title}")
        if snippet:
            lines.append(f"    - {snippet}")
    return "\n".join(lines)


def summarize_web_docs_with_llm(
    session: WebSearchSession,
    *,
    model_pool=None,
    model_name: Optional[str] = None,
    max_docs: int = 10,
) -> str:
    """
    Single 'large model' call to summarize retrieved docs, per requirement.
    """
    docs = session.all_docs()[:max_docs]
    if not docs:
        return ""

    payload_lines: List[str] = []
    for i, d in enumerate(docs, start=1):
        payload_lines.append(f"[{i}] Title: {d.title}\nURL: {d.url}\nSnippet: {d.snippet}".strip())

    system = (
        "Summarize the web-search documents provided by the user.\n"
        "Write a concise synthesis and clearly cite sources like [1], [2] where relevant.\n"
        "Output plain text (no JSON)."
    )
    user = "\n\n".join(payload_lines)

    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return call_ai_api(messages, response_format="text", temp=0.2, model_name=model_name, model_pool=model_pool).strip()


def pick_large_model_name(model_pool) -> Optional[str]:
    """
    Best-effort choice: prefer reasoning/large models when present; fallback to None (random).
    """
    if not model_pool:
        return None
    names = list(model_pool.keys())
    preferred_keywords = [
        "DeepSeek-R1",
        "DeepSeek-V3",
        "deepseek-reasoner",
        "deepseek-chat",
        "kimi-k2",
    ]
    for kw in preferred_keywords:
        for n in names:
            if kw.lower() in n.lower():
                return n
    return names[0] if names else None


def _heuristic_summary_from_docs(docs: List[WebDoc]) -> str:
    """
    Lightweight summary (no extra model call): compress snippets into 1-2 sentences.
    """
    snippets = [d.snippet.strip() for d in docs if d.snippet and d.snippet.strip()]
    if not snippets:
        return "Top results were retrieved; snippets were not provided."
    joined = " ".join(snippets)
    joined = " ".join(joined.split())
    if len(joined) > 260:
        joined = joined[:257] + "..."
    return joined


