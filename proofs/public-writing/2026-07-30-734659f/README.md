# Public Writing Corpus Snapshot

This directory is the first complete Fieldlight Proofs snapshot of Anni McHenry's `public-writing` repository.

- Source repository: `https://github.com/annimch04/public-writing`
- Source commit: `734659faf3c57ca2b70f24bada347613d4e1e7bf`
- Source tree: `738cda58b5b471836a0737a3ef8b9074fdcd617c`
- Tracked files: `97`
- Exact tracked bytes: `29,578,119`
- Authored works: `44`
- Fieldlight reading surfaces: `39`
- Manifest SHA-256: `6f5a9ad9f76e4633ef2a9d3a50556b91f3abe92d8425afa3fa5b6bebb7f1be90`
- OpenTimestamps proof: submitted July 31, 2026 at `00:17:32Z`
- OpenTimestamps status: pending Bitcoin confirmation
- Direct Bitcoin transaction: not created

`manifest.json` and `manifest.sha256` are immutable. Future timestamp and blockchain evidence must be stored as detached receipts referencing the manifest SHA-256.

The initial detached proof is `manifest.json.ots`. Its current SHA-256 is `a27f084a0bb4d9111d69853bc77ff7e64205c0111f1076a47c082bd0aee1ba2c`; `anchor-receipt.json` records its pending state and responding calendars. The proof file and receipt may be upgraded after a calendar publishes the commitment into Bitcoin. That upgrade does not modify the manifest or its hash.

Verify the complete snapshot against a local clone containing the source commit:

```bash
python3 -m fieldlight_proofs verify-corpus \
  proofs/public-writing/2026-07-30-734659f/manifest.json \
  --source-root /path/to/public-writing
```

Inspect or upgrade the detached timestamp with the official OpenTimestamps client:

```bash
ots info proofs/public-writing/2026-07-30-734659f/manifest.json.ots
ots upgrade proofs/public-writing/2026-07-30-734659f/manifest.json.ots
```
