# Debug & Visualization

Enable structured logs:
```bash
DEBUG=1 python3 -m Tafsir.pipeline.analysis.sahihah.compare_txt_agains_db
```

Plot coverage trend:
```bash
DEBUG=1 PLOT_COVERAGE=1 python3 -m Tafsir.pipeline.analysis.sahihah.compare_txt_agains_db
```

Key debug sections:
- Anchors (strength)
- Candidate flow (AND/OR/fallback counts)
- Cache stats
- Objective (coverage + avg_hit)
