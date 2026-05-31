# MCP Research Benchmark: Proposal-Aligned Evaluation

**Date:** 2026-05-31
**Scope:** 3 queries × 3 MCPs = 9 runs (subset of proposed 10×3=30)
**Year filter:** 2018–2026 (applied where supported)

---

## 1. Tool Surface Comparison

| MCP | Tool Count | Est. Total Chars | Est. Tokens (÷4) |
|---|---|---|---|
| **academix** | 8 | ~1,700 | ~425 |
| **paper-search** | 57 | ~11,400 | ~2,850 |
| **research** | 8 | ~4,000 | ~1,000 |
| **Total** | **73** | **~17,100** | **~4,275** |

### academix (8 tools)
`academic_cache_stats`, `academic_get_bibtex`, `academic_get_citation_network`, `academic_get_citations`, `academic_get_paper_details`, `academic_get_related_papers`, `academic_search_author`, `academic_search_papers`

### paper-search (57 tools)
57 search/download/read tools covering arXiv, bioRxiv, medRxiv, IACR, Semantic Scholar, CrossRef, PubMed/PMC, CORE, EuropePMC, DBLP, OpenAIRE, CiteSeerX, DOAJ, BASE, Zenodo, HAL, SSRN, Unpaywall, Google Scholar, Sci-Hub, plus unified `search_papers` and `download_with_fallback`.

### research (8 tools)
`search_literature`, `paper_lookup`, `read_paper`, `extract_sections`, `compare_papers`, `walk_citations`, `author_literature`, `export_references`

---

## 2. Full Results Table

### Query 1: *"LLM feedback accuracy category-level writing"*

| MCP | Papers Ret. | With Abstracts | Relevant | Top 3 Relevant Papers |
|---|---|---|---|---|
| **academix** | 10 | 10 | 0 (1 marginal) | — |
| **paper-search** | 10 | 7 | 3 | Zhang 2025 (*LLM Feedback vs AWE*), Glüsing 2025 (*LLM feedback academic writing*), Bitchener 2010 (*Raising linguistic accuracy with WCF*) |
| **research** | 10 | 10 | 5 | Zhang 2025 (*LLM Feedback vs AWE*), Rashkin 2025 (*Help Me Write a Story*), Liu 2025 (*LLM vs human feedback quality*) |

### Query 2: *"peer teacher feedback comparison accuracy second language writing"*

| MCP | Papers Ret. | With Abstracts | Relevant | Top 3 Relevant Papers |
|---|---|---|---|---|
| **academix** | 10 | 10 | 1 | Wu 2023 (*Peer feedback Chinese medical students writing*) |
| **paper-search** | 15 | ~10 | 8 | Yanwar 2026 (*Unidentified vs Identified Peer+Teacher*), Pojslová 2024 (*Peer vs teacher feedback role*), Yang 2006 (*Comparative peer/teacher EFL*) |
| **research** | 10 | 10 | 3 | Yanwar 2026 (*Peer+Teacher feedback*), Wu 2023, Ma 2023 (*Teacher-supported peer feedback literacy*) |

### Query 4: *"automated feedback classifier DeBERTa educational text"*

| MCP | Papers Ret. | With Abstracts | Relevant | Top 3 Relevant Papers |
|---|---|---|---|---|
| **academix** | 10 | 10 | 1 | Rodrigues 2024 (*GPT-4 automated short answer assessment*) |
| **paper-search** | 10 | 5 | 3 | Rahmat 2025 (*DeBERTa V3 essay evaluation*), Dux Speltz (*Automated fluency feedback*), Gegenheimer 2024 (*Automated text classification feedback*) |
| **research** | 10 | 10 | 7 | Jansen 2025 (*Feedback from GenAI revision engagement*), Ajitha 2025 (*NLP automated feedback generation BERT+GRU*), Gupta 2025 (*Explainable AI student feedback*) |

---

## 3. MCP Winner per Query

| Query | Winner | Relevant Count | Runner-Up | Relevant Count |
|---|---|---|---|---|
| Q1: LLM feedback accuracy writing | **research** | 5 | paper-search | 3 |
| Q2: Peer/teacher feedback L2 writing | **paper-search** | 8 | research | 3 |
| Q4: DeBERTa feedback classifier | **research** | 7 | paper-search | 3 |

**research wins 2/3 queries; paper-search wins 1/3; academix wins 0/3.**

---

## 4. Overall MCP Ranking

| Rank | MCP | Avg Relevant/Query | Total Relevant | Total Papers |
|---|---|---|---|---|
| **1** | **research** | **5.0** | 15 | 30 |
| **2** | **paper-search** | **4.7** | 14 | 35 |
| **3** | **academix** | **0.7** | 2 | 30 |

---

## 5. Efficiency Comparison (Relevant Papers per k-Tokens)

| MCP | Avg Relevant/Query | Tool Est. k-Tokens | Rel/k-Token |
|---|---|---|---|
| **research** | 5.0 | 1.0 | **5.00** |
| **paper-search** | 4.7 | 2.85 | 1.65 |
| **academix** | 0.7 | 0.425 | 1.65 |

**research is 3× more efficient than the other two MCPs** in relevant papers per k-token of tool surface.

---

## 6. Key Findings

1. **research_search_literature** is the strongest single endpoint: it aggregates arXiv, Semantic Scholar, OpenAlex, CrossRef, PubMed, and Unpaywall with auto-deduplication and citation walking, returning the most relevant results per query.

2. **paper-search** is a close second in relevance (4.7 vs 5.0 avg) but carries a **7× larger tool surface** (57 vs 8 tools), making it expensive in prompt context.

3. **academix** (OpenAlex-only) is the weakest on domain-specific educational queries — it returns many high-citation general papers but misses the niche area-specific literature.

4. **Recommendation:** Prefer `research_search_literature` as the primary search endpoint. Use `paper-search` only when specific source-native download/read is needed. Use `academix` for citation-chaining and bibliometric queries.

---

## 7. MCP-Specific Observations

### academix
- Fastest response time
- OpenAlex-only: broad coverage but domain shallow
- High abstract coverage (100%)
- Poor precision on narrow educational NLP queries

### paper-search
- Richest tool ecosystem (57 tools)
- Good multi-source aggregation via `search_papers`
- Many papers from CrossRef lack abstracts (~30-50% empty)
- `search_papers` deduplicates well across sources

### research
- Best precision-recall balance for domain queries
- Auto-citation-walking adds value but causes timeouts (~30s limit)
- `expand_queries` (auto acronym expansion) is a nice feature
- Returns OA status — useful for literature review pipelines
- Smaller tool surface = more prompt budget for actual work
