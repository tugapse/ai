"""
Markdown documentation loader: splits a document into heading sections (and word chunks)
for semantic search, and extracts the metadata that links it to code components.

Works with any Markdown. Docs produced by the ``code/create-code-documentation`` task
also give the component's source file (Overview table) and repo-absolute links.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from ai.modules.knowledge.schema import path_key

SECTION_WORDS = 350
SECTION_OVERLAP = 50

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_LINK_RE = re.compile(r"\[[^\]]*\]\((/[^)\s#]+)(?:#[^)]*)?\)")
_MD_LINK_TEXT_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")


@dataclass
class DocChunk:
    heading: str
    level: int
    text: str
    chunk_index: int = 0


@dataclass
class ParsedDoc:
    title: str
    chunks: List[DocChunk] = field(default_factory=list)
    links: List[str] = field(default_factory=list)          # path keys of internal links
    source_file_key: Optional[str] = None                   # from the Overview table

    @property
    def headings(self) -> List[str]:
        seen, out = set(), []
        for c in self.chunks:
            if c.heading not in seen:
                seen.add(c.heading)
                out.append(c.heading)
        return out


def chunk_text(text: str, chunk_size: int = SECTION_WORDS, overlap: int = SECTION_OVERLAP) -> List[str]:
    """
    Splits text into overlapping chunks based on word count.

    Args:
        text: The full text content to be chunked.
        chunk_size: The target number of words per chunk.
        overlap: The number of words to overlap between consecutive chunks.

    Returns:
        A list of text chunks (empty for blank text).
    """
    words = text.split()
    if not words:
        return []
    if chunk_size <= overlap or len(words) <= chunk_size:
        return [" ".join(words)]
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        if i + chunk_size >= len(words):
            break
        i += chunk_size - overlap
    return chunks


def _strip_link_syntax(cell: str) -> str:
    m = _MD_LINK_TEXT_RE.search(cell)
    if m:
        target = m.group(2).strip()
        return target if target and not target.startswith("http") else m.group(1)
    return cell.strip().strip("*` ")


def _overview_source(lines: List[str]) -> Optional[str]:
    """Second cell of the first data row of the table under an 'Overview' heading."""
    in_overview = False
    for line in lines:
        h = _HEADING_RE.match(line)
        if h:
            if in_overview:
                return None
            in_overview = "overview" in h.group(2).lower()
            continue
        if not in_overview or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set(":- ") or cells[0].lower() in ("component", "entity"):
            continue
        key = path_key(_strip_link_syntax(cells[1]))
        return key or None
    return None


def parse_markdown(text: str, doc_key: str = "") -> ParsedDoc:
    """
    Parses a Markdown document into heading sections.

    Args:
        text: The Markdown source.
        doc_key: The document's own path key (excluded from links).

    Returns:
        ParsedDoc with chunks (sections split into ~SECTION_WORDS-word pieces), internal links and
        the source file key from an Overview table, when present.
    """
    lines = text.splitlines()
    sections: List[tuple] = []  # (heading, level, [lines])
    title = ""
    current_heading, current_level, buf = "", 0, []
    in_fence = False

    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            buf.append(line)
            continue
        h = None if in_fence else _HEADING_RE.match(line)
        if h:
            if buf and any(b.strip() for b in buf):
                sections.append((current_heading, current_level, buf))
            current_level = len(h.group(1))
            current_heading = h.group(2).strip()
            if current_level == 1 and not title:
                title = current_heading
            buf = []
        else:
            buf.append(line)
    if buf and any(b.strip() for b in buf):
        sections.append((current_heading, current_level, buf))

    if not title:
        title = doc_key.rsplit("/", 1)[-1] if doc_key else (sections[0][0] if sections else "")

    chunks: List[DocChunk] = []
    for heading, level, body in sections:
        body_text = "\n".join(body).strip()
        for i, piece in enumerate(chunk_text(body_text)):
            chunks.append(DocChunk(heading=heading or title or "Introduction", level=level, text=piece, chunk_index=i))

    links: List[str] = []
    for target in _LINK_RE.findall(text):
        key = path_key(target)
        if key and key != doc_key and key not in links:
            links.append(key)

    return ParsedDoc(title=title, chunks=chunks, links=links, source_file_key=_overview_source(lines))
