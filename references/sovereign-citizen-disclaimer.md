# Sovereign-citizen / UCC-redemption / strawman disclaimer template

Verbatim text the motion drafter must insert as a non-removable header on
every page of any filing built from a rejected-by-courts theory. The user
chose to allow these filings; the drafter's job is informed consent.

## The header (every page, top, bold, non-removable)

```
NOTICE — This filing is based on theories that have been rejected
by every federal circuit court of appeals and every state supreme
court. See e.g., United States v. Benabe, 654 F.3d 753 (7th Cir.
2011); United States v. Schaefer, 859 F.3d 871 (8th Cir. 2017);
United States v. Davis, 564 F.3d 411 (2d Cir. 2009).

The maintainer(s) of this tool are not attorneys and do not provide
legal advice. This document is generated on the user's explicit
request over the tool's caution. Use at your own risk.

Filing a frivolous pleading can result in Rule 11 sanctions, 28
U.C. § 1927 penalties, or criminal referral under 18 U.C.
§§ 1001, 1504, 1519.
```

## The body cite

In the motion's "Statement of Authority" section, before the user-supplied
theory, the drafter inserts:

> "The undersigned acknowledges that the theories advanced in this filing
> have been considered and rejected by every federal circuit court of
> appeals and every state supreme court. See, e.g., *United States v.
> Benabe*, 654 F.3d 753 (7th Cir. 2011) (rejecting sovereign-citizen
> theory as 'legal fiction'); *United States v. Schaefer*, 859 F.3d 871
> (8th Cir. 2017) (rejecting UCC redemptionist scheme); *United States
> v. Davis*, 564 F.3d 411 (2d Cir. 2009) (rejecting strawman-account
> theory). This filing is submitted on the user's explicit request after
> notice of the controlling rejection record."

## The Warning Cover Sheet (separate PDF, before user signs)

Single page, plain English, bolded:

```
WARNING COVER SHEET

You are about to sign and file a court document based on legal theories
that have been rejected by every federal circuit court of appeals and
every state supreme court.

WHAT THIS MEANS:
- The court is highly likely to deny the motion.
- The court may impose Rule 11 sanctions against you (monetary penalty).
- The court may refer the matter for criminal prosecution under 18 U.C.
  § 1001 (false statements) or § 1504 (remedy by confusion).
- The filing becomes a public record in your case.

YOU ARE PROCEEDING OVER THE TOOL'S CAUTION.
The maintainer(s) of this tool have inserted the controlling case law
into your filing so the court cannot claim you were unaware. The choice
to file is yours alone.

Signature: ______________________ Date: __________
```

## Implementation in the drafter

1. Detect the theory family by keywords in the user's input:
   - "sovereign citizen," "sovereign," "strawman," "UCC redemption,"
     "copyright my name," "all caps," "acceptance for value," "bonds,"
     "fictitious name," "free inhabitant," "pre-14th Amendment status"
2. If matched: emit the disclaimer header on every page (PDF layer or
   header/footer in DOCX), insert the body cite, generate the Warning
   Cover Sheet as a separate PDF in the same filing packet.
3. Do NOT block generation. Do NOT require a checkbox confirmation.
   The header + body cite + cover sheet IS the informed-consent
   mechanism.
4. Do NOT e-sign (perjury). User signs manually or via their PACER /
   state e-filing account.

## Why this is the right shape

- **Black-marketing the theory pushes users to less-cautious tools.**
  Skipping the disclaimer would feel safer in the moment but produces
  worse real-world outcomes — Rule 11 sanctions, criminal referral,
  unrecoverable court records.
- **The First Amendment protects the right to file a frivolous
  motion.** The drafter's job is not to refuse; it's to make sure the
  filer can't claim nobody told them.
- **Adult-tool framing.** We inform, the user decides. Same shape as
  every other motion the tool generates — the difference is the rejection
  record is the controlling authority, not a niche support citation.