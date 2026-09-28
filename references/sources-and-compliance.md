# Sources and Compliance

Read this file when choosing where metadata or PDFs come from, or when deciding whether a fetch is
allowed.

## Metadata

| Source | Use for | Notes |
|---|---|---|
| Crossref, `api.crossref.org/works/{doi}` | the authoritative record | free, no key, include a contact email in the request |
| The PDF itself | a cross-check on title and DOI | never the primary source for a citation |
| Publisher landing page | a human check on ambiguous records | manual step, not automated here |

Crossref carries the title, author list, container title, volume, issue, page range, publication
date, and type. That set is enough for a complete reference in every common style, which is why the
skill builds citations from it rather than from scraping page text.

When Crossref returns several records, the one whose DOI matches exactly wins. When a record is
missing a field, leave the field out rather than inventing a plausible value; a missing volume number
is visible and fixable, a wrong one is not.

## Open-access PDFs

Unpaywall reports, per DOI, whether an open version exists and where. The skill takes the best
open-access location and, when that location has no direct PDF, falls back to the landing URL rather
than guessing a file path.

Order of preference when several open locations exist: publisher open access, then a repository copy
deposited by the authors, then a preprint server. Record which one was used; the version matters when
the text is quoted.

## What is never allowed

- Scraping a publisher site behind a login, a cookie, or an entitlement check.
- Any mirror or library of unclear legality, however convenient.
- Circumventing a paywall, a proxy restriction, an embargo, or a rate limit.
- Presenting a preprint as the version of record, or the reverse.

If none of the legal routes yields a PDF, the correct output is a `manual` row with the DOI link. The
author then uses their own institutional access, which is the only path that is both legal and
reliable.

## Etiquette for bulk querying

- Always send a contact email; both Crossref and Unpaywall use it to reach you before blocking you.
- One request at a time with roughly half a second between calls is plenty for a review's reference
  list.
- Cache responses on disk so a re-run does not re-query. The skill writes `metadata.json` per
  reference and reuses it unless `--refresh` is passed.
- Stop rather than retry hard on repeated failures. A throttled run that resumes later beats a banned
  address.

## What goes into a shared library

The library folder is meant to be shared with co-authors, which means it must contain nothing
personal beyond the reference material: no API keys, no tokens, no proxy credentials, no browser
cookies. Contact emails belong in the command line, never in a committed file.
