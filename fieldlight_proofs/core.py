from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROTOCOL = "fieldlight-proof-v1"
DEFAULT_SITE = "https://fieldlight.com"


@dataclass(frozen=True)
class ArticleProof:
    url: str
    title: str
    source_path: str | None
    canonical_sha256: str
    zeros: int
    nonce: int
    proof_sha256: str

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "canonical_sha256": self.canonical_sha256,
            "nonce": self.nonce,
            "proof_sha256": self.proof_sha256,
            "title": self.title,
            "url": self.url,
            "zeros": self.zeros,
        }
        if self.source_path:
            data["source_path"] = self.source_path
        return data


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonicalize_bytes(raw: bytes) -> bytes:
    text = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    lines = [line.rstrip(b" \t") for line in text.split(b"\n")]
    while lines and lines[0] == b"":
        lines.pop(0)
    while lines and lines[-1] == b"":
        lines.pop()
    return b"\n".join(lines) + b"\n"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_file_sha256(path: Path) -> str:
    return sha256_hex(canonicalize_bytes(path.read_bytes()))


def proof_payload(url: str, title: str, canonical_sha256: str, zeros: int, nonce: int) -> bytes:
    return (
        f"{PROTOCOL}\n"
        f"url:{url}\n"
        f"title:{title}\n"
        f"canonical_sha256:{canonical_sha256}\n"
        f"zeros:{zeros}\n"
        f"nonce:{nonce}\n"
    ).encode("utf-8")


def proof_hash(url: str, title: str, canonical_sha256: str, zeros: int, nonce: int) -> str:
    return sha256_hex(proof_payload(url, title, canonical_sha256, zeros, nonce))


def mine_proof(
    path: Path,
    url: str,
    title: str,
    zeros: int,
    start_nonce: int = 0,
    source_path: str | None = None,
) -> ArticleProof:
    if zeros < 0:
        raise ValueError("zeros must be non-negative")

    canonical_sha256 = canonical_file_sha256(path)
    target = "0" * zeros
    nonce = start_nonce
    while True:
        digest = proof_hash(url, title, canonical_sha256, zeros, nonce)
        if digest.startswith(target):
            return ArticleProof(
                url=url,
                title=title,
                source_path=source_path,
                canonical_sha256=canonical_sha256,
                zeros=zeros,
                nonce=nonce,
                proof_sha256=digest,
            )
        nonce += 1


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    copy = dict(manifest)
    copy["manifest_sha256"] = None
    return (json.dumps(copy, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compute_manifest_sha256(manifest: dict[str, Any]) -> str:
    return sha256_hex(manifest_bytes(manifest))


def build_manifest(
    articles: list[ArticleProof],
    zeros: int,
    site: str = DEFAULT_SITE,
    created_at: str | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "articles": [article.to_json() for article in articles],
        "created_at": created_at or utc_now(),
        "difficulty": {
            "algorithm": "sha256",
            "target": "leading_hex_zeros",
            "zeros": zeros,
        },
        "manifest_sha256": None,
        "protocol": PROTOCOL,
        "site": site,
    }
    manifest["manifest_sha256"] = compute_manifest_sha256(manifest)
    return manifest


def read_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def opreturn_payload(manifest: dict[str, Any]) -> str:
    digest = manifest.get("manifest_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("manifest_sha256 must be a 64-character hex string")
    return f"fieldlight:v1:{digest}"


def verify_manifest(manifest: dict[str, Any], base_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    if manifest.get("protocol") != PROTOCOL:
        errors.append(f"unsupported protocol: {manifest.get('protocol')}")

    expected_manifest_hash = compute_manifest_sha256(manifest)
    if manifest.get("manifest_sha256") != expected_manifest_hash:
        errors.append("manifest_sha256 does not match manifest contents")

    articles = manifest.get("articles")
    if not isinstance(articles, list):
        return errors + ["articles must be a list"]

    for index, article in enumerate(articles):
        prefix = f"articles[{index}]"
        try:
            url = article["url"]
            title = article["title"]
            canonical_sha256 = article["canonical_sha256"]
            zeros = int(article["zeros"])
            nonce = int(article["nonce"])
            proof_sha256 = article["proof_sha256"]
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{prefix} has invalid or missing fields: {exc}")
            continue

        expected_proof = proof_hash(url, title, canonical_sha256, zeros, nonce)
        if proof_sha256 != expected_proof:
            errors.append(f"{prefix}.proof_sha256 does not match proof payload")
        if not proof_sha256.startswith("0" * zeros):
            errors.append(f"{prefix}.proof_sha256 does not satisfy difficulty")

        source_path = article.get("source_path")
        if source_path and base_dir:
            source = (base_dir / source_path).resolve()
            if not source.exists():
                errors.append(f"{prefix}.source_path does not exist: {source_path}")
            else:
                actual = canonical_file_sha256(source)
                if actual != canonical_sha256:
                    errors.append(f"{prefix}.canonical_sha256 does not match source_path")

    return errors

