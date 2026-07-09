# Fieldlight Public Artifact Process

Fieldlight Proofs is the public record process for work that moves from private creation into public memory.

It exists for two reasons:

1. To make published Fieldlight artifacts independently verifiable.
2. To give humans and AI collaborators a fast way to reorient to a project without flattening its history.

This is not a claim that a hash proves meaning, authorship, or ownership by itself. A hash proves that a specific set of bytes existed in a specific form. Fieldlight uses that proof as part of a larger authorship trail: source files, publication URLs, recordings, images, manifests, Git history, and optional Bitcoin anchoring.

## Core Principle

Every public artifact should be able to answer five questions:

- What is this?
- Where is its source?
- Where is its public surface?
- What exact bytes were published or released?
- What later artifacts are derived from it?

The process is intentionally boring at the cryptographic layer and expressive at the human layer.

## Artifact Chain

```text
source writing
  -> reading surface
  -> author recording
  -> public audio derivative
  -> hashes
  -> manifest entry
  -> manifest hash
  -> optional Bitcoin anchor
```

The local rule is simple:

> Hash artifacts when they become public or canonical enough to cite.

Do not interrupt drafting, editing, or recording flow just to hash temporary work.

## What Gets Hashed

Hash public/canonical artifacts, not every scratch file.

Recommended:

- Markdown source in `public-writing`
- fieldlight.com reading page source or published HTML snapshot when available
- featured image or share card
- public author-read audio derivative
- proof manifest

Optional:

- raw audio file, if the raw file is being preserved as part of the archive
- transcript file
- editing notes or take log
- cover image or social card

Not recommended:

- every failed take
- temporary exports
- private source material not intended to be public
- sensitive local logs

## Writing and Migration Workflow

1. Move or create the public source in the writing repository.
2. Publish the reading surface on fieldlight.com.
3. Confirm the title, slug, source path, and public URL.
4. Generate a proof record for the source artifact.
5. Add related files, if any, as supplemental artifact hashes.
6. Update the manifest.
7. Verify the manifest.
8. Optionally anchor the manifest hash through Bitcoin.

## Recording Workflow

For author-read recordings:

1. Record without fussing.
2. Save the raw file locally with a clear date/title name.
3. Export a public derivative, usually `.mp3` or `.m4a`.
4. Store or publish the public derivative wherever the site can reference it.
5. Hash the public derivative.
6. Add the audio hash to the artifact entry for the writing piece.
7. Add the audio link to the fieldlight.com reading page.

Suggested naming:

```text
2026-07-09_terms-of-a-future_raw.wav
terms-of-a-future-i-can-live-in_author-read.mp3
```

## Manifest Batching

Fieldlight Proofs should not require a Bitcoin transaction for every article or recording.

The normal pattern is:

```text
hash each artifact locally
batch entries into a manifest
hash the manifest
anchor the manifest hash periodically
```

This keeps the creative process lightweight while preserving a durable public chain.

## Bitcoin Anchor

The v1 anchor payload is compact:

```text
fieldlight:v1:<manifest_sha256>
```

The manifest can later record the Bitcoin transaction ID, block height, and block hash.

## Reorientation Use

This repo is also a reorientation surface for AI collaborators.

When reorienting Codex, ChatGPT, or another assistant to Fieldlight artifact work, start here:

- Read `README.md` for the tool purpose.
- Read `SPEC.md` for the proof format.
- Read this file for the public artifact workflow.
- Read `docs/reorientation-note.md` for the current project frame.
- Inspect the relevant manifest and source files before making changes.

The goal is continuity without asking the user to restate the whole project every time.
