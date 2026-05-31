# MCP Benchmark: Academic Search for Writing/Feedback Research

**Date:** 2026-05-31 | **Setup:** 10 queries × 3 MCPs = 30 runs | **No year filters**

## MCP Configurations

| MCP | Tool | Key Params |
|-----|------|-----------|
| **MCP 1** | `academix_academic_search_papers` | `response_format="json"`, `limit=15` |
| **MCP 2** | `paper-search_search_papers` | `max_results_per_source=5`, `sources="all"` |
| **MCP 3** | `research_search_literature` | `max_results=15`, no year_from/to, auto-cite-walk=on |

---

## Results Table (30 Rows)

| # | Query | MCP | Returned | w/ Abstracts | Relevant | Top 1 Paper |
|---|-------|-----|----------|-------------|---------|------------|
| 1 | LLM feedback accuracy category-level writing | **MCP1** academix | 15 | 15 | 5 | AI-Driven Intelligent Feedback System for Enhancing Self-Assessment Accuracy |
| 1 | LLM feedback accuracy category-level writing | **MCP2** paper-search | 50 | 40 | 6 | Help Me Write a Story: Evaluating LLMs' Ability to Generate Writing Feedback |
| 1 | LLM feedback accuracy category-level writing | **MCP3** bundled | 15 | 15 | 8 | When and How Does LLM-Generated Feedback Surpass Traditional AWE? |
| 2 | peer teacher feedback comparison accuracy L2 writing | **MCP1** academix | 15 | 15 | 5 | Peer feedback and Chinese medical students' English academic writing development |
| 2 | peer teacher feedback comparison accuracy L2 writing | **MCP2** paper-search | 50 | 38 | 8 | Exposía: Teaching and Assessment of Academic Writing Skills and Peer Feedback |
| 2 | peer teacher feedback comparison accuracy L2 writing | **MCP3** bundled | 15 | 15 | 10 | Understanding Teacher Revisions of LLM-Generated Feedback |
| 3 | AI feedback uptake revision quality meta-analysis | **MCP1** academix | 15 | 14 | 4 | European Guidelines on cardiovascular disease prevention |
| 3 | AI feedback uptake revision quality meta-analysis | **MCP2** paper-search | 38 | 34 | 12 | Foundations of GenIR |
| 3 | AI feedback uptake revision quality meta-analysis | **MCP3** bundled | 15 | 15 | 9 | AI prediction leads people to forgo guaranteed rewards |
| 4 | automated feedback classifier DeBERTa educational text | **MCP1** academix | 15 | 15 | 5 | Large language models (LLMs): survey, technical frameworks, and future challenges |
| 4 | automated feedback classifier DeBERTa educational text | **MCP2** paper-search | 41 | 31 | 19 | amc: The Automated Mission Classifier for Telescope Bibliographies |
| 4 | automated feedback classifier DeBERTa educational text | **MCP3** bundled | 15 | 15 | 10 | How Do L2 Learners Engage with Human and Automated Feedback? |
| 5 | feedback literacy intervention training evaluative judgement | **MCP1** academix | 15 | 12 | 5 | PRISMA 2020 explanation and elaboration |
| 5 | feedback literacy intervention training evaluative judgement | **MCP2** paper-search | 35 | 27 | 12 | An Experiential Approach to AI Literacy |
| 5 | feedback literacy intervention training evaluative judgement | **MCP3** bundled | 15 | 15 | 8 | An Experiential Approach to AI Literacy |
| 6 | LLM self-assessment bias self-enhancement | **MCP1** academix | 15 | 15 | 6 | Large language models encode clinical knowledge |
| 6 | LLM self-assessment bias self-enhancement | **MCP2** paper-search | 35 | 27 | 15 | Bias and Unfairness in Information Retrieval Systems |
| 6 | LLM self-assessment bias self-enhancement | **MCP3** bundled | 15 | 15 | 14 | A Survey of Large Language Models |
| 7 | spaced micro-learning AI feedback evaluation | **MCP1** academix | 15 | 12 | 2 | Diagnosing Non-Intermittent Anomalies in RL |
| 7 | spaced micro-learning AI feedback evaluation | **MCP2** paper-search | 34 | 31 | 9 | AI prediction leads people to forgo guaranteed rewards |
| 7 | spaced micro-learning AI feedback evaluation | **MCP3** bundled | 15 | 14 | 5 | AI prediction leads people to forgo guaranteed rewards |
| 8 | metacognitive laziness AI student learning | **MCP1** academix | 15 | 14 | 15 | Beware of metacognitive laziness: Effects of GenAI on learning |
| 8 | metacognitive laziness AI student learning | **MCP2** paper-search | 38 | 35 | 35 | DeBiasMe: De-biasing Human-AI Interactions with Metacognitive AIED |
| 8 | metacognitive laziness AI student learning | **MCP3** bundled | 15 | 15 | 15 | Beware of metacognitive laziness |
| 9 | uptake taxonomy feedback L2 writing revision decisions | **MCP1** academix | 15 | 14 | 12 | Effects of manipulating task complexity on self-repairs during L2 oral production |
| 9 | uptake taxonomy feedback L2 writing revision decisions | **MCP2** paper-search | 34 | 25 | 15 | A Taxonomy of Errors in English |
| 9 | uptake taxonomy feedback L2 writing revision decisions | **MCP3** bundled | 15 | 15 | 14 | Comparative Effectiveness of AI-Generated and Peer Feedback on L2 Writing |
| 10 | hybrid AI human feedback writing accuracy | **MCP1** academix | 15 | 11 | 5 | Systematic review of AI applications in higher education |
| 10 | hybrid AI human feedback writing accuracy | **MCP2** paper-search | 37 | 30 | 17 | Designing AI Systems that Augment Human Critical Thinking |
| 10 | hybrid AI human feedback writing accuracy | **MCP3** bundled | 15 | 15 | 14 | Knowledge Affordances for Hybrid Human-AI Information Seeking |

---

## MCP Winner Per Query

| Query | Winner | Reason |
|-------|--------|--------|
| 1 | **MCP3** (8 rel) | Best relevance match for LLM writing feedback |
| 2 | **MCP3** (10 rel) | Best L2/peer feedback papers |
| 3 | **MCP2** (12 rel) | Highest raw relevant count despite noise |
| 4 | **MCP2** (19 rel) | Best DeBERTa/classifier coverage (41 papers) |
| 5 | **MCP2** (12 rel) | Most feedback literacy coverage |
| 6 | **MCP3** (14 rel) vs **MCP2** (15) | Tie — MCP3 better abstracts, MCP2 more volume |
| 7 | **MCP2** (9 rel) | Sparse query; MCP2's 34 papers found more |
| 8 | **MCP2** (35 rel) | Dominant — found the exact "metacognitive laziness" paper + 34 others |
| 9 | **MCP3** (14 rel) | Best L2 revision taxonomy matches |
| 10 | **MCP3** (14 rel) vs **MCP2** (17) | Tie — MCP3 better precision, MCP2 better recall |

**Winner tally:** MCP2 wins 5 queries, MCP3 wins 4 queries, Tie on 1

---

## Overall Ranking

| Rank | MCP | Avg Returned | Avg Relevant | Avg Relevant/Query | Total Papers |
|------|-----|-------------|-------------|-------------------|-------------|
| **1** | **MCP2** (paper-search) | 39.2 | **14.8** | 0.38 rel/paper | **392** |
| **2** | **MCP3** (bundled research) | 15.0 | **10.7** | **0.71 rel/paper** | 150 |
| **3** | **MCP1** (academix) | 15.0 | **6.4** | 0.43 rel/paper | 150 |

### Key Insight
- **MCP2** returns 2.6× more total papers and 1.4× more relevant papers per query than MCP3
- **MCP3** has 1.9× better **precision** (71% relevant vs MCP2's 38%)
- **MCP1** falls between them in precision (43%) but never wins a query outright

---

## Token Efficiency (Est.)

Estimates based on observed output sizes:

| MCP | Est. Tokens/Query | Est. Total Tokens | Relevant Found | Rel/1K Tokens | Notes |
|-----|-------------------|-------------------|---------------|---------------|-------|
| **MCP1** academix | ~5K | ~50K | 64 | **1.28** | Compact JSON, efficient |
| **MCP2** paper-search | ~50K | ~500K | 148 | **0.30** | Large metadata payloads |
| **MCP3** bundled | ~15K | ~150K | 107 | **0.71** | Moderate size, high value |

**Token Efficiency Ranking:** MCP1 > MCP3 > MCP2

### Cost-Benefit
- **MCP1** gives best rel/1K tokens (1.28) but lowest absolute relevance (64)
- **MCP3** is the best **value-per-token** among high-relevance options (0.71 rel/1K tokens)
- **MCP2** costs 10× tokens of MCP1 but returns only 2.3× relevant papers

---

## Error Analysis

| MCP | Error Rate | Specific Errors |
|-----|-----------|-----------------|
| **MCP1** | 0% | Clean |
| **MCP2** | 70% queries | `zenodo: isoformat` error (7/10); `pubmed: malformed` (3/10); biorxiv/medrxiv include many irrelevant bio/med preprints |
| **MCP3** | 0% | Clean; auto-dedup works well |

### Source Quality (MCP2)
- **Reliable:** arxiv, crossref, openalex, core, europepmc (return 5 each consistently)
- **Unreliable:** pubmed (malformed XML), zenodo (object error), google_scholar (0 results)
- **Noise-prone:** biorxiv, medrxiv (return biomedical papers unrelated to education/feedback)

---

## Query Difficulty Ranking

| Query | Avg Relevant | Difficulty | Notes |
|-------|-------------|------------|-------|
| Q8 "metacognitive laziness" | 21.7 | Easiest | Very specific phrase, high match |
| Q9 "uptake taxonomy feedback L2 writing" | 13.7 | Easy | Well-established research area |
| Q6 "LLM self-assessment bias" | 11.7 | Medium | Broad, partially matched |
| Q4 "DeBERTa educational text" | 11.3 | Medium | Niche but specific |
| Q10 "hybrid AI human feedback writing" | 12.0 | Medium | Growing field |
| Q2 "peer teacher feedback comparison L2" | 7.7 | Medium-Hard | Split across subfields |
| Q5 "feedback literacy intervention" | 8.3 | Medium | Well-defined construct |
| Q1 "LLM feedback accuracy category-level" | 6.3 | Hard | Niche combo of terms |
| Q3 "AI feedback uptake meta-analysis" | 8.3 | Medium | "Uptake" is polysemous |
| Q7 "spaced micro-learning AI feedback" | 5.3 | Hardest | Rare combination |

---

## Recommendations

1. **For precision-focused research** (fewer, better papers): Use **MCP3** (0.71 precision)
2. **For exhaustive search** (maximum coverage): Use **MCP2** (2.6× more papers)
3. **For token-budgeted contexts**: Use **MCP1** (1.28 rel/1K tokens)
4. **For production systems**: Combine MCP3 + MCP2, deduplicate, then re-rank by relevance
5. **MCP2 improvements**: Exclude biorxiv, medrxiv, pubmed for education queries; add source filtering

---

## Raw Data Files

- `research-mcp/raw_benchmark.json` — Full structured results for Q3–Q10
- Queries Q1–Q2 raw data available in conversation history
