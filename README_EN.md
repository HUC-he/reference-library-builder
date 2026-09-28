# `reference-library-builder`

[中文](README.md)

![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![deps](https://img.shields.io/badge/deps-none%20(stdlib)-brightgreen)
![tests](https://img.shields.io/badge/tests-18%20passing-brightgreen)

In one line: turn a list of DOIs into a **verifiable review library** — metadata from Crossref rather
than from typing, legal open-access PDFs fetched automatically, RIS, EndNote ENW, and BibTeX written
in one pass, and every downloaded PDF checked against the reference it claims to be.

It exists to prevent two common accidents: a folder of PDFs that nobody can cite correctly, and a
reference list whose metadata was typed by hand.

## What it is for

- Building the reference library for a review: a list of DOIs in, `pdf/ + cite/ + index.csv` out.
- Exporting RIS, ENW, or BibTeX straight into Zotero, EndNote, or LaTeX.
- Auditing a reference list in bulk: which papers are open access, which need institutional access,
  which DOIs are wrong.
- Checking before submission that a cited PDF really is the cited paper.

Not for: inserting citations into manuscript text (a citation skill), or auditing an existing
reference list for internal consistency (a reference-verifying skill). This skill builds and verifies
the library, and hands over `index.csv`.

## Four ground rules

Metadata comes from Crossref, never from guessing or "fixing". Only legally open PDFs are downloaded.
Paywalls, logins, proxies, and publisher restrictions are never bypassed; a paper with no legal open
copy is recorded as `manual` and left to the author's own access. Bulk querying carries a contact
email and a default half-second delay.

## Usage

```bash
python3 scripts/refs.py build --input dois.txt --out library \
  --email you@example.com --pdf --formats ris,enw,bib
python3 scripts/refs.py verify --dir library
python3 scripts/refs.py index --dir library
```

A real run, full transcript in [examples/demo-library.md](examples/demo-library.md):

```text
library at library: 5 references, 2 open PDF(s)
2 reference(s) need your own access:
  - 10.1038/nnano.2016.300  "Water-evaporation-induced electricity with nanostructured ca"
  - 10.1038/s41586-020-2010-9  "Power generation from ambient humidity using protein nanowir"

$ python3 scripts/refs.py verify --dir library
OK       wu-2020-a-new-coronavirus-associated-with-human
OK       shan-2021-n-protein-presents-early-in-blood-dried
checked 2, mismatched 0, unverifiable 0
```

That batch also contained a bad DOI and a 404: the bad DOI produced one `error` row without stopping
the other references from resolving.

## Output layout

```text
library/
|-- index.csv                machine readable status, one row per reference
|-- index.md                 the same, readable
|-- library.ris              combined import file
|-- library.bib              combined BibTeX
|-- cite/                    one ris, enw, and bib per reference
|-- meta/                    Crossref record plus the open-access location
`-- pdf/                     open-access PDFs
```

File keys are stable — `first-author-year-title-slug` — so re-running a DOI does not duplicate the
entry in Zotero. `oa_status` is only ever `open`, `manual`, or `error`; `manual` is not a failure, it
means the paper needs your institutional access.

## Legality

Only open-access locations reported by Unpaywall: publisher open access, an institutional or author
repository, or a preprint server. Paywalled papers stay in `manual` with their DOI link, for the
author to fetch through their subscription, interlibrary loan, or a request to the authors. This
skill never substitutes a mirror of unclear legality, and never presents a preprint as the version
of record.

## Install

```bash
git clone https://github.com/HUC-he/reference-library-builder.git \
  ~/.codex/skills/reference-library-builder
```

Or ask Codex to install it with `$skill-installer`:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo HUC-he/reference-library-builder --path . --name reference-library-builder
```

## Dependencies

Building a library needs no third-party packages. Verifying PDF text needs `pymupdf`; without it
`verify` says so instead of pretending the check passed. If the interpreter has no usable CA store,
the script prefers `certifi`'s bundle.

## Red lines

Never download from a paywall, a pirate mirror, or a source of unclear legality. Never invent metadata
Crossref does not report. Never mark a reference verified when it was not checked or the check
failed. Never write an API key, token, or proxy credential into the library, the scripts, or the
index. Never present a preprint as the published version, or the reverse.

## Contact and keywords

Author: UUNICE (GitHub [@HUC-he](https://github.com/HUC-he)). Feedback: shiyuhe1@163.com.

Keywords: literature library, reference manager export, RIS, EndNote ENW, BibTeX, Zotero, DOI lookup,
Crossref, Unpaywall, open access PDFs, bibliography building, reference verification.

## License

MIT, see [LICENSE](LICENSE).
