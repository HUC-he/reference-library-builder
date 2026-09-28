#!/usr/bin/env python3
"""Build and verify a review's reference library from DOIs.

Metadata comes from Crossref, open-access PDFs from Unpaywall, citation files are written locally in
RIS, EndNote ENW, and BibTeX. Nothing here bypasses a paywall: a reference with no legal open copy is
recorded as `manual` and left to the author's own access.

Commands:
    build   resolve DOIs, write citation files, optionally download open-access PDFs
    verify  check that each downloaded PDF really is the reference it claims to be
    index   rebuild index.csv and index.md from what is already in the folder
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import ssl
import sys
import time
import unicodedata
from pathlib import Path
from urllib import error, parse, request

CROSSREF = "https://api.crossref.org/works/"
UNPAYWALL = "https://api.unpaywall.org/v2/"
USER_AGENT = "reference-library-builder/1.0 (mailto:{email})"
DEFAULT_SLEEP = 0.5
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\"'<>)\],;]+")
INDEX_COLUMNS = [
    "key", "doi", "year", "first_author", "title",
    "journal", "oa_status", "pdf", "verified",
]
RIS_TYPE = {
    "journal-article": "JOUR",
    "book-chapter": "CHAP",
    "proceedings-article": "CPAPER",
    "posted-content": "UNPB",
    "book": "BOOK",
    "report": "RPRT",
}
ENW_TYPE = {
    "journal-article": "Journal Article",
    "book-chapter": "Book Section",
    "proceedings-article": "Conference Paper",
    "posted-content": "Preprint",
    "book": "Book",
    "report": "Report",
}


class RefError(Exception):
    """User-facing failure."""


# ------------------------------------------------------------------ text utils


def normalise_doi(raw: str) -> str:
    doi = (raw or "").strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
    doi = doi.strip().strip(".,;:")
    return doi.lower()


def extract_dois(text: str) -> list[str]:
    found: list[str] = []
    for match in DOI_PATTERN.finditer(text or ""):
        doi = normalise_doi(match.group(0))
        if doi and doi not in found:
            found.append(doi)
    return found


def slugify(text: str, max_length: int = 48) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    )
    ascii_text = ascii_text.lower()
    words = re.findall(r"[a-z0-9]+", ascii_text)
    slug = ""
    for word in words:
        candidate = f"{slug}-{word}" if slug else word
        if len(candidate) > max_length:
            break
        slug = candidate
    return slug or "reference"


def significant_words(title: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[a-z0-9]{4,}", (title or "").lower())
    stop = {"with", "from", "that", "this", "using", "into", "their", "these", "based"}
    return [word for word in words if word not in stop][:limit]


# ------------------------------------------------------------------ http


def _fetch(url: str, email: str, timeout: int, accept: str):
    req = request.Request(
        url, headers={"User-Agent": USER_AGENT.format(email=email or "unknown"), "Accept": accept}
    )
    try:
        with request.urlopen(req, timeout=timeout, context=_ssl_context()) as response:
            return response.read(), response.headers.get("Content-Type", "")
    except error.HTTPError as exc:
        raise RefError(f"HTTP {exc.code} for {url}") from exc
    except error.URLError as exc:
        raise RefError(f"network error for {url}: {exc.reason}") from exc


def _ssl_context() -> ssl.SSLContext:
    """Use certifi's CA bundle when the interpreter has no usable system one.

    A python.org build on macOS ships without a linked CA store, which makes every HTTPS call fail
    with CERTIFICATE_VERIFY_FAILED. certifi is usually present because requests depends on it.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch_json(url: str, email: str, timeout: int = 25) -> dict:
    body, _ = _fetch(url, email, timeout, "application/json")
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RefError(f"invalid JSON from {url}") from exc


# ------------------------------------------------------------------ metadata


