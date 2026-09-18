# Legal Data Sources & Connectors

## Primary law (free APIs)

| Source | Coverage | Access |
|---|---|---|
| CourtListener / Free Law Project | US federal + state case law, RECAP dockets | https://www.courtlistener.com/api/rest/v4/ |
| GovInfo | U.S. Code, Statutes at Large, Federal Register | https://api.govinfo.gov/ |
| Regulations.gov | Federal rulemaking comments and documents | https://www.regulations.gov/api/ |
| eCFR | Code of Federal Regulations (current) | https://www.ecfr.gov/api/ |
| Indiana Doxpop | Indiana state trial court records | https://doxpop.com/ |
| Indiana Judiciary self-help | Indiana forms + rules | https://www.indianajudiciary.gov/ |

## MCP servers

| Server | Endpoint / Repo | Notes |
|---|---|---|
| CourtListener official MCP | https://mcp.courtlistener.com/ | OAuth 2.0 or API token; search, analyze_citations, alerts |
| CourtListener++ (community) | Travis-Prall/court-listener-mcp | Adds GovInfo, Regulations.gov; PolyForm Noncommercial |

## Indiana-specific forms (examples)

- Small Claims: https://www.indianajudiciary.gov/rules/small-claims/
- Fee Waiver (Form 29620): https://www.indianajudiciary.gov/
