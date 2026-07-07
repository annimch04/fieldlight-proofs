# Fieldlight Proofs v1

This document defines the `fieldlight-proof-v1` manifest and proof format.

## Goals

- Make a published article independently hashable.
- Attach a configurable proof-of-work to that article.
- Batch many article proofs into one manifest.
- Anchor the manifest with a compact Bitcoin `OP_RETURN` payload.

## Non-Goals

- Storing complete articles on Bitcoin.
- Managing Bitcoin private keys.
- Broadcasting transactions.
- Proving authorship by itself. A proof establishes existence of specific bytes before an anchor time, not legal authorship.

## Canonical Article Bytes

For v1, canonicalization is intentionally simple and file-oriented:

1. Read the source file as bytes.
2. Normalize line endings by replacing CRLF and CR with LF.
3. Remove trailing ASCII spaces and tabs from each line.
4. Strip leading and trailing blank lines.
5. Ensure the result ends with exactly one LF byte.
6. Hash the resulting bytes with SHA-256.

This produces `canonical_sha256`.

URLs are metadata in v1. They are not fetched during verification unless a future tool explicitly adds URL retrieval.

## Proof Payload

Each article proof hashes this UTF-8 payload:

```text
fieldlight-proof-v1\n
url:<url>\n
title:<title>\n
canonical_sha256:<canonical_sha256>\n
zeros:<zeros>\n
nonce:<nonce>\n
```

The `proof_sha256` is the SHA-256 hex digest of that payload.

A proof is valid when `proof_sha256` starts with `zeros` ASCII `0` characters.

## Manifest

A manifest is JSON with sorted keys and two-space indentation when written by the reference tool.

Required top-level fields:

```json
{
  "protocol": "fieldlight-proof-v1",
  "created_at": "2026-07-07T00:00:00Z",
  "site": "https://fieldlight.com",
  "difficulty": {
    "algorithm": "sha256",
    "target": "leading_hex_zeros",
    "zeros": 8
  },
  "articles": [],
  "manifest_sha256": "..."
}
```

Each article has:

```json
{
  "url": "https://fieldlight.com/example",
  "title": "Example",
  "source_path": "examples/article.md",
  "canonical_sha256": "...",
  "zeros": 8,
  "nonce": 123,
  "proof_sha256": "..."
}
```

`source_path` is optional but recommended for local verification.

## Manifest Hash

`manifest_sha256` is computed over the manifest JSON after temporarily setting `manifest_sha256` to `null`, serializing with sorted keys, two-space indentation, and a trailing LF.

## Bitcoin Anchor

The v1 Bitcoin anchor payload is:

```text
fieldlight:v1:<manifest_sha256>
```

The transaction ID, block height, and block hash can be added to the manifest later under:

```json
{
  "bitcoin_anchor": {
    "op_return": "fieldlight:v1:...",
    "txid": "...",
    "block_height": 0,
    "block_hash": "..."
  }
}
```