def _first_year(message: dict) -> int | None:
    for field in ("published-print", "published-online", "published", "issued", "created"):
        parts = (message.get(field) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return None


def parse_crossref(record: dict) -> dict:
    message = record.get("message") or {}
    authors = []
    for author in message.get("author") or []:
        family = (author.get("family") or "").strip()
        given = (author.get("given") or "").strip()
        if family or given:
            authors.append({"family": family, "given": given,
                            "literal": (author.get("name") or "").strip()})
    return {
        "doi": normalise_doi(message.get("DOI", "")),
        "title": (message.get("title") or [""])[0].strip(),
        "subtitle": (message.get("subtitle") or [""])[0].strip() if message.get("subtitle") else "",
        "container": (message.get("container-title") or [""])[0].strip()
        if message.get("container-title") else "",
        "publisher": (message.get("publisher") or "").strip(),
        "year": _first_year(message),
        "volume": (message.get("volume") or "").strip(),
        "issue": (message.get("issue") or "").strip(),
        "page": (message.get("page") or "").strip(),
        "article_number": (message.get("article-number") or "").strip(),
        "type": (message.get("type") or "").strip(),
        "authors": authors,
        "url": (message.get("URL") or "").strip()
        or (f"https://doi.org/{normalise_doi(message.get('DOI', ''))}"),
    }


def first_author_family(meta: dict) -> str:
    for author in meta.get("authors") or []:
        if author.get("family"):
            return author["family"]
    return "unknown"


def key_for(meta: dict) -> str:
    year = meta.get("year") or "n.d."
    family = slugify(first_author_family(meta), 20)
    return f"{family}-{year}-{slugify(meta.get('title', ''), 44)}"


def author_string(meta: dict, separator: str = " and ") -> str:
    parts = []
    for author in meta.get("authors") or []:
        if author.get("family"):
            entry = author["family"]
            if author.get("given"):
                entry += f", {author['given']}"
        else:
            entry = author.get("literal") or ""
        if entry:
            parts.append(entry)
    return separator.join(parts)


# ------------------------------------------------------------------ citations


def to_ris(meta: dict) -> str:
    lines = [f"TY  - {RIS_TYPE.get(meta.get('type'), 'JOUR')}"]
    for author in meta.get("authors") or []:
        if author.get("family"):
            name = author["family"] + (f", {author['given']}" if author.get("given") else "")
        else:
            name = author.get("literal") or ""
        if name:
            lines.append(f"AU  - {name}")
    lines.append(f"TI  - {meta.get('title', '')}")
    if meta.get("container"):
        lines.append(f"JO  - {meta['container']}")
    if meta.get("year"):
        lines.append(f"PY  - {meta['year']}")
    if meta.get("volume"):
        lines.append(f"VL  - {meta['volume']}")
    if meta.get("issue"):
        lines.append(f"IS  - {meta['issue']}")
    if meta.get("page"):
        start, _, end = meta["page"].partition("-")
        lines.append(f"SP  - {start.strip()}")
        if end.strip():
            lines.append(f"EP  - {end.strip()}")
    elif meta.get("article_number"):
        lines.append(f"SP  - {meta['article_number']}")
    if meta.get("doi"):
        lines.append(f"DO  - {meta['doi']}")
    if meta.get("url"):
        lines.append(f"UR  - {meta['url']}")
    lines.append("ER  - ")
    return "\n".join(lines) + "\n"


def to_enw(meta: dict) -> str:
    lines = [f"%0 {ENW_TYPE.get(meta.get('type'), 'Journal Article')}"]
    for author in meta.get("authors") or []:
        if author.get("family"):
            name = author["family"] + (f", {author['given']}" if author.get("given") else "")
        else:
            name = author.get("literal") or ""
        if name:
            lines.append(f"%A {name}")
    lines.append(f"%T {meta.get('title', '')}")
    if meta.get("container"):
        lines.append(f"%J {meta['container']}")
    if meta.get("year"):
        lines.append(f"%D {meta['year']}")
    if meta.get("volume"):
        lines.append(f"%V {meta['volume']}")
    if meta.get("issue"):
        lines.append(f"%N {meta['issue']}")
    if meta.get("page"):
        lines.append(f"%P {meta['page']}")
    elif meta.get("article_number"):
        lines.append(f"%P {meta['article_number']}")
    if meta.get("publisher"):
        lines.append(f"%I {meta['publisher']}")
    if meta.get("doi"):
        lines.append(f"%R {meta['doi']}")
    if meta.get("url"):
        lines.append(f"%U {meta['url']}")
    return "\n".join(lines) + "\n"


def to_bibtex(meta: dict, key: str) -> str:
    entry_type = "article" if meta.get("type") in ("journal-article", "posted-content") else "inbook"
    if meta.get("type") == "proceedings-article":
        entry_type = "inproceedings"
    if meta.get("type") == "book":
        entry_type = "book"
    fields = [("author", author_string(meta)), ("title", meta.get("title", ""))]
    if meta.get("container"):
        fields.append(("journal" if entry_type == "article" else "booktitle", meta["container"]))
    if meta.get("year"):
        fields.append(("year", str(meta["year"])))
    if meta.get("volume"):
        fields.append(("volume", meta["volume"]))
    if meta.get("issue"):
        fields.append(("number", meta["issue"]))
    if meta.get("page"):
        fields.append(("pages", meta["page"].replace("-", "--")))
    elif meta.get("article_number"):
        fields.append(("pages", meta["article_number"]))
    if meta.get("publisher"):
        fields.append(("publisher", meta["publisher"]))
    if meta.get("doi"):
        fields.append(("doi", meta["doi"]))
    if meta.get("url"):
        fields.append(("url", meta["url"]))
    body = ",\n".join(f"  {name} = {{{value}}}" for name, value in fields if value)
    return f"@{entry_type}{{{key},\n{body}\n}}\n"


def matches_reference(text: str, doi: str, title: str, ratio: float = 0.6) -> bool:
    """True when the PDF text plausibly belongs to this reference."""
    haystack = re.sub(r"\s+", " ", (text or "").lower())
    if not haystack:
        return False
    if doi and normalise_doi(doi) in haystack.replace(" ", ""):
        return True
    words = significant_words(title)
    if not words:
        return False
    hits = sum(1 for word in words if word in haystack)
    return hits / len(words) >= ratio


# ------------------------------------------------------------------ open access


def find_open_access(doi: str, email: str, timeout: int = 25) -> dict | None:
    payload = fetch_json(
        f"{UNPAYWALL}{parse.quote(doi)}?email={parse.quote(email)}", email, timeout
    )
    if not payload.get("is_oa"):
        return None

    candidates: list[str] = []
    locations = []
    if payload.get("best_oa_location"):
        locations.append(payload["best_oa_location"])
    locations.extend(payload.get("oa_locations") or [])

    primary: dict = {}
    for location in locations:
        url = location.get("url_for_pdf") or location.get("url")
        if not url or url in candidates:
            continue
        candidates.append(url)
        if not primary:
            primary = location
    if not candidates:
        return None
    return {
        "url": candidates[0],
        "urls": candidates,
        "version": primary.get("version") or "unknown",
        "host_type": primary.get("host_type") or "unknown",
        "license": primary.get("license") or "",
    }


def download_pdf(urls: list[str], email: str, target: Path, timeout: int = 90) -> tuple[bool, str]:
    """Try each open-access URL; return (ok, reason).

    A publisher PDF that answers with an HTML consent page is a failure, not a download: the library
    records it as manual rather than storing a web page under a .pdf name.
    """
    last = "no candidate URL"
    for url in urls:
        for attempt in (1, 2):
            try:
                body, content_type = _fetch(url, email, timeout, "application/pdf,*/*")
            except RefError as exc:
                last = str(exc)
                if attempt == 1:
                    time.sleep(1.5)
                continue
            if body.startswith(b"%PDF"):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
                return True, url
            last = f"{content_type or 'unknown content type'} instead of a PDF at {url}"
            break
    return False, last


# ------------------------------------------------------------------ library io


def write_citation_files(meta: dict, key: str, outdir: Path, formats: list[str]) -> list[Path]:
    written = []
    cite_dir = outdir / "cite"
    cite_dir.mkdir(parents=True, exist_ok=True)
    if "ris" in formats:
        path = cite_dir / f"{key}.ris"
        path.write_text(to_ris(meta), encoding="utf-8")
        written.append(path)
    if "enw" in formats:
        path = cite_dir / f"{key}.enw"
        path.write_text(to_enw(meta), encoding="utf-8")
        written.append(path)
    if "bib" in formats:
        path = cite_dir / f"{key}.bib"
        path.write_text(to_bibtex(meta, key), encoding="utf-8")
        written.append(path)
    return written


def write_index(outdir: Path, rows: list[dict]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "index.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in INDEX_COLUMNS})

    lines = ["# Reference library", "",
             f"references: {len(rows)}  |  open: "
             f"{sum(1 for r in rows if r.get('oa_status') == 'open')}  |  manual: "
             f"{sum(1 for r in rows if r.get('oa_status') == 'manual')}  |  verified: "
             f"{sum(1 for r in rows if r.get('verified') == 'yes')}", "",
             "| key | year | first author | title | open access | verified |",
             "|---|---|---|---|---|---|"]
    for row in rows:
        title = (row.get("title") or "")[:70]
        lines.append(
            f"| {row.get('key','')} | {row.get('year','')} | {row.get('first_author','')} | "
            f"{title} | {row.get('oa_status','')} | {row.get('verified','')} |"
        )
    (outdir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_combined(outdir: Path, metas: list[dict], formats: list[str]) -> None:
    if "ris" in formats:
        (outdir / "library.ris").write_text(
            "".join(to_ris(meta) for meta in metas), encoding="utf-8"
        )
    if "bib" in formats:
        (outdir / "library.bib").write_text(
            "".join(to_bibtex(meta, key_for(meta)) for meta in metas), encoding="utf-8"
        )


def load_cached_meta(outdir: Path) -> dict[str, dict]:
    cache: dict[str, dict] = {}
    for path in sorted((outdir / "meta").glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        doi = payload.get("meta", {}).get("doi")
        if doi:
            cache[doi] = payload
    return cache


# ------------------------------------------------------------------ commands


def cmd_build(args: argparse.Namespace) -> int:
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "meta").mkdir(exist_ok=True)
    (outdir / "pdf").mkdir(exist_ok=True)
    formats = [item.strip() for item in args.formats.split(",") if item.strip()]

    raw_input = Path(args.input).read_text(encoding="utf-8") if args.input else ""
    if args.doi:
        raw_input += "\n" + "\n".join(args.doi)
    dois = extract_dois(raw_input)
    if not dois:
        raise RefError("no DOI found in the input")
    if args.pdf and not args.email:
        raise RefError("--pdf needs --email, because Unpaywall requires a contact address")

    cache = {} if args.refresh else load_cached_meta(outdir)
    rows: list[dict] = []
    metas: list[dict] = []

    for index, doi in enumerate(dois):
        if index and args.sleep:
            time.sleep(args.sleep)
        cached = cache.get(doi)
        if cached:
            meta = cached["meta"]
            oa = cached.get("open_access")
            print(f"[cached] {doi}")
        else:
            try:
                record = fetch_json(CROSSREF + parse.quote(doi), args.email)
                meta = parse_crossref(record)
            except RefError as exc:
                print(f"[error] {doi}: {exc}", file=sys.stderr)
                rows.append(
                    {
                        "key": f"unresolved-{slugify(doi, 40)}",
                        "doi": doi,
                        "year": "",
                        "first_author": "",
                        "title": "(metadata could not be resolved)",
                        "journal": "",
                        "oa_status": "error",
                        "pdf": "",
                        "verified": "n/a",
                    }
                )
                continue
            oa = None
            if args.pdf:
                try:
                    oa = find_open_access(doi, args.email)
                except RefError as exc:
                    print(f"  open-access lookup failed: {exc}", file=sys.stderr)
            print(f"[resolved] {doi} -> {meta.get('title', '')[:64]}")

        key = key_for(meta)
        metas.append(meta)
        write_citation_files(meta, key, outdir, formats)

        pdf_rel = ""
        status = "manual"
        if args.pdf:
            target = outdir / "pdf" / f"{key}.pdf"
            if target.exists() and not args.refresh:
                pdf_rel, status = str(target.relative_to(outdir)), "open"
            elif oa and oa.get("url"):
                if index and args.sleep:
                    time.sleep(args.sleep)
                ok, reason = download_pdf(oa.get("urls") or [oa["url"]], args.email, target)
                if ok:
                    pdf_rel, status = str(target.relative_to(outdir)), "open"
                    print(f"  pdf: {pdf_rel} ({oa.get('host_type')}, {oa.get('version')})")
                else:
                    print(f"  recorded as manual: {reason}", file=sys.stderr)

        (outdir / "meta" / f"{key}.json").write_text(
            json.dumps({"meta": meta, "open_access": oa}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rows.append(
            {
                "key": key,
                "doi": meta.get("doi", ""),
                "year": meta.get("year", ""),
                "first_author": first_author_family(meta),
                "title": meta.get("title", ""),
                "journal": meta.get("container", ""),
                "oa_status": status,
                "pdf": pdf_rel,
                "verified": "n/a" if status != "open" else "no",
            }
        )

    write_combined(outdir, metas, formats)
    write_index(outdir, rows)

    open_count = sum(1 for row in rows if row["oa_status"] == "open")
    print(f"\nlibrary at {outdir}: {len(rows)} references, {open_count} open PDF(s)")
    manual = [row for row in rows if row["oa_status"] == "manual"]
    if manual:
        print(f"{len(manual)} reference(s) need your own access:")
        for row in manual:
            print(f'  - {row["doi"]}  "{row["title"][:60]}"')
    print("next: python3 scripts/refs.py verify --dir " + str(outdir))
    return 0


def load_index(outdir: Path) -> list[dict]:
    path = outdir / "index.csv"
    if not path.exists():
        raise RefError(f"no index.csv in {outdir}; run build first")
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def pdf_text(path: Path, pages: int = 2) -> str:
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            return ""
    try:
        with fitz.open(path) as doc:
            return "\n".join(doc[i].get_text() for i in range(min(pages, len(doc))))
    except Exception:
        return ""


def cmd_verify(args: argparse.Namespace) -> int:
    outdir = Path(args.dir)
    rows = load_index(outdir)
    checked = mismatch = skipped = 0
    for row in rows:
        pdf = row.get("pdf") or ""
        if not pdf:
            row["verified"] = "n/a"
            continue
        path = outdir / pdf
        if not path.exists():
            row["verified"] = "no"
            mismatch += 1
            print(f"MISSING  {row['key']}: {pdf}")
            continue
        text = pdf_text(path)
        if not text:
            row["verified"] = "no"
            skipped += 1
            print(f"UNREADABLE {row['key']}: install pymupdf to verify PDF text")
            continue
        checked += 1
        if matches_reference(text, row.get("doi", ""), row.get("title", "")):
            row["verified"] = "yes"
            print(f"OK       {row['key']}")
        else:
            row["verified"] = "no"
            mismatch += 1
            print(f"WRONG FILE {row['key']}: text does not match "
                  f'"{row.get("title", "")[:50]}"')
    write_index(outdir, rows)
    print(f"\nchecked {checked}, mismatched {mismatch}, unverifiable {skipped}")
    return 1 if mismatch else 0


def cmd_index(args: argparse.Namespace) -> int:
    outdir = Path(args.dir)
    cache = load_cached_meta(outdir)
    if not cache:
        raise RefError(f"no metadata under {outdir}/meta; run build first")
    rows = []
    for payload in cache.values():
        meta = payload["meta"]
        key = key_for(meta)
        pdf = outdir / "pdf" / f"{key}.pdf"
        rows.append(
            {
                "key": key,
                "doi": meta.get("doi", ""),
                "year": meta.get("year", ""),
                "first_author": first_author_family(meta),
                "title": meta.get("title", ""),
                "journal": meta.get("container", ""),
                "oa_status": "open" if pdf.exists() else "manual",
                "pdf": str(pdf.relative_to(outdir)) if pdf.exists() else "",
                "verified": "no" if pdf.exists() else "n/a",
            }
        )
    rows.sort(key=lambda row: (row["first_author"], str(row["year"])))
    write_index(outdir, rows)
    print(f"index rewritten: {len(rows)} reference(s)")
    return 0


# ------------------------------------------------------------------ entry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and verify a reference library from DOIs.")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="resolve DOIs and write the library")
    build.add_argument("--input", help="file containing DOIs, one per line or in a citation dump")
    build.add_argument("--doi", action="append", help="a DOI, repeatable")
    build.add_argument("--out", default="文献库")
    build.add_argument("--email", help="contact email for Crossref and Unpaywall")
    build.add_argument("--pdf", action="store_true", help="download open-access PDFs")
    build.add_argument("--formats", default="ris,enw,bib")
    build.add_argument("--refresh", action="store_true", help="ignore the metadata cache")
    build.add_argument("--sleep", type=float, default=DEFAULT_SLEEP,
                       help=f"seconds between requests (default {DEFAULT_SLEEP})")
    build.set_defaults(func=cmd_build)

    verify = sub.add_parser("verify", help="check that each PDF is the right paper")
    verify.add_argument("--dir", required=True)
    verify.set_defaults(func=cmd_verify)

    index = sub.add_parser("index", help="rebuild index.csv and index.md")
    index.add_argument("--dir", required=True)
    index.set_defaults(func=cmd_index)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RefError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
