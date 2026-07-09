# Fieldlight Proofs

A small proof-of-work and Bitcoin anchoring ritual for published Fieldlight artifacts.

Fieldlight Proofs turns a public artifact into a verifiable record:

```text
article -> canonical bytes -> article_sha256
article_sha256 + nonce -> proof_sha256 with leading zeros
proof records -> manifest.json
manifest_sha256 -> Bitcoin OP_RETURN payload
```

The tool does not hold keys, sign transactions, or broadcast Bitcoin payments. It produces deterministic proof records and the compact `OP_RETURN` text you can anchor with the wallet or node software you already trust.

## Why This Exists

Fieldlight has writing, reading surfaces, images, recordings, protocols, and repositories that should be able to carry a public record without turning creative work into paperwork hell.

The practical rule:

> Hash artifacts when they become public or canonical enough to cite.

For the broader migration and recording process, start here:

- [Public Artifact Process](docs/public-artifact-process.md)
- [Reorientation Note](docs/reorientation-note.md)
- [Artifact Entry Example](examples/artifact-entry-example.json)

## Install for local use

This project uses only the Python standard library.

```bash
python3 -m fieldlight_proofs --help
```

For a shorter command while developing:

```bash
python3 -m pip install -e .
fieldlight-proof --help
```

## Mine a Proof

Start with a small difficulty while testing:

```bash
python3 -m fieldlight_proofs mine examples/article.md \
  --url https://fieldlight.com/example \
  --title "Example Fieldlight Article" \
  --zeros 5 \
  --manifest proofs/manifest-example.json
```

The result is a manifest containing the article hash, nonce, proof hash, and enough metadata for someone else to verify it later.

## Verify

```bash
python3 -m fieldlight_proofs verify proofs/manifest-example.json
```

If the manifest references local source paths, verification recomputes the article hashes too. If it does not, verification still checks every proof hash and the manifest hash.

## Print the Bitcoin Payload

```bash
python3 -m fieldlight_proofs opreturn proofs/manifest-example.json
```

The payload looks like:

```text
fieldlight:v1:<manifest_sha256>
```

That compact string is what you anchor in an `OP_RETURN` output.

## Protocol

The exact hashing, canonicalization, manifest format, and verification rules are described in [SPEC.md](SPEC.md).

## Public Workflow

The normal Fieldlight publishing chain is:

```text
source writing
  -> fieldlight.com reading surface
  -> author recording
  -> public audio derivative
  -> hashes
  -> manifest entry
  -> manifest hash
  -> optional Bitcoin anchor
```

The Bitcoin anchor is batch-oriented. Hash each artifact locally, update the manifest, then periodically anchor the manifest hash.

## Difficulty

Expected work grows by 16x for every additional leading hex zero:

```text
8 leading hex zeros  ~= 2^32 tries
9 leading hex zeros  ~= 2^36 tries
10 leading hex zeros ~= 2^40 tries
```

Use low values for tests and ordinary batches. Save high values for pieces where the burn itself is part of the work.
