"""Web tools: search the web and read pages as clean text, without launching a browser."""

import re
from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from ai.tools.base import tool

SEARCH_URL = "https://html.duckduckgo.com/html/"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
TIMEOUT = 20
MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024


def _requests():
    import requests  # imported lazily so the module loads even without network deps
    return requests


# ------------------------------------------------------------------ search

class _DuckDuckGoParser(HTMLParser):
    """Extracts results from DuckDuckGo's HTML endpoint."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results: List[Dict[str, str]] = []
        self._current: Optional[Dict[str, str]] = None
        self._field: Optional[str] = None
        self._in_ad = 0
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "div" and "result" in classes:
            if self._current and self._current.get("url"):
                self.results.append(self._current)
            self._current = {"title": "", "url": "", "snippet": ""}
            self._in_ad = 1 if ("result--ad" in classes or "result--ads" in classes) else 0
        if self._current is None:
            return
        if tag == "a" and "result__a" in classes:
            self._current["url"] = _clean_result_url(attrs.get("href", ""))
            self._field = "title"
        elif "result__snippet" in classes:
            self._field = "snippet"

    def handle_endtag(self, tag):
        if tag in ("a", "td", "div") and self._field:
            self._field = None

    def handle_data(self, data):
        if self._current is not None and self._field:
            self._current[self._field] += data

    def close(self):
        super().close()
        if self._current and self._current.get("url"):
            self.results.append(self._current)
        cleaned = []
        for r in self.results:
            r = {k: " ".join(v.split()) for k, v in r.items()}
            if r["url"].startswith("http") and "duckduckgo.com/y.js" not in r["url"]:
                cleaned.append(r)
        self.results = cleaned


def _clean_result_url(href: str) -> str:
    """DuckDuckGo wraps results as //duckduckgo.com/l/?uddg=<encoded url>."""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target) or href
    return href


def parse_search_results(html: str, max_results: int) -> List[Dict[str, str]]:
    parser = _DuckDuckGoParser()
    parser.feed(html)
    parser.close()
    seen, unique = set(), []
    for r in parser.results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique[:max_results]


