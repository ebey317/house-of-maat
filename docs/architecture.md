# Architecture

```
maat
├── cli.py              # click CLI entry point
├── modes
│   ├── ask.py          # plain-English legal Q&A
│   ├── research.py     # case-law research + small-batch ranking
│   └── file.py         # draft filing packet
├── connectors
│   ├── courtlistener.py # REST client + optional MCP wrapper
│   └── seeds.py         # Maat + Black's 4th seed queries
├── templates
│   └── loader.py        # template discovery/scaffold
├── forms
│   └── fillable.py      # fillable PDF form support
└── seeds
    ├── maat/            # 42 Laws of Maat chunks
    └── blacks4/         # Black's 4th edition chunks
```

## Data flow

1. User runs a command.
2. Mode loads templates / evidence / seed context.
3. If research is needed, `connectors/courtlistener.py` queries the API.
4. Draft is generated from template + evidence + verified citations.
5. `analyze_citations` is called before output.
6. Packet is written to `output/` for user review, signature, and filing.
