"""StudySearch: 可追溯的本地 PDF 检索。核心算法与界面共用这一文件。"""
from __future__ import annotations

import hashlib
import html
import io
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import jieba
import pymupdf
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parent
STOPWORDS = set("的 了 是 在 和 与 及 或 一个 什么 如何 为什么 请 请问 可以 进行 我 你 它 这 那 有 哪些 怎么".split())
MAX_BYTES = 30 * 1024 * 1024
MAX_PAGES = 500


def tokenize(text: str) -> list[str]:
    """同一分词器服务于两种算法；保留单字术语和英文字母。"""
    return [w for w in jieba.lcut(text.lower())
            if w.strip() and w not in STOPWORDS and re.search(r"[\w\u4e00-\u9fff]", w)]


@dataclass(frozen=True)
class Chunk:
    source: str
    document_id: str
    page: int
    chunk_id: str
    text: str


def split_text(text: str, size: int = 450, overlap: int = 70) -> list[str]:
    """页内切块，不跨页；优先在句末截断，长句有长度上限。"""
    if size < 50 or not 0 <= overlap < size // 2:
        raise ValueError("切块参数无效")
    text = re.sub(r"[ \t]+", " ", text).strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            candidates = [m.end() for m in re.finditer(r"[。！？；\n]", text[start:end])]
            candidates = [n for n in candidates if n >= size // 2]
            if candidates:
                end = start + candidates[-1]
        part = text[start:end].strip()
        if part:
            chunks.append(part)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def extract_pdf(name: str, data: bytes) -> tuple[list[Chunk], list[str]]:
    if len(data) > MAX_BYTES:
        raise ValueError("单份 PDF 请控制在 30 MB 以内")
    doc_id = hashlib.sha256(data).hexdigest()[:16]
    chunks, warnings = [], []
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError("无法读取 PDF，文件可能损坏或格式不正确") from exc
    with doc:
        if doc.needs_pass:
            raise ValueError("暂不支持加密 PDF，请先提供可直接打开的副本")
        if len(doc) > MAX_PAGES:
            raise ValueError("单份 PDF 最多支持 500 页，请拆分后上传")
        empty = []
        for page_no, page in enumerate(doc, 1):
            text = page.get_text("text", sort=True)
            if not text.strip():
                empty.append(page_no)
                continue
            for number, part in enumerate(split_text(text), 1):
                chunks.append(Chunk(name, doc_id, page_no,
                                    f"{doc_id}-p{page_no}-c{number}", part))
        if empty:
            warnings.append(f"{name}：第 {', '.join(map(str, empty[:20]))} 页未提取到文字"
                            + ("等" if len(empty) > 20 else "") + "，可能是扫描页或空白页；本版不含 OCR。")
    return chunks, warnings


class SearchIndex:
    def __init__(self, chunks: list[Chunk]):
        if not chunks:
            raise ValueError("没有可检索的文字")
        self.chunks = chunks
        self.token_sets = [set(tokenize(c.text)) for c in chunks]
        self.vectorizer = TfidfVectorizer(tokenizer=tokenize, token_pattern=None,
                                        lowercase=False, sublinear_tf=True)
        try:
            self.matrix = self.vectorizer.fit_transform(c.text for c in chunks)
        except ValueError as exc:
            raise ValueError("资料中没有有效词语，无法建立索引") from exc

    def search(self, query: str, method: str = "tfidf", top_k: int = 5,
               document_ids: set[str] | None = None) -> list[dict]:
        terms = set(tokenize(query))
        if not terms:
            return []
        if method == "tfidf":
            # 默认 L2 归一化后，向量内积等于余弦相似度。
            scores = (self.matrix @ self.vectorizer.transform([query]).T).toarray().ravel()
        elif method == "keyword":
            scores = [len(terms & s) / len(terms) for s in self.token_sets]
        else:
            raise ValueError("未知检索方法")
        candidates = [i for i, score in enumerate(scores) if score > 0
                      and (document_ids is None or self.chunks[i].document_id in document_ids)]
        candidates.sort(key=lambda i: (-float(scores[i]), i))
        return [{**asdict(self.chunks[i]), "score": float(scores[i])}
                for i in candidates[:max(0, top_k)]]


def highlighted(text: str, query: str) -> str:
    terms = sorted(set(tokenize(query)), key=len, reverse=True)
    if not terms:
        return html.escape(text)
    pattern = re.compile("(" + "|".join(re.escape(t) for t in terms) + ")", re.I)
    # 逐段转义，PDF 内容不能插入 HTML 或脚本。
    return "".join(f"<mark>{html.escape(p)}</mark>" if i % 2 else html.escape(p)
                   for i, p in enumerate(pattern.split(text)))


def page_preview(data: bytes, page: int) -> bytes:
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        return doc[page - 1].get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2)).tobytes("png")


