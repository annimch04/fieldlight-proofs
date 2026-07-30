from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .corpus import (
    build_corpus_manifest,
    load_corpus_config,
    verify_corpus_manifest,
    write_corpus_snapshot,
)
from .core import (
    DEFAULT_SITE,
    ArticleProof,
    build_manifest,
    mine_proof,
    opreturn_payload,
    read_manifest,
    verify_manifest,
    write_manifest,
)


def _relative_source_path(path: Path, manifest_path: Path) -> str:
    return os.path.relpath(path.resolve(), manifest_path.parent.resolve())


def command_mine(args: argparse.Namespace) -> int:
    article_path = Path(args.article)
    manifest_path = Path(args.manifest)
    source_path = None if args.no_source_path else _relative_source_path(article_path, manifest_path)
    proof = mine_proof(
        path=article_path,
        url=args.url,
        title=args.title,
        zeros=args.zeros,
        start_nonce=args.start_nonce,
        source_path=source_path,
    )

    articles: list[ArticleProof] = [proof]
    manifest = build_manifest(articles, zeros=args.zeros, site=args.site)
    write_manifest(manifest_path, manifest)

    print(f"wrote {manifest_path}")
    print(f"canonical_sha256: {proof.canonical_sha256}")
    print(f"nonce: {proof.nonce}")
    print(f"proof_sha256: {proof.proof_sha256}")
    print(f"manifest_sha256: {manifest['manifest_sha256']}")
    print(f"op_return: {opreturn_payload(manifest)}")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest = read_manifest(manifest_path)
    errors = verify_manifest(manifest, base_dir=manifest_path.parent)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"verified {manifest_path}")
    print(f"manifest_sha256: {manifest['manifest_sha256']}")
    return 0


def command_opreturn(args: argparse.Namespace) -> int:
    manifest = read_manifest(Path(args.manifest))
    print(opreturn_payload(manifest))
    return 0


def command_snapshot(args: argparse.Namespace) -> int:
    config = load_corpus_config(Path(args.config))
    manifest = build_corpus_manifest(
        repo=Path(args.repository),
        ref=args.ref,
        config=config,
        previous_manifest_sha256=args.previous_manifest_sha256,
    )
    manifest_path, digest = write_corpus_snapshot(Path(args.output), manifest)
    print(f"wrote {manifest_path}")
    print(f"tracked files: {manifest['summary']['tracked_file_count']}")
    print(f"authored works: {manifest['summary']['authored_work_count']}")
    print(f"reading surfaces: {manifest['summary']['reading_surface_count']}")
    print(f"manifest_sha256: {digest}")
    return 0


def command_verify_corpus(args: argparse.Namespace) -> int:
    source_root = Path(args.source_root) if args.source_root else None
    errors = verify_corpus_manifest(Path(args.manifest), source_root=source_root)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"verified {args.manifest}")
    if source_root:
        print(f"source commit verified against {source_root}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fieldlight-proof",
        description="Create and verify Fieldlight provenance and proof manifests.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    mine = subparsers.add_parser("mine", help="mine a proof for one article and write a manifest")
    mine.add_argument("article", help="local article file to canonicalize and hash")
    mine.add_argument("--url", required=True, help="published article URL")
    mine.add_argument("--title", required=True, help="article title")
    mine.add_argument("--zeros", type=int, default=5, help="leading hex zeros required")
    mine.add_argument("--manifest", default="proofs/manifest.json", help="manifest output path")
    mine.add_argument("--site", default=DEFAULT_SITE, help="site recorded in the manifest")
    mine.add_argument("--start-nonce", type=int, default=0, help="nonce to start searching from")
    mine.add_argument("--no-source-path", action="store_true", help="omit source_path from manifest")
    mine.set_defaults(func=command_mine)

    verify = subparsers.add_parser("verify", help="verify a manifest")
    verify.add_argument("manifest", help="manifest JSON path")
    verify.set_defaults(func=command_verify)

    opreturn = subparsers.add_parser("opreturn", help="print the Bitcoin OP_RETURN payload")
    opreturn.add_argument("manifest", help="manifest JSON path")
    opreturn.set_defaults(func=command_opreturn)

    snapshot = subparsers.add_parser(
        "snapshot",
        help="create an immutable manifest for every tracked file at a Git commit",
    )
    snapshot.add_argument("repository", help="local Git repository containing the source corpus")
    snapshot.add_argument("--ref", default="HEAD", help="commit or ref to snapshot")
    snapshot.add_argument("--config", required=True, help="corpus metadata and reading-URL policy")
    snapshot.add_argument("--output", required=True, help="new or existing snapshot output directory")
    snapshot.add_argument(
        "--previous-manifest-sha256",
        help="SHA-256 of the preceding immutable corpus manifest",
    )
    snapshot.set_defaults(func=command_snapshot)

    verify_corpus = subparsers.add_parser(
        "verify-corpus",
        help="verify a corpus manifest, checksum, and optionally its pinned Git source",
    )
    verify_corpus.add_argument("manifest", help="corpus manifest JSON path")
    verify_corpus.add_argument(
        "--source-root",
        help="local clone containing the source commit for full byte verification",
    )
    verify_corpus.set_defaults(func=command_verify_corpus)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
