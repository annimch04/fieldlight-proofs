# Fieldlight Corpus Manifest v1

This document defines `fieldlight-corpus-manifest-v1`, an immutable inventory of every tracked file in a pinned Git repository snapshot.

The corpus manifest complements the article-level proof-of-work format in `SPEC.md`. It does not replace or silently revise that format.

## Claims

A valid corpus manifest establishes:

1. the exact Git repository, commit, and tree being described;
2. the exact bytes, byte length, Git blob object, and portable SHA-256 digest of every tracked file;
3. a deterministic inventory of human-readable artifact classes;
4. normalized-text continuity for authored Markdown in addition to exact-byte identity; and
5. a single immutable manifest file whose SHA-256 can later be signed or externally timestamped.

It does not establish legal authorship, original creation time, or exclusive ownership by itself.

## Inclusion Rule

The v1 inclusion rule is:

```text
all_tracked_blob_files
```

Every blob returned by `git ls-tree -r <commit>` must appear exactly once. Directories, submodules, working-tree changes, ignored files, and untracked files are not included.

The repository commit is part of the manifest. Regenerating a snapshot from the same commit and configuration must produce identical manifest bytes.

## Artifact Classes

Each tracked file is assigned one class:

- `authored_work`
- `derivative`
- `public_archive`
- `repository_documentation`
- `tooling`
- `metadata`

Classification describes the file's role. It does not change whether the file is included or hashed.

## Artifact Record

Every artifact records:

```json
{
  "artifact_class": "authored_work",
  "git_blob_oid": "...",
  "media_type": "text/markdown",
  "path": "edge-infrastructure-and-safety/the-right-to-local-intelligence.md",
  "raw_sha256": "...",
  "size_bytes": 0,
  "source_url": "https://github.com/..."
}
```

`raw_sha256` is computed over the exact Git blob bytes. It is the primary portable integrity digest for every file, including binary files.

Authored Markdown additionally records:

```json
{
  "canonical_text_sha256": "...",
  "metadata": {
    "author": "Anni McHenry",
    "status": "Published",
    "title": "The Right to Local Intelligence"
  },
  "reading_url": "https://fieldlight.com/writing/the-right-to-local-intelligence/"
}
```

`canonical_text_sha256` uses the text normalization rules in `SPEC.md`. It permits continuity checks across line-ending and insignificant trailing-whitespace changes. It does not replace `raw_sha256`.

`reading_url` is optional. A source artifact without a dedicated fieldlight.com surface retains its immutable GitHub `source_url`.

## Serialization and Manifest Digest

The reference writer serializes `manifest.json` as:

- UTF-8;
- JSON object keys sorted lexicographically;
- two-space indentation;
- non-ASCII characters preserved as UTF-8; and
- exactly one trailing LF.

The manifest contains no self-hash and no anchor data. `manifest.sha256` contains:

```text
<sha256-of-exact-manifest.json-bytes>  manifest.json
```

This avoids self-reference and makes the published manifest bytes the canonical object.

## Snapshot Chain

The first corpus snapshot sets:

```json
{
  "previous_manifest_sha256": null
}
```

Each later snapshot records the SHA-256 of the preceding immutable `manifest.json`. Prior snapshot directories must not be rewritten.

## Verification

Structural verification checks:

- deterministic manifest serialization;
- the `manifest.sha256` sidecar;
- protocol and allowed fields;
- sorted and unique artifact paths;
- digest and object-ID syntax; and
- summary counts.

Full source verification additionally checks:

- the pinned commit and tree;
- exact equality between Git tree paths and manifest paths;
- Git blob IDs and byte lengths;
- every raw SHA-256; and
- normalized text hashes where present.

## External Timestamp and Bitcoin Receipts

Timestamp or blockchain evidence must never be inserted into `manifest.json`.

A detached receipt references the immutable manifest digest:

```json
{
  "protocol": "fieldlight-anchor-receipt-v1",
  "manifest_sha256": "...",
  "method": "opentimestamps",
  "proof_path": "manifest.ots"
}
```

A future direct Bitcoin receipt may instead record the OP_RETURN payload, transaction ID, block height, and block hash. Updating or supplementing a detached receipt never changes the anchored manifest digest.
