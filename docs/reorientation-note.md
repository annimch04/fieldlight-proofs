# Reorientation Note

Fieldlight Proofs is the provenance and publication-memory layer for Fieldlight artifacts.

Use this note to reorient quickly.

## Current Frame

Fieldlight work now moves through several public surfaces:

- `public-writing`: versioned source for essays, protocols, fiction, and author notes.
- `fieldlight.com`: public reading surface.
- audio recordings: author-read versions of selected pieces.
- `fieldlight-proofs`: hashes, manifests, proof-of-work records, and optional Bitcoin anchors.

The purpose is not just archival neatness. It is authorship continuity.

Fieldlight treats public artifacts as traceable outputs: writing, images, audio, protocols, and reading surfaces should be able to carry their source path, public URL, hash, derivative relationships, and anchor status.

## Vocabulary

- **Artifact**: A public or canonical file worth preserving as part of the record.
- **Source artifact**: The primary source file, usually Markdown.
- **Derivative**: A public file derived from a source artifact, such as audio, image, share card, transcript, or HTML page.
- **Manifest**: A JSON record of artifacts and hashes.
- **Manifest hash**: The SHA-256 digest of the manifest, suitable for external anchoring.
- **Bitcoin anchor**: An optional OP_RETURN record containing the manifest hash.
- **Reading surface**: The fieldlight.com page where a public artifact is presented to readers.

## Working Rule

Do not overburden creation.

Hash when something becomes public, cited, recorded, or canonical enough to preserve.

## Current Priority

The next practical milestone is author-read audio:

1. record three pieces without overthinking;
2. export public audio derivatives;
3. add audio entries to the relevant artifact records;
4. publish audio links on fieldlight.com;
5. update and verify the manifest;
6. decide whether the batch is ready for Bitcoin anchoring.

## Important Boundary

A hash proves byte continuity. It does not, by itself, prove legal authorship or the meaning of the work.

Fieldlight uses hashes as one layer in a larger authorship system that also includes Git history, publication records, local custody, public context, and explicit attribution.
