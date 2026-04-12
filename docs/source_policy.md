# Source Policy

## Goals

The project is passage-grounded and evidence-first. Every passage record must retain source
metadata, and the repository should prefer redistributable text sources whenever possible.

## Current source scope

### Canonical ingest target

- `wikisource_ross_1908`
- Book II URL:
  `https://en.wikisource.org/w/index.php?title=Nicomachean_Ethics_(Ross)/Book_Two&oldid=11905514`
- Book III URL:
  `https://en.wikisource.org/w/index.php?title=Nicomachean_Ethics_(Ross)/Book_Three&oldid=14820856`
- Translator: W. D. Ross
- Role: preferred canonical ingest target for the currently implemented books

Rationale:

- the underlying Ross translation is public-domain
- the pages expose stable section headings (`Part n`)
- the fixed `oldid` URLs make segmentation reproducible

### Verification source

- `mit_archive_ross`
- Book II URL: `https://classics.mit.edu/Aristotle/nicomachaen.2.ii.html`
- Book III URL: `https://classics.mit.edu/Aristotle/nicomachaen.3.iii.html`
- Translator: W. D. Ross
- Role: reference and verification source

Rationale:

- the user explicitly supplied MIT as the reference source
- it is useful for cross-checking wording and section boundaries in the implemented books
- the site presentation carries an explicit copyright notice, so it is not treated as the
  canonical committed raw corpus

## Repository commitment policy

- Do commit source metadata and derived structured data.
- Do commit stable passage exports when they are derived from approved sources.
- Do not commit MIT HTML.
- Do not assume downloaded HTML is safe to redistribute just because the underlying
  translation is public-domain.
- Keep `data/raw/` local and ignored until a clearly redistributable raw-text policy is
  confirmed.

## Practical implication for the current tranche

The Book II MVP writes the committed derived artifact:

- `data/interim/book2_passages.jsonl`

The Book III foundation tranche now also writes:

- `data/interim/book3_wikisource_ross_1908_normalized.json`
- `data/interim/book3_mit_archive_ross_normalized.json`
- `data/interim/book3_passages.jsonl`

The pipeline can still fetch live sources or consume a local dropped-in source file without
changing the architecture.

## Promotion rule for future canonical raw text

Raw Book II text may become a committed canonical corpus only if:

1. the repository can identify a redistributable source or transcription policy clearly
   enough to commit it confidently, and
2. the committed representation excludes site-specific presentation markup.
