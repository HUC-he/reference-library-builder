---
name: reference-library-builder
description: >-
  Build a review paper's reference library from DOIs: resolve metadata through Crossref, find the
  legal open-access PDF, download it, and export citation files (RIS, EndNote ENW, BibTeX) plus a
  status index, then verify that each downloaded PDF really is the reference it claims to be. Use
  for 文献库, 批量下载文献, 参考文献 PDF, 导出 RIS, EndNote ENW, BibTeX, Zotero, 引用格式,
  DOI 校验, 综述文献管理, literature library, reference manager export, open access PDF fetching,
  bibliography building. Never bypasses a paywall.
---

# Reference Library Builder

Turn a list of DOIs into an organised, verifiable reference library: correct metadata, legal PDFs,
citation files your reference manager can import, and an index that says what is missing.

The two failure modes this skill exists to prevent are a library of PDFs that nobody can cite
correctly, and a citation list whose metadata was typed by hand.

## What it produces

For each reference: a `.ris`, a `.enw`, and a `.bib` entry built from publisher metadata, plus the
open-access PDF when one legally exists, all in one folder with a stable file name. Across the
library: `index.csv` and `index.md` listing the DOI, year, first author, title, journal, open-access
status, and which files exist.

## Ground rules

- Metadata comes from Crossref, not from guessing. One DOI resolves to one record, and the record is
  the source of truth for the citation files.
- Only legally available PDFs. The skill uses open-access locations reported by Unpaywall. If nothing
  is open, the reference is recorded as `manual` with its DOI landing page, and the author fetches it
  through their own institutional access.
- Never bypass a paywall, a login, a proxy, or a publisher restriction. A missing PDF is a result, not
  a bug to work around.
- State the contact email. Crossref and Unpaywall both ask for one, and using it is what makes bulk
  querying acceptable rather than abusive.
- Pace the requests. Default is half a second between calls; do not raise it to scrape.
- Verify before citing. A downloaded PDF that does not contain its DOI or title is a wrong file, and
  it is far cheaper to catch here than in proof.

## Workflow

1. Collect the DOIs. Accept a plain list, one per line, or the DOIs inside a `.bib`, `.ris`, or
   exported reference list. Drop duplicates and normalise the `https://doi.org/` prefix.
2. Resolve metadata:

   ```bash
   python3 scripts/refs.py build --input dois.txt --out 文献库 \
     --email you@example.com --pdf --formats ris,enw,bib
   ```

   Every reference gets its citation files. With `--pdf`, each open-access PDF is downloaded and
   named after its first author, year, and title.
3. Read the summary the tool prints. Anything marked `manual` needs a PDF from the author's own
   access; nothing else needs attention.
4. Verify the library:

   ```bash
   python3 scripts/refs.py verify --dir 文献库
   ```

   Each PDF is checked for its DOI, then for title words from the resolved metadata. A mismatch is
   reported as `WRONG FILE` and the entry stays unverified until a human looks at it.
5. Import. Point Zotero or EndNote at the folder, or import the combined `library.ris`. Read
   [references/library-layout.md](references/library-layout.md) for the folder contract and the
   index columns.

## Citation formats

RIS for Zotero and most reference managers, ENW for EndNote, BibTeX for LaTeX. The writers are
deterministic, so re-running the same DOI produces byte-identical output and the diff stays readable.

Author names keep the order Crossref reports and keep the family name first in RIS and ENW, because
that is what the importers expect. Titles keep publisher capitalisation. A journal-less record, such
as a preprint, is written with its repository as the container rather than dropped.

## When a reference is not open access

The index row says `manual` and carries the DOI link. Options for the author, in order of preference:
fetch it through their institution, request it from a co-author, or email the corresponding author.
The skill never substitutes a different paper, a preprint of unknown provenance, or a
shadow-library copy.

## Pairing with the review workflow

This skill builds and verifies the library. Citing the library inside manuscript text is a different
job, and an existing citation skill handles it; verifying that an existing reference list is
internally consistent is another. Hand this skill's `index.csv` to those, because it already records
which entries are verified and which are not.

## Red lines

- Never download from a paywall, a pirate mirror, or a source of unclear legality.
- Never invent, complete, or "fix" metadata that Crossref does not report.
- Never mark a reference verified when the PDF was not checked, or when the check failed.
- Never write an API key, a personal token, or a proxy credential into the library, the scripts, or
  the index.
- Never present a preprint as the published version, or the reverse.

## Related files

| File | Open when |
|---|---|
| [references/sources-and-compliance.md](references/sources-and-compliance.md) | Choosing a metadata or open-access source, or checking what is allowed |
| [references/library-layout.md](references/library-layout.md) | Deciding the folder contract, file names, or index columns |
| [scripts/refs.py](scripts/refs.py) | Running build, verify, or index |
| [examples/demo-library.md](examples/demo-library.md) | Showing a real run and what its output looks like |
