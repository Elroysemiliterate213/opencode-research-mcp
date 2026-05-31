# Proposal-Aligned MCP Benchmark — 10 Queries × 3 MCPs

## Instructions

Run every query through all 3 MCPs. Record metrics per query. Save results to `BENCHMARK_PROPOSAL.md` in this same folder.

---

## Setup

- **Year filter:** 2018–2026 (where supported)
- **MCP 1:** `academic_search_papers` (academix) — `response_format="json"`, `limit=10`
- **MCP 2:** `search_papers` (paper-search) — `sources="arxiv,semantic,openalex,crossref,pubmed"`, `max_results_per_source=5`
- **MCP 3:** `research_search_literature` (bundled research) — `max_results=10`, `year_from=2018`

---

## Queries

| # | Query | Proposal link |
|---|---|---|
| 1 | `LLM feedback accuracy category-level writing` | Core gap claim — validates no category-level accuracy data exists |
| 2 | `peer teacher feedback comparison accuracy second language writing` | Three-way design — baseline comparisons for LLM |
| 3 | `AI feedback uptake revision quality meta-analysis` | Positions against 6 existing meta-analyses (I² = 81–95%) |
| 4 | `automated feedback classifier DeBERTa educational text` | Study 2 architecture — DeBERTa-v3 viability |
| 5 | `feedback literacy intervention training evaluative judgement` | Study 3 intervention — training precedents |
| 6 | `LLM self-assessment bias self-enhancement` | Dual-annotation design — can LLMs rate own feedback? |
| 7 | `spaced micro-learning AI feedback evaluation` | Training format — 3 × 10–15 min spaced sessions |
| 8 | `metacognitive laziness AI student learning` | Problem statement — Fan et al. (2025) lineage |
| 9 | `uptake taxonomy feedback L2 writing revision decisions` | 6-category uptake taxonomy — precedents and gaps |
| 10 | `hybrid AI human feedback writing accuracy` | Hybrid condition — AI-augmented teacher feedback |

---

## Per-Query Metrics (record for each MCP × query)

For every combination, record:

1. **Papers returned** — count
2. **Papers with abstracts** — count
3. **Relevant to query** — count (papers directly addressing the query topic)
4. **Relevant & within 2018–2026** — count
5. **Top 3 papers** — title, year, authors (most relevant only)
6. **New papers not in proposal reference list** — flag any that aren't already cited in `proposal_for_hu_final.md`

---

## Summary Table (build after all 30 runs)

| Query | MCP | Returned | With Abstracts | Relevant | Relevant + 2018–2026 | New Papers |
|---|---|---|---|---|---|---|
| Q1 | Academix | | | | | |
| Q1 | Paper-Search | | | | | |
| Q1 | Research | | | | | |
| Q2 | Academix | | | | | |
| Q2 | Paper-Search | | | | | |
| Q2 | Research | | | | | |
| ... | ... | | | | | |

---

## Deliverables

After all runs, produce:

1. **Full results table** (30 rows: 10 queries × 3 MCPs)
2. **MCP winner per query** — which MCP found the most relevant 2018+ papers
3. **Overall MCP ranking** — averaged across all 10 queries
4. **New paper list** — all papers found that are NOT in `proposal_for_hu_final.md` references, with title, year, DOI, and why it's relevant
5. **Coverage gap analysis** — which of the 10 queries returned zero or near-zero relevant results (identifies blind spots in available literature)
6. **Save to:** `C:\Users\mwp5a\Desktop\research-mcp\BENCHMARK_PROPOSAL.md`

---

## Notes

- This benchmark is proposal-specific: every query maps to a concrete design decision or gap claim in `proposal_for_hu_final.md`
- "New papers" means anything not already cited in the proposal's reference list (lines 321–518)
- If an MCP doesn't support year filtering, note it but still record results
- Run all 3 MCPs per query before moving to the next query (parallel MCP, sequential queries)
