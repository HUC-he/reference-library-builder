# Demo: a real library from real DOIs

Everything below is a genuine run of `scripts/refs.py` against Crossref and Unpaywall. The input was
five DOIs chosen to exercise all four outcomes: an open-access paper, a paywalled paper, a bad DOI,
and a paper whose open copy exists but is not directly downloadable.

## Input

```text
10.1038/nnano.2016.300              hydrovoltaic, paywalled
10.1038/s41586-020-2010-9           hydrovoltaic, paywalled
10.1038/s41586-020-2008-3           open access
10.1038/s41467-021-22072-9          open access
10.9999/not-a-real-doi-12345        deliberately invalid
```

## Build

```bash
python3 scripts/refs.py build --input dois.txt --out 文献库 \
  --email shiyuhe1@163.com --pdf
```

```text
[error] 10.9999/not-a-real-doi-12345: HTTP 404 for https://api.crossref.org/works/10.9999/not-a-real-doi-12345
[resolved] 10.1038/nnano.2016.300 -> Water-evaporation-induced electricity with nanostructured carbon
[resolved] 10.1038/s41586-020-2010-9 -> Power generation from ambient humidity using protein nanowires
[resolved] 10.1038/s41586-020-2008-3 -> A new coronavirus associated with human respiratory disease in C
  pdf: pdf/wu-2020-a-new-coronavirus-associated-with-human.pdf (publisher, publishedVersion)
[resolved] 10.1038/s41467-021-22072-9 -> N-protein presents early in blood, dried blood and saliva during
  pdf: pdf/shan-2021-n-protein-presents-early-in-blood-dried.pdf (publisher, publishedVersion)

library at 文献库: 5 references, 2 open PDF(s)
2 reference(s) need your own access:
  - 10.1038/nnano.2016.300  "Water-evaporation-induced electricity with nanostructured ca"
  - 10.1038/s41586-020-2010-9  "Power generation from ambient humidity using protein nanowir"
next: python3 scripts/refs.py verify --dir 文献库
```

Four things to notice.

The bad DOI did not stop the run. It produced an `error` row and the other four references still
resolved, which is what you want when a reference list came from a co-author.

The two paywalled papers were resolved correctly and recorded as `manual`. Their metadata and
citation files are complete; only the PDF is missing, and it needs the author's own institutional
access. This is the intended outcome, not a failure.

Both open-access PDFs came from the publisher rather than a repository, so they are the version of
record. The `host_type` and `version` in the parentheses are recorded in `meta/` for exactly this
reason.

Fetching publisher PDFs is not always that easy. In an earlier run of the same DOI, Nature answered
the PDF URL with an HTML consent page instead of the file. The downloader tries every open location
reported for the DOI and verifies the `%PDF` magic bytes, so that paper would have been recorded as
`manual` rather than stored as a `.pdf` that is really a web page.

## Verify

```bash
python3 scripts/refs.py verify --dir 文献库
```

```text
OK       wu-2020-a-new-coronavirus-associated-with-human
OK       shan-2021-n-protein-presents-early-in-blood-dried

checked 2, mismatched 0, unverifiable 0
```

A `WRONG FILE` line means the PDF text matched neither the DOI nor enough of the title, which is the
signature of a mis-downloaded or mis-named file. The entry stays unverified until a human looks at
it, and `index.csv` keeps that state.

## The library

```text
文献库/
|-- index.csv
|-- index.md
|-- library.ris
|-- library.bib
|-- cite/   5 x (ris, enw, bib)
|-- meta/   4 x metadata + open-access record
`-- pdf/    2 x open-access PDF
```

`index.md` as printed:

```text
# Reference library

references: 5  |  open: 2  |  manual: 2  |  verified: 2

| key | year | first author | title | open access | verified |
|---|---|---|---|---|---|
| xue-2017-water-evaporation-induced-electricity-with | 2017 | Xue | Water-evaporation-induced electricity with nanostructured carbon mater | manual | n/a |
| liu-2020-power-generation-from-ambient-humidity-using | 2020 | Liu | Power generation from ambient humidity using protein nanowires | manual | n/a |
| wu-2020-a-new-coronavirus-associated-with-human | 2020 | Wu | A new coronavirus associated with human respiratory disease in China | open | yes |
| shan-2021-n-protein-presents-early-in-blood-dried | 2021 | Shan | N-protein presents early in blood, dried blood and saliva during asymp | open | yes |
| unresolved-10-9999-not-a-real-doi-12345 |  |  | (metadata could not be resolved) | error | n/a |
```

## What the citation files look like

One RIS record, built from Crossref metadata with no hand typing:

```text
TY  - JOUR
AU  - Xue, Guobin
AU  - Xu, Ying
AU  - Ding, Tianpeng
AU  - Li, Jia
...
TI  - Water-evaporation-induced electricity with nanostructured carbon materials
JO  - Nature Nanotechnology
PY  - 2017
VL  - 12
IS  - 4
SP  - 317
EP  - 321
DO  - 10.1038/nnano.2016.300
UR  - https://doi.org/10.1038/nnano.2016.300
ER  -
```

And a BibTeX entry for an article that has an article number rather than a page range:

```text
@article{shan-2021-n-protein-presents-early-in-blood-dried,
  author = {Shan, Dandan and Johnson, Joseph M. and ...},
  title = {N-protein presents early in blood, dried blood and saliva during asymptomatic and symptomatic SARS-CoV-2 infection},
  journal = {Nature Communications},
  year = {2021},
  volume = {12},
  number = {1},
  pages = {1931},
  publisher = {Springer Science and Business Media LLC},
  doi = {10.1038/s41467-021-22072-9},
  url = {https://doi.org/10.1038/s41467-021-22072-9}
}
```

## What the tool deliberately does not do

It does not fetch paywalled PDFs, and it does not look for them anywhere unofficial. The two
hydrovoltaic papers above need institutional access, remote-access login, or an author request; the
library says so and stops there.
