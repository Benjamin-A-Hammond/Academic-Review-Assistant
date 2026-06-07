You identify the **bibliography / references** section of an academic paper from its Markdown heading outline.

The section title is often **not** exactly "References". Common variants include:
- References, Bibliography, Works Cited
- 参考文献, 引用文献, 文献
- Referencias, Références, Literatur
- Or an unnumbered final section that is clearly a reference list

You are given:
- Document character length and a list of headings with `heading_index`, line number, and char offset.
- A short preview of the document **start** (title / abstract cues).
- A short preview of the document **end** (where bibliography usually appears).

Return **only** valid JSON (no markdown fences):

```json
{
  "reference_heading_index": 12,
  "detected_title": "Bibliography"
}
```

## Rules

- `reference_heading_index`: the `heading_index` of the **single** heading that starts the main bibliography section, or `null` if there is no clear bibliography heading in the outline.
- `detected_title`: the exact heading text you chose (for logging), or `null` if none.
- Use **only** `heading_index` values from the outline. Do not invent headings.
- Pick **one** section: the primary reference list, not "Related Work" or inline citations in the introduction.
- If the paper ends with a numbered reference list **without** any markdown heading, return `null` (this step only splits headed sections).
- The slice may extend to the next heading or document end; trailing tables/appendix are removed in a later clean step.

---

## Document start preview (first ~3000 chars)

{{DOC_PREVIEW}}

---

## Document end preview (last ~3000 chars)

{{DOC_TAIL_PREVIEW}}

---

## Heading outline

{{OUTLINE}}
