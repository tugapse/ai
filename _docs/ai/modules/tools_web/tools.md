## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| Web tools | /ai/modules/tools_web/tools.md |

This component provides two core functionalities for external information retrieval: `web_search` and `web_read`. It allows the system to query external search engines (specifically DuckDuckGo) to find relevant web links based on a query, and subsequently download and extract clean, readable text content from a specified URL.

Architecturally, this module acts as a service layer responsible for interfacing with the external web. It abstracts away the complexities of HTTP requests, HTML parsing, and text extraction, providing structured data (search results or clean text) to higher-level agents or controllers, while deferring complex interactions requiring browser automation to specialized tools like [playwright](/ai/modules/tools_web/tools.md) (as referenced in `web_search` docstring).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `web_search` | Function | Searches the web using DuckDuckGo to retrieve titles, URLs, and short snippets for a given query. Supports specifying a maximum number of results and a region. |
| `web_read` | Function | Downloads a specified URL, extracts its readable text content, and returns the title, URL, and content, optionally truncating the output based on `max_chars`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** `web_search` constructs and sends a POST request to the DuckDuckGo search endpoint, parsing the raw HTML response using `_DuckDuckGoParser` to extract structured results. `web_read` fetches the URL content via GET request, checks the content type, and if it is HTML, uses `_TextExtractor` to strip markup and return a tidy text summary.
- **Side Effects:** Interacts heavily with the network via `requests` to perform HTTP GET and POST operations to external services.
- **Error Handling:** Both functions include extensive try/except blocks. `web_search` specifically checks for HTTP status codes and content indicating bot blocking (e.g., "anomaly" or "captcha" in the response text). `web_read` checks for HTTP status codes $\ge 400$ and handles unsupported content types.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `requests`, `html`, `urllib.parse`
- **Internal:** None (All internal dependencies are part of the current module or standard library imports).