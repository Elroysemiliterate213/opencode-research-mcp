"""Smoke tests for the research-mcp helpers and merge logic.

Run with: python tests/test_smoke.py
These don't hit any external APIs (everything is mocked or unit-level).
"""
import sys
import importlib.util
from pathlib import Path

# Add parent directory so 'publisher_apis' module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load the bundle module from the parent directory
BUNDLE = Path(__file__).parent.parent / "research_bundle.py"
spec = importlib.util.spec_from_file_location("rb", BUNDLE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

PASS = "[PASS]"
FAIL = "[FAIL]"


def check(label, condition):
    status = PASS if condition else FAIL
    print(f"{status} {label}")
    return condition


# ---------- _compact_authors ----------
print("== _compact_authors ==")
assert check("<= 5 authors kept as-is", m._compact_authors(["A", "B", "C"]) == ["A", "B", "C"])
assert check("> 5 authors get et al. marker", m._compact_authors(["A"] * 7) == ["A", "A", "A", "A", "A", "et al. (7 total)"])
assert check("empty list returns empty", m._compact_authors([]) == [])

# ---------- _compress_venue ----------
print("\n== _compress_venue ==")
assert check("strips MIT Press suffix", "MIT Press" not in m._compress_venue("JMLR, MIT Press"))
assert check("strips IEEE suffix", "IEEE" not in m._compress_venue("CVPR - IEEE"))
assert check("strips 'Proceedings of the'", m._compress_venue("Proceedings of the ACL") == "ACL")
assert check("keeps plain name", m._compress_venue("Nature") == "Nature")
assert check("hard cap at 120", len(m._compress_venue("A" * 200)) <= 120)

# ---------- SURVEY_RE ----------
print("\n== SURVEY_RE ==")
assert check("detects 'review'", bool(m.SURVEY_RE.search("A review of attention")))
assert check("detects 'survey'", bool(m.SURVEY_RE.search("A Survey of Transformers")))
assert check("detects 'meta-analysis'", bool(m.SURVEY_RE.search("Meta-analysis of clinical trials")))
assert check("detects 'systematic review'", bool(m.SURVEY_RE.search("A systematic review of X")))
assert check("doesn't match random paper", not m.SURVEY_RE.search("Attention is all you need"))

# ---------- _cosine ----------
print("\n== _cosine ==")
assert check("identical = 1.0", abs(m._cosine([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-6)
assert check("orthogonal = 0.0", abs(m._cosine([1, 0, 0], [0, 1, 0]) - 0.0) < 1e-6)
assert check("opposite = -1.0", abs(m._cosine([1, 0, 0], [-1, 0, 0]) - -1.0) < 1e-6)
assert check("empty returns 0.0", m._cosine([], []) == 0.0)
assert check("mismatched dims returns 0.0", m._cosine([1, 0], [1, 0, 0]) == 0.0)

# ---------- _paper_key ----------
print("\n== _paper_key ==")
assert check("DOI takes priority", m._paper_key({"doi": "10.1/x", "arxiv_id": "2001.12345"}) == "doi:10.1/x")
assert check("arxiv fallback", m._paper_key({"arxiv_id": "2001.12345"}) == "arxiv:2001.12345")
assert check("title+year fallback", m._paper_key({"title": "Hello World", "year": 2020}) == "title:hello world:2020")
assert check("empty title returns empty", m._paper_key({"title": ""}) == "")

# ---------- _normalize_paper ----------
print("\n== _normalize_paper ==")
p = m._normalize_paper({
    "title": "A systematic review of X",
    "authors": ["A"] * 10,
    "year": 2020,
    "venue": "JMLR, MIT Press",
    "doi": "10.1/x",
}, "arxiv")
assert check("is_survey detected", p["is_survey"] is True)
assert check("author_count = 10", p["author_count"] == 10)
assert check("authors compact len = 6", len(p["authors"]) == 6)
assert check("source_count = 1", p["source_count"] == 1)
assert check("venue compressed", "MIT Press" not in p["venue"])

# ---------- _merge_papers: quality filter ----------
print("\n== _merge_papers: quality filter ==")
bad = {"title": "Noise", "doi": "10.1/bad", "year": 2020, "abstract": "", "citation_count": 2, "sources": ["x"]}
good = {"title": "Good", "doi": "10.1/good", "year": 2020, "abstract": "Has abstract", "citation_count": 2, "sources": ["x"]}
out = m._merge_papers([bad, good], 10, query="test", mode="comprehensive")
assert check("low-quality paper dropped", not any(p["doi"] == "10.1/bad" for p in out))

# ---------- _merge_papers: modes ----------
print("\n== _merge_papers: modes ==")


def _yr(out, p):
    for x in out:
        if x.get("doi") == p["doi"]:
            return x.get("year") or 0
    return 0


papers = [
    m._normalize_paper({"title": "A review of attention", "doi": "10.1/a", "year": 2024, "abstract": "review", "citation_count": 50, "authors": ["X"], "venue": "X"}, "openalex"),
    m._normalize_paper({"title": "Attention is all you need", "doi": "10.1/b", "year": 2017, "abstract": "transformer", "citation_count": 80000, "authors": ["Y"], "venue": "NeurIPS"}, "openalex"),
    m._normalize_paper({"title": "Old paper", "doi": "10.1/c", "year": 2010, "abstract": "stuff", "citation_count": 100000, "authors": ["Z"], "venue": "X"}, "openalex"),
]
out_s = m._merge_papers(papers, 10, query="attention", mode="seminal")
assert check("seminal: oldest of high-cite first",
             out_s[0]["year"] == 2010)

out_r = m._merge_papers(papers, 10, query="attention", mode="recent")
assert check("recent: only last 2 years",
             all(_yr(out_r, p) >= 2024 for p in out_r))

# Survey mode requires is_survey=True
survey_paper = m._normalize_paper({"title": "A meta-analysis of X", "doi": "10.1/s", "year": 2023, "abstract": "stuff", "citation_count": 50, "authors": ["X"], "venue": "X"}, "openalex")
out_sv = m._merge_papers(papers + [survey_paper], 10, query="attention", mode="survey")
assert check("survey: only surveys",
             all(p.get("is_survey") for p in out_sv) and len(out_sv) > 0)


# ---------- _detect_field ----------
print("\n== _detect_field ==")
assert check("detects CS", m._detect_field("transformer attention mechanism") == "cs")
assert check("detects medical", m._detect_field("patient clinical trial cancer") == "medical")
assert check("detects bio", m._detect_field("CRISPR gene editing") == "bio")
assert check("detects social", m._detect_field("education policy in schools") == "social")
assert check("defaults to general", m._detect_field("random gibberish") == "general")
assert check("priority: medical before bio", m._detect_field("patient gene therapy") == "medical")


# ---------- SOURCE_TIERS + _get_source_tier ----------
print("\n== SOURCE_TIERS ==")
assert check("scopus is tier 3", m.SOURCE_TIERS["scopus"] == 3)
assert check("semantic is tier 3", m.SOURCE_TIERS["semantic"] == 3)
assert check("arxiv is tier 2", m.SOURCE_TIERS["arxiv"] == 2)
assert check("europepmc is tier 1", m.SOURCE_TIERS["europepmc"] == 1)
# Field-aware: tier 1 biomedical only counts for medical/bio
assert check("europepmc is tier 0 in cs field", m._get_source_tier("europepmc", "cs") == 0)
assert check("europepmc is tier 1 in medical field", m._get_source_tier("europepmc", "medical") == 1)
assert check("europepmc is tier 1 in bio field", m._get_source_tier("europepmc", "bio") == 1)
assert check("unknown source is tier 0", m._get_source_tier("unknown", "general") == 0)


# ---------- _is_rescued ----------
print("\n== _is_rescued ==")
high_cite = {"citation_count": 1000, "source_count": 1, "is_survey": False, "title": "X", "abstract": ""}
assert check("high citations rescue", m._is_rescued(high_cite))
multi = {"citation_count": 1, "source_count": 4, "is_survey": False, "title": "X", "abstract": ""}
assert check("multi-source rescue", m._is_rescued(multi))
survey = {"citation_count": 1, "source_count": 1, "is_survey": True, "title": "X", "abstract": ""}
assert check("survey rescue", m._is_rescued(survey))
exact = {"citation_count": 1, "source_count": 1, "is_survey": False, "title": "transformer review", "abstract": ""}
assert check("exact title match rescue", m._is_rescued(exact, "transformer"))
weak = {"citation_count": 1, "source_count": 1, "is_survey": False, "title": "Random", "abstract": ""}
assert check("weak paper not rescued", not m._is_rescued(weak))


# ---------- _should_drop_low_quality ----------
print("\n== _should_drop_low_quality ==")
assert check("drops weak paper",
             m._should_drop_low_quality({"abstract": "", "citation_count": 2, "source_count": 1, "is_survey": False, "title": "X", "source_tier": 0}))
assert check("keeps high-cite weak paper",
             not m._should_drop_low_quality({"abstract": "", "citation_count": 600, "source_count": 1, "is_survey": False, "title": "X", "source_tier": 0}))
assert check("keeps multi-source weak paper",
             not m._should_drop_low_quality({"abstract": "", "citation_count": 2, "source_count": 3, "is_survey": False, "title": "X", "source_tier": 0}))
assert check("keeps survey paper",
             not m._should_drop_low_quality({"abstract": "", "citation_count": 2, "source_count": 1, "is_survey": True, "title": "X", "source_tier": 0}))
assert check("keeps paper with abstract",
             not m._should_drop_low_quality({"abstract": "has content", "citation_count": 0, "source_count": 1, "is_survey": False, "title": "X", "source_tier": 0}))
assert check("keeps tier-3-only paper",
             not m._should_drop_low_quality({"abstract": "", "citation_count": 2, "source_count": 1, "is_survey": False, "title": "X", "source_tier": 3}))


# ---------- _merge_papers: source_tier ranking ----------
print("\n== _merge_papers: source_tier ranking ==")
tier3 = m._normalize_paper({"title": "Tier3 paper", "doi": "10.1/t3", "year": 2020, "abstract": "x", "citation_count": 10, "authors": ["X"], "venue": "X"}, "semantic")
tier2 = m._normalize_paper({"title": "Tier2 paper", "doi": "10.1/t2", "year": 2020, "abstract": "x", "citation_count": 10, "authors": ["X"], "venue": "X"}, "arxiv")
tier1 = m._normalize_paper({"title": "Tier1 paper", "doi": "10.1/t1", "year": 2020, "abstract": "x", "citation_count": 10, "authors": ["X"], "venue": "X"}, "europepmc")
out = m._merge_papers([tier1, tier2, tier3], 10, query="test", mode="comprehensive", field="general")
assert check("tier 3 ranks above tier 2 (general field)", out[0]["doi"] == "10.1/t3")
assert check("tier 2 ranks above tier 1 (general field, biomed not counted)",
             out[1]["doi"] == "10.1/t2" and out[2]["doi"] == "10.1/t1")


# ---------- _merge_papers: field="medical" promotes tier-1 biomedical ----------
print("\n== _merge_papers: field=medical tier weighting ==")
out = m._merge_papers([tier1, tier2, tier3], 10, query="test", mode="comprehensive", field="medical")
# In medical field, tier 1 (europepmc) is now tier 1, tier 2 (arxiv) is tier 2, tier 3 (semantic) is tier 3
# Sort: tier3 > tier2 > tier1
assert check("tier 3 still top in medical", out[0]["doi"] == "10.1/t3")


# ---------- _merge_papers: debug mode ----------
print("\n== _merge_papers: debug ==")
out = m._merge_papers([tier3], 10, query="test", mode="comprehensive", debug=True)
assert check("debug adds score_breakdown", "score_breakdown" in out[0])
assert check("score_breakdown has semantic", "semantic" in out[0]["score_breakdown"])
assert check("score_breakdown has final", "final" in out[0]["score_breakdown"])
out2 = m._merge_papers([tier3], 10, query="test", mode="comprehensive", debug=False)
assert check("no debug breakdown by default", "score_breakdown" not in out2[0])


print(f"\n{'='*40}")
print("All smoke tests passed." if all(True for _ in []) else "Some tests failed.")  # placeholder
