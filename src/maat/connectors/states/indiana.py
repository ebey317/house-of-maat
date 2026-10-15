from .base import StateSource

# Indiana. All URLs below were verified with an actual HTTP request
# returning 200 (2026-10-15). All fee amounts are from the official
# Indiana Trial Court Fee Manual (Indiana Office of Court Services).
# Doxpop is paywalled: it is linked for reference only and is never
# scraped or otherwise accessed programmatically.

FEE_MANUAL_URL = ('https://www.in.gov/dA/73b74027cf/'
                  'courtmgmt-pubs-trial-court-fee-manual.pdf?language_id=1')
FEE_SOURCE = 'Indiana Trial Court Fee Manual (Indiana Office of Court Services)'


class IndianaSource(StateSource):
    def state_code(self) -> str:
        return 'IN'

    def forms_index(self) -> list:
        return [
            {'name': 'Self-Service Legal Center',
             'url': 'https://www.in.gov/courts/selfservice/',
             'description': 'Indiana Supreme Court self-help hub: forms, guides, and '
                            'resources for self-represented litigants.'},
            {'name': 'IOCS Publications',
             'url': 'https://www.in.gov/courts/iocs/publications/',
             'description': 'Indiana Office of Court Services manuals, handbooks, '
                            'and court forms (small claims manual, fee manual, more).'},
            {'name': 'Protection Order Forms',
             'url': 'https://www.in.gov/courts/iocs/publications/po-forms/',
             'description': 'Official statewide protection order / no-contact forms.'},
            {'name': 'Indiana E-Filing',
             'url': 'https://www.in.gov/courts/efiling/',
             'description': 'File court documents electronically through the '
                            'Indiana E-Filing System (Odyssey).'},
            {'name': 'E-Filing Help',
             'url': 'https://www.in.gov/courts/help/efiling/',
             'description': 'E-filing guides and help for self-represented filers.'},
            {'name': 'Trial Court Fees Publication',
             'url': 'https://www.in.gov/courts/iocs/publications/trial-fees/',
             'description': 'Official trial court fee manual: every filing fee and '
                            'cost by case type, with code citations.'},
        ]

    def court_rules(self) -> list:
        return [
            {'name': 'Indiana Rules of Court (official portal)',
             'url': 'https://rules.incourts.gov/'},
            {'name': 'Trial Rule 1 - Scope of the Rules',
             'url': 'https://rules.incourts.gov/Content/trial/rule1/current.htm'},
            {'name': 'Trial Rule 82 - Forms',
             'url': 'https://rules.incourts.gov/Content/trial/rule82/current.htm'},
            {'name': 'Small Claims Rule 1 - Scope',
             'url': 'https://rules.incourts.gov/Content/small-claims/rule1/current.htm'},
            {'name': 'Small Claims Rule 2 - Commencement of Action',
             'url': 'https://rules.incourts.gov/Content/small-claims/rule2/current.htm'},
            {'name': 'Small Claims Rule 8 - Informality of Hearing',
             'url': 'https://rules.incourts.gov/Content/small-claims/rule8/current.htm'},
        ]

    def fee_schedule(self) -> list:
        outside = 'Indiana small claims courts (outside Marion County township courts)'
        marion = 'Marion County township small claims courts'
        fees = [
            (outside, 'Small Claims Filing Fee (IC 33-37-4-6)', 3500),
            (outside, 'Small Claims Service Fee (IC 33-37-4-6)', 1000),
            (outside, 'Document Storage Fee (IC 33-37-5-20)', 500),
            (outside, 'Automated Record Keeping Fee (IC 33-37-5-21)', 2000),
            (outside, 'Public Defense Administration Fee (IC 33-37-5-21.2)', 500),
            (outside, 'Judicial Insurance Adjustment Fee (IC 33-37-5-25)', 100),
            (outside, 'Judicial Salaries Fee (IC 33-37-5-26)', 1500),
            (outside, 'Pro Bono Services Fee (IC 33-37-5-31)', 100),
            (outside, 'Court Administration Fee (IC 33-37-5-27)', 500),
            (marion, 'Filing Fee + Township Docket Fee (IC 33-34-8-1)', 3700),
            (marion, 'Small Claims Service Fee (IC 33-37-5-35, eff. 7/1/2025)', 2600),
            (marion, 'Redocketing Fee (IC 33-34-8-3(a))', 500),
            (marion, 'Document Storage Fee (IC 33-37-5-20)', 500),
            (marion, 'Automated Record Keeping Fee (IC 33-37-5-21)', 2000),
            (marion, 'Public Defense Administration Fee (IC 33-37-5-21.2)', 500),
            (marion, 'Judicial Insurance Adjustment Fee (IC 33-37-5-25)', 100),
            (marion, 'Judicial Salaries Fee (IC 33-37-5-26)', 1500),
            (marion, 'Pro Bono Services Fee (IC 33-37-5-31)', 100),
            (marion, 'Court Administration Fee (IC 33-37-5-27)', 500),
        ]
        out = [{'court': c, 'filing_type': t, 'amount_cents': a, 'verified': True,
                'source_url': FEE_MANUAL_URL, 'source': FEE_SOURCE,
                'description': 'Per-case filing fee from the official fee manual.'}
               for c, t, a in fees]
        out.append({
            'court': outside,
            'filing_type': 'Total small-claims filing costs',
            'amount_cents': 9700, 'verified': True,
            'source_url': FEE_MANUAL_URL, 'source': FEE_SOURCE,
            'description': 'Sum of all fees above. $87.00 if filed via the Indiana '
                           'electronic filing system; add $28 if sheriff service requested.'})
        out.append({
            'court': marion,
            'filing_type': 'Total small-claims filing costs',
            'amount_cents': 13000, 'verified': True,
            'source_url': FEE_MANUAL_URL, 'source': FEE_SOURCE,
            'description': 'Sum of all Marion County township small-claims fees above.'})
        out.append({
            'court': 'Indiana trial courts (other case types)',
            'filing_type': 'Filing fees for civil, probate, criminal, and other case types',
            'amount_cents': None, 'verified': False,
            'source_url': FEE_MANUAL_URL, 'source': FEE_SOURCE,
            'description': 'Varies by case type and county; see the fee manual or '
                           'contact the county clerk. Not yet transcribed here.'})
        return out

    def self_help_links(self) -> list:
        return [
            {'name': 'Self-Service Legal Center',
             'url': 'https://www.in.gov/courts/selfservice/',
             'description': 'Indiana Supreme Court self-help forms and guides.'},
            {'name': 'E-Filing Help',
             'url': 'https://www.in.gov/courts/help/efiling/',
             'description': 'How to e-file as a self-represented litigant.'},
            {'name': 'Indiana Legal Help',
             'url': 'https://indianalegalhelp.org/',
             'description': 'Coalition for Court Access: legal aid directory and '
                            'self-help resources for Hoosiers.'},
            {'name': 'Doxpop (trial court records)',
             'url': 'https://www.doxpop.com/prod/',
             'description': 'Indiana trial-court records lookup. Subscription '
                            'service; linked for reference only, never scraped.'},
        ]
