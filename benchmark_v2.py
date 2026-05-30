"""Quick benchmark v2: using correct academix server functions like the bundle does."""
import asyncio, json, os, sys, time
from pathlib import Path

for t, s in [('paper-search-mcp', 'Lib/site-packages'), ('academix', 'Lib/site-packages')]:
    p = Path.home() / 'AppData/Roaming/uv/tools' / t / s
    if p.exists(): sys.path.insert(0, str(p))

os.environ['UNPAYWALL_EMAIL'] = '22080209d@connect.polyu.hk'
os.environ['PAPER_SEARCH_MCP_UNPAYWALL_EMAIL'] = '22080209d@connect.polyu.hk'
os.environ['ACADEMIX_EMAIL'] = '22080209d@connect.polyu.hk'

from academix import server as ac_server
from paper_search_mcp import server as ps_server

async def main():
    query = 'retrieval augmented generation'

    # --- ACADEMIX via correct server function ---
    print('=== ACADEMIX ===')
    t0 = time.monotonic()
    try:
        r1 = await ac_server.academic_search_papers(query=query, limit=10, sort='relevance', response_format='json')
        if isinstance(r1, str): r1 = json.loads(r1)
        papers = r1.get('papers', []) if isinstance(r1, dict) else []
        print(f'{len(papers)} papers in {time.monotonic()-t0:.1f}s')
        for p in papers[:3]:
            cc = p.get('citation_count', 0) if isinstance(p, dict) else 0
            t = p.get('title', '?') if isinstance(p, dict) else str(p)[:80]
            print(f'  [{cc:>4} cites] {str(t)[:80]}')
        ac_papers = papers
    except Exception as e:
        print(f'Error: {e}')
        ac_papers = []

    # --- PAPER-SEARCH ---
    print()
    print('=== PAPER-SEARCH (arxiv,semantic,openalex,crossref,pubmed) ===')
    t0 = time.monotonic()
    try:
        r2 = await ps_server.search_papers(query=query, max_results_per_source=5,
                                           sources='arxiv,semantic,openalex,crossref,pubmed')
        ps_papers = r2.get('papers', []) if isinstance(r2, dict) else []
        srcs = r2.get('sources_used', []) if isinstance(r2, dict) else []
        print(f'{len(ps_papers)} papers in {time.monotonic()-t0:.1f}s')
        print(f'Sources: {srcs}')
        for p in ps_papers[:3]:
            print(f'  [{p.get("source","?"):>12}] {p.get("title","?")[:80]}')
    except Exception as e:
        print(f'Error: {e}')
        ps_papers = []

    # --- CROSS-SOURCE OVERLAP ---
    print()
    print('=== CROSS-SOURCE OVERLAP ===')
    paper_search_titles = set(str(p.get('title','')).strip().lower()[:80] for p in ps_papers)
    academix_titles = set()
    for p in ac_papers:
        if isinstance(p, dict):
            academix_titles.add(str(p.get('title','')).strip().lower()[:80])
    
    overlap = paper_search_titles & academix_titles
    only_ac = academix_titles - paper_search_titles
    only_ps = paper_search_titles - academix_titles
    print(f'Academix unique: {len(only_ac)} | Paper-Search unique: {len(only_ps)} | Overlap: {len(overlap)}')
    print(f'Total unique papers across both: {len(only_ac) + len(only_ps) + len(overlap)}')
    if overlap:
        print(f'Duplicates found: {len(overlap)} papers exist in both backends (would be deduped by bundle)')
    
    # --- QUALITY CHECK ---
    print()
    print('=== QUALITY CHECK ===')
    all_with_citations = []
    for p in ps_papers:
        if isinstance(p, dict):
            cit = p.get('citations') or p.get('citation_count') or 0
            all_with_citations.append((cit, p.get('title','?'), p.get('source','?')))
    all_with_citations.sort(reverse=True)
    print('Top 5 by citation count (paper-search):')
    for c, t, s in all_with_citations[:5]:
        print(f'  [{c:>4} cites] [{s:>12}] {str(t)[:80]}')

    print()
    print(f'TOTAL: Bundle would give {len(only_ac) + len(only_ps) + len(overlap)} unique papers')
    print(f'       vs running either backend alone ({len(ac_papers)} or {len(ps_papers)})')
    coverage_gain = (len(only_ac) + len(only_ps) + len(overlap)) / max(len(ac_papers), len(ps_papers), 1)
    print(f'       Coverage gain: {coverage_gain:.1f}x over the best single backend')

asyncio.run(main())