def main():
    import streamlit as st

    st.set_page_config(page_title="StudySearch · 学习资料检索", page_icon="📚", layout="wide")
    st.title("📚 StudySearch")
    st.write("从课程资料中找到相关原文，每条结果都有出处和页码。")
    st.caption("本地运行时，资料仅在本机进程中处理；无需账号、API 密钥或大模型服务。")
    with st.sidebar:
        st.header("资料库")
        mode = st.radio("选择资料来源", ["内置示例", "上传 PDF"])
        uploads = st.file_uploader("添加课程资料（最多 10 份，每份 30 MB）", type="pdf",
                                   accept_multiple_files=True) if mode == "上传 PDF" else []
        method_label = st.radio("检索方式", ["TF-IDF 相关性排序", "关键词覆盖率"])
        top_k = st.slider("返回结果数", 1, 10, 5)
        st.caption("页码为 PDF 文件物理页码，从 1 开始，可能不同于书中印刷页码。")
    files = [(p.name, p.read_bytes()) for p in sorted((ROOT / "samples").glob("*.pdf"))] if mode == "内置示例" else [(f.name, f.getvalue()) for f in uploads]
    if not files:
        st.info("请上传可选中文字的 PDF，或者在左侧选择内置示例。")
        return
    if len(files) > 10 or sum(len(b) for _, b in files) > 100 * 1024 * 1024:
        st.error("一次最多 10 份资料，总大小不超过 100 MB。")
        return
    signature = hashlib.sha256(b"".join(n.encode() + hashlib.sha256(b).digest() for n, b in files)).hexdigest()
    if st.session_state.get("signature") != signature:
        chunks, notices, documents = [], [], {}
        with st.spinner("正在读取资料并建立索引…"):
            for name, data in files:
                doc_id = hashlib.sha256(data).hexdigest()[:16]
                if doc_id in documents:
                    notices.append(f"{name}：与已添加资料内容相同，已去重。")
                    continue
                try:
                    parts, warnings = extract_pdf(name, data)
                    notices.extend(warnings)
                    chunks.extend(parts)
                    if parts:
                        documents[doc_id] = (name, data)
                except ValueError as exc:
                    notices.append(f"{name}：{exc}")
            try:
                index = SearchIndex(chunks)
            except ValueError as exc:
                index = None
                notices.append(str(exc))
        st.session_state.update(signature=signature, index=index, notices=notices, documents=documents)
    for notice in st.session_state.notices:
        st.warning(notice)
    index = st.session_state.index
    documents = st.session_state.documents
    if index is None:
        return
    a, b, c = st.columns(3)
    a.metric("资料数量", len(documents))
    b.metric("含文字的页数", len({(c.document_id, c.page) for c in index.chunks}))
    c.metric("可检索段落", len(index.chunks))
    selected = st.multiselect("检索范围", list(documents), default=list(documents),
                              format_func=lambda d: f"{documents[d][0]} · {d[:6]}")
    query = st.text_input("你想找什么？", placeholder="例如：什么是矩阵的秩？", max_chars=300)
    st.caption("示例：如何判断过拟合？ / 为什么特征需要标准化？ / 梯度下降怎样更新参数？")
    if not query.strip():
        return
    if not selected:
        st.info("请至少选择一份资料。")
        return
    started = time.perf_counter()
    results = index.search(query, "tfidf" if method_label.startswith("TF") else "keyword", top_k, set(selected))
    elapsed = (time.perf_counter() - started) * 1000
    st.caption(f"找到 {len(results)} 条相关段落 · 查询耗时 {elapsed:.1f} ms（不含建索引和页面渲染）")
    if not results:
        st.info("没有找到共同词语。尝试使用教材中的术语，或检查资料是否包含相关内容。")
        return
    st.caption("相关性分数不是答案正确率；本工具返回原文，不生成答案，也不保证问题一定被资料覆盖。")
    for rank, result in enumerate(results, 1):
        with st.container(border=True):
            st.subheader(f"{rank}. {result['source']} · 第 {result['page']} 页")
            st.caption(f"相关性 {result['score']:.3f} · 段落 {result['chunk_id']}")
            st.markdown('<div style="white-space:pre-wrap;line-height:1.9">' + highlighted(result["text"], query) + '</div>', unsafe_allow_html=True)
            if st.checkbox("查看原始页面与上下文", key=f"preview-{signature}-{result['chunk_id']}"):
                st.image(page_preview(documents[result["document_id"]][1], result["page"]))
    export = {"query": query, "method": method_label, "results": results}
    st.download_button("下载检索结果 JSON", json.dumps(export, ensure_ascii=False, indent=2),
                       "studysearch-results.json", "application/json")


if __name__ == "__main__":
    main()
