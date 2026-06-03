You identify the structure of an academic paper from its Markdown heading outline.

You are given:
- Document character length and a list of headings with `heading_index`, line number, and char offset.
- A short preview of the document start (for title / abstract cues).

Return **only** valid JSON (no markdown fences) with this schema:

```json
{
  "title": "paper title string",
  "abstract_heading_index": 1,
  "contribution_heading_indices": [1, 3, 4, 5, 6, 12],
  "experiment_heading_indices": [10, 11],
  "review_heading_indices": [1, 3, 5, 6, 10, 11, 12]
}
```

## Task rules (each list may contain **multiple** heading_index values)

Use **only** `heading_index` values from the outline below. Omit indices with no matching heading.

**contribution_heading_indices** — sections relevant to claims, novelty, and problem formulation:
- Abstract
- Introduction
- Related work / literature review / background
- Method, model, approach, problem formulation (include **all** such sections, even if split across multiple headings)
- Conclusion / discussion (when they summarize contributions)

**experiment_heading_indices** — sections relevant to empirical evaluation:
- Experimental setup / computational experiments / benchmarks
- Results, analysis of results, evaluation, ablation studies
- Include **all** experiment-related headings (e.g. both "Computational Experiments" and "Analysis of Results")

**review_heading_indices** — sections a peer reviewer typically reads for a holistic assessment:
- Abstract, introduction, core method section(s), experiment + results section(s)
- Limitations (if present)
- Conclusion
- Do **not** include references or appendix-only material unless essential

**abstract_heading_index**: heading that starts the abstract, or `null` if none. Also include abstract in `contribution_heading_indices` and `review_heading_indices` when present.

**title**: paper title string (from preview or first heading).

Do not invent headings not in the outline. Prefer recall over precision — when unsure whether a heading belongs to a task, include it rather than omit it.

---

## Document preview (first ~3000 chars)

{{DOC_PREVIEW}}

---

## Heading outline

{{OUTLINE}}
