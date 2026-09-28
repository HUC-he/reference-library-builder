# Library Layout

Read this file when deciding folder structure, file names, or index columns.

## Folder contract

```text
文献库/
|-- index.csv                 machine readable status, one row per reference
|-- index.md                  the same, readable at a glance
|-- library.ris               all references in one import file
|-- library.bib               all references in one BibTeX file
|-- cite/                     one ris, enw, and bib file per reference
|-- pdf/                      open-access PDFs, one file per reference
`-- meta/
    `-- <key>.json            the Crossref record plus the resolved open-access location
```

One folder per review, named for the review, not per topic. A library that mixes two papers'
references produces two papers with the wrong citations.

## File naming

PDF and citation files share one key: `first-author-family` + `year` + a short slug of the title,
lower case, hyphens, no punctuation. Long titles are cut at the slug boundary rather than mid-word.

Examples: `guo-2021-moisture-electricity-wood.pdf`, `li-2023-hydrovoltaic-chiral.pdf`.

The key is stable: re-running the same DOI produces the same name, so an import does not duplicate
entries in Zotero or EndNote.

## Index columns

| Column | Meaning |
|---|---|
| `key` | the shared file key |
| `doi` | normalised DOI |
| `year` | publication year from Crossref |
| `first_author` | family name of the first author |
| `title` | full title |
| `journal` | container title |
| `oa_status` | `open`, `manual`, or `error` |
| `pdf` | relative path, or empty for `manual` |
| `verified` | `yes`, `no`, or `n/a` before verification runs |

Read `oa_status` before anything else. `manual` means the author must supply a PDF; it is not a
failure of the workflow, and pretending otherwise hides the real gap in the library.

## Deduplication

Two DOIs are the same reference when they match after normalisation. Two entries are likely the same
paper when the first author family name, the year, and the first four significant title words all
match; report those as a probable duplicate and let the author decide. Never delete a reference
automatically: a duplicate costs a second glance, a silently removed reference costs a citation.

## Handing the library on

`index.csv` is the handoff artefact. A citation-adding or reference-verifying step should read it and
respect the `verified` column: an entry marked `no` after verification has been checked and failed,
which is different from an entry never checked.
