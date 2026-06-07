You trim an extracted **bibliography slice** so it contains **only** reference list entries.

The slice may incorrectly include trailing or leading material, for example:
- Tables, figures, or captions (e.g. "Table 3 shows...")
- Appendix, supplementary material
- Author contributions, declarations, funding, acknowledgments
- Page headers/footers, "Continued on next page"

**Do not rewrite or summarize** reference entries. Only identify where the bibliography **starts** and **ends** in the given text.

Return **only** valid JSON (no markdown fences):

```json
{
  "keep_start": 0,
  "keep_end": 2847,
  "end_exclusive_snippet": "Table 3 shows, for each instance",
  "start_after_snippet": null,
  "removed_summary": "Dropped benchmark table after bibliography"
}
```

## Field rules

- `keep_start` / `keep_end`: **0-based character indices** into the slice below (`keep_end` is **exclusive**). The bibliography body is `text[keep_start:keep_end]`.
- `end_exclusive_snippet`: copy **verbatim** (40–120 chars) the first characters of content **after** the last reference entry — the part to **remove**. Use `null` if nothing should be trimmed at the end.
- `start_after_snippet`: verbatim snippet of the **last line of leading junk** immediately before the first real reference entry, or `null` if the slice already starts at the bibliography heading/first entry.
- `removed_summary`: one short English sentence describing what you excluded (for logs).

Include the `# References` (or equivalent) heading in the kept range when it is present.

If the entire slice is bibliography, return `keep_start: 0`, `keep_end: {{SLICE_LENGTH}}`, and null snippets.

---

## Extracted slice (length {{SLICE_LENGTH}} characters)

{{REFERENCE_SLICE}}