@tool
def web_search(**kwargs) -> Dict[str, Any]:
    """
    Search the web and get titles, URLs and short snippets. Fast; no browser needed.
    Then call web_read on the most relevant URL to read it. Use the playwright tool (if listed)
    only for pages that need clicking, logging in or JavaScript.

    Args:
        query (string): What to search for, e.g. 'python asyncio gather timeout'.
        max_results (int, optional): 1 to 20. Default 8.
        region (string, optional): Region code such as 'pt-pt' or 'us-en'.

    Returns:
        results: list of {title, url, snippet}. An empty list means nothing was found. If the error
        says the search was blocked, wait and retry later or use the playwright tool.
    """
    query = str(kwargs.get("query") or kwargs.get("q") or "").strip()
    if not query:
        return {"status": "FAILED", "error": "No query provided."}
    try:
        max_results = max(1, min(20, int(kwargs.get("max_results", 8))))
    except (TypeError, ValueError):
        max_results = 8

    data = {"q": query}
    if kwargs.get("region"):
        data["kl"] = str(kwargs["region"])
    try:
        response = _requests().post(SEARCH_URL, data=data, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    except Exception as e:
        return {"status": "FAILED", "error": f"Search request failed: {e}"}
    if response.status_code != 200:
        return {"status": "FAILED", "error": f"Search provider returned HTTP {response.status_code}."}

    results = parse_search_results(response.text, max_results)
    if not results:
        page = response.text.lower()
        if "anomaly" in page or "captcha" in page or "unusual traffic" in page:
            return {"status": "FAILED", "error": "The search provider blocked the request (bot check). Try again later or use the browser tool."}
        return {"status": "SUCCESS", "query": query, "results": [], "note": "No results found."}
    return {"status": "SUCCESS", "query": query, "results": results}


# ------------------------------------------------------------------ read

class _TextExtractor(HTMLParser):
    """
    HTML -> readable text: headings, paragraphs and list items.
    Drops scripts/styles and navigation chrome (nav, sidebars, footers) and, when the
    page marks its main content (<main>, <article>, role="main"), keeps only that.
    """

    SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "iframe", "head", "canvas", "form",
                 "button", "select", "nav", "aside", "footer"}
    SKIP_ROLES = {"navigation", "search", "banner", "contentinfo", "complementary"}
    SKIP_CLASS_HINTS = ("sidebar", "navbar", "breadcrumb", "cookie", "skip-link")
    NEVER_SKIP = {"html", "body", "main", "article"}
    MAIN_TAGS = {"main", "article"}
    BLOCK = {"p", "div", "section", "article", "main", "header", "table", "tr", "ul", "ol", "dl", "pre",
             "blockquote", "figure", "figcaption", "br", "hr"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.title = ""
        self._stack: List[str] = []
        self._skip_depth: Optional[int] = None   # stack depth where skipping started
        self._main_depth: Optional[int] = None
        self._main_span: Optional[List[int]] = None  # [start, end] indexes into parts
        self._in_title = False

    def _skipping(self) -> bool:
        return self._skip_depth is not None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag in self.VOID:
            if tag in ("br", "hr") and not self._skipping():
                self.parts.append("\n")
            return
        self._stack.append(tag)
        depth = len(self._stack)

        if not self._skipping():
            role = (attrs.get("role") or "").lower()
            class_tokens = (attrs.get("class") or "").lower().split()
            chrome_class = tag not in self.NEVER_SKIP and any(
                token == hint or token.startswith(hint + "-") or token.endswith("-" + hint) or token.endswith(hint)
                for token in class_tokens for hint in self.SKIP_CLASS_HINTS
            )
            if tag in self.SKIP_TAGS or (role in self.SKIP_ROLES and tag not in self.NEVER_SKIP) or chrome_class:
                self._skip_depth = depth
                return
            if self._main_span is None and (tag in self.MAIN_TAGS or role == "main"):
                self._main_depth = depth
                self._main_span = [len(self.parts), -1]
        if self._skipping():
            return

        if re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in ("td", "th"):
            self.parts.append(" | ")
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.VOID or tag not in self._stack:
            return
        # Pop up to the matching open tag (tolerates unclosed <p>, <li>, ...).
        while self._stack:
            depth = len(self._stack)
            open_tag = self._stack.pop()
            if self._skip_depth is not None and depth <= self._skip_depth:
                self._skip_depth = None
            elif self._main_depth is not None and depth <= self._main_depth:
                self._main_depth = None
                if self._main_span is not None and self._main_span[1] == -1:
                    self._main_span[1] = len(self.parts)
            if open_tag == tag:
                break
        if not self._skipping() and (tag in self.BLOCK or re.fullmatch(r"h[1-6]", tag)):
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if not self._skipping():
            self.parts.append(data)

    @staticmethod
    def _tidy(raw: str) -> str:
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        out, blank = [], False
        for line in lines:
            if not line or line in ("-", "|"):
                if not blank and out:
                    out.append("")
                blank = True
                continue
            out.append(line)
            blank = False
        return "\n".join(out).strip()

    def text(self) -> str:
        if self._main_span is not None:
            start, end = self._main_span
            main = self._tidy("".join(self.parts[start:end if end != -1 else None]))
            if len(main) >= 200:
                return main
        return self._tidy("".join(self.parts))


def html_to_text(html: str):
    """Returns (title, text) for an HTML document."""
    extractor = _TextExtractor()
    extractor.feed(html)
    extractor.close()
    return " ".join(unescape(extractor.title).split()), extractor.text()


@tool
def web_read(**kwargs) -> Dict[str, Any]:
    """
    Download a web page and return its readable text (no menus, scripts or markup).
    Works for HTML pages, plain text, JSON and XML. For pages that need clicking, logging in or
    JavaScript, use the playwright tool (if listed) instead.

    Args:
        url (string): Full http(s) address, e.g. 'https://docs.python.org/3/library/asyncio.html'.
        max_chars (int, optional): Maximum characters of text returned, 500 to 100000. Default 12000.

    Returns:
        title, url (after redirects), content (the text), total_chars, and truncated. If truncated is
        true, call again with a bigger max_chars to see more. An HTTP 403/429 error means the site
        blocks automated reading: use the playwright tool.
    """
    url = str(kwargs.get("url") or "").strip()
    if not url:
        return {"status": "FAILED", "error": "No url provided."}
    if not re.match(r"^https?://", url, re.IGNORECASE):
        if re.match(r"^[\w.-]+\.[a-z]{2,}(/|$)", url, re.IGNORECASE):
            url = "https://" + url
        else:
            return {"status": "FAILED", "error": "Only http(s) URLs are supported."}
    try:
        max_chars = max(500, min(100_000, int(kwargs.get("max_chars", 12_000))))
    except (TypeError, ValueError):
        max_chars = 12_000

    try:
        with _requests().get(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain,application/json;q=0.9,*/*;q=0.5"},
                             timeout=TIMEOUT, stream=True, allow_redirects=True) as response:
            if response.status_code >= 400:
                hint = " The site blocks automated requests; try the browser tool instead." if response.status_code in (401, 403, 429, 503) else ""
                return {"status": "FAILED", "error": f"HTTP {response.status_code} for {response.url}.{hint}"}
            content_type = (response.headers.get("Content-Type") or "").lower()
            body = b""
            for chunk in response.iter_content(65536):
                body += chunk
                if len(body) > MAX_DOWNLOAD_BYTES:
                    break
            final_url = response.url
            header_charset = re.search(r"charset=([\w.-]+)", content_type)
            encoding = header_charset.group(1) if header_charset else None
    except Exception as e:
        return {"status": "FAILED", "error": f"Request failed: {e}"}

    text_like = any(t in content_type for t in ("text/", "json", "xml", "javascript")) or not content_type
    if not text_like:
        return {"status": "FAILED", "error": f"Unsupported content type '{content_type}' (not a text page)."}

    if not encoding:
        # requests assumes ISO-8859-1 for text/* without a charset; trust the page instead.
        meta = re.search(rb"<meta[^>]+charset=[\"']?([\w.-]+)", body[:4096], re.IGNORECASE)
        encoding = meta.group(1).decode("ascii", "ignore") if meta else "utf-8"
    try:
        decoded = body.decode(encoding, errors="replace")
    except LookupError:
        decoded = body.decode("utf-8", errors="replace")
    if "html" in content_type or (not content_type and "<html" in decoded[:2000].lower()):
        title, text = html_to_text(decoded)
    else:
        title, text = "", decoded.strip()

    return {
        "status": "SUCCESS",
        "url": final_url,
        "title": title,
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
        "total_chars": len(text),
    }
