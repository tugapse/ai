# Knowledge viewer

`docs/` is a small static web page for browsing the knowledge JARVIS generated for this repo
(`_knowledge/` and `_docs/`): components, their symbols and dependencies, as a graph. The data
comes from `docs/data.json`, which browsers won't load from a `file://` page, so serve the folder:

```bash
python -m http.server -d docs 8000      # then open http://localhost:8000
```

This is **not** the project documentation. For that, see [`guide/`](../guide/index.md).
