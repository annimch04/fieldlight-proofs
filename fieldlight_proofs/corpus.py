from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .core import canonicalize_bytes, sha256_hex

CORPUS_PROTOCOL = "fieldlight-corpus-manifest-v1"
GENERATOR_VERSION = "0.2.0"
ARTIFACT_CLASSES = {
    "authored_work",
    "derivative",
    "metadata",
    "public_archive",
    "repository_documentation",
    "tooling",
}
TOP_LEVEL_FIELDS = {
    "artifacts",
    "generator",
    "identity",
    "protocol",
    "snapshot",
    "source",
    "summary",
}
ARTIFACT_FIELDS = {
    "artifact_class",
    "canonical_text_sha256",
    "git_blob_oid",
    "media_type",
    "metadata",
    "path",
    "raw_sha256",
    "reading_url",
    "size_bytes",
    "source_url",
}
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_GIT_OID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_DERIVATIVE_EXTENSIONS = {
    ".aac",
    ".flac",
    ".gif",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".svg",
    ".wav",
    ".webm",
    ".webp",
}
_METADATA_EXTENSIONS = {".csv", ".json", ".jsonl"}
_MEDIA_TYPES = {
    ".csv": "text/csv",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".m4a": "audio/mp4",
    ".md": "text/markdown",
    ".mjs": "text/javascript",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".py": "text/x-python",
    ".sh": "text/x-shellscript",
    ".svg": "image/svg+xml",
    ".wav": "audio/wav",
    ".webm": "video/webm",
    ".webp": "image/webp",
}


def _git(repo: Path, *args: str, text: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return result.stdout


def _git_text(repo: Path, *args: str) -> str:
    return str(_git(repo, *args, text=True)).strip()


def _manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _parse_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            parsed = json.loads(value)
            if isinstance(parsed, str):
                return parsed
        except json.JSONDecodeError:
            pass
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def parse_front_matter(raw: bytes) -> dict[str, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}

    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in {"author", "canonical_url", "status", "title"}:
            metadata[key] = _parse_scalar(value)
    return metadata


def _media_type(path: str) -> str:
    if Path(path).name == ".gitignore":
        return "text/plain"
    suffix = Path(path).suffix.lower()
    return _MEDIA_TYPES.get(suffix, "application/octet-stream")


def _artifact_class(path: str, metadata: dict[str, str]) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".md" and metadata.get("title"):
        return "authored_work"
    if path.startswith("archive/"):
        return "public_archive"
    if path.startswith(("tests/", "tools/")) or suffix in {".mjs", ".py", ".sh"}:
        return "tooling"
    if suffix in _DERIVATIVE_EXTENSIONS:
        return "derivative"
    if suffix in _METADATA_EXTENSIONS or Path(path).name == ".gitignore":
        return "metadata"
    if suffix == ".md":
        return "repository_documentation"
    return "metadata"


def _reading_url(path: str, metadata: dict[str, str], config: dict[str, Any]) -> str | None:
    if metadata.get("canonical_url"):
        return metadata["canonical_url"]

    overrides = config.get("reading_url_overrides", {})
    if path in overrides:
        override = overrides[path]
        return override if isinstance(override, str) else None

    template = config.get("default_reading_url_template")
    if not isinstance(template, str):
        return None
    return template.format(slug=Path(path).stem)


def _tree_entries(repo: Path, commit: str) -> list[tuple[str, str, int]]:
    raw = bytes(_git(repo, "ls-tree", "-r", "-z", "--long", commit))
    entries: list[tuple[str, str, int]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, encoded_path = record.split(b"\t", 1)
        _mode, object_type, oid, size = header.decode("ascii").split()
        if object_type != "blob":
            continue
        entries.append((encoded_path.decode("utf-8", "surrogateescape"), oid, int(size)))
    return sorted(entries)


def load_corpus_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {"author", "repository_url", "site"}
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"corpus config is missing required fields: {', '.join(missing)}")
    return config


def build_corpus_manifest(
    repo: Path,
    ref: str,
    config: dict[str, Any],
    previous_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    commit = _git_text(repo, "rev-parse", f"{ref}^{{commit}}")
    tree_oid = _git_text(repo, "rev-parse", f"{commit}^{{tree}}")
    commit_time = _git_text(repo, "show", "-s", "--format=%cI", commit)
    repository_url = str(config["repository_url"]).rstrip("/")
    default_author = str(config["author"])

    artifacts: list[dict[str, Any]] = []
    for path, oid, recorded_size in _tree_entries(repo, commit):
        raw = bytes(_git(repo, "cat-file", "blob", oid))
        if len(raw) != recorded_size:
            raise ValueError(f"Git reported the wrong byte size for {path}")

        front_matter = parse_front_matter(raw)
        artifact_class = _artifact_class(path, front_matter)
        artifact: dict[str, Any] = {
            "artifact_class": artifact_class,
            "git_blob_oid": oid,
            "media_type": _media_type(path),
            "path": path,
            "raw_sha256": sha256_hex(raw),
            "size_bytes": len(raw),
            "source_url": f"{repository_url}/blob/{commit}/{quote(path, safe='/')}",
        }

        if artifact_class == "authored_work":
            artifact["canonical_text_sha256"] = sha256_hex(canonicalize_bytes(raw))
            metadata = {
                "author": front_matter.get("author", default_author),
                "status": front_matter.get("status", ""),
                "title": front_matter["title"],
            }
            artifact["metadata"] = metadata
            reading_url = _reading_url(path, front_matter, config)
            if reading_url:
                artifact["reading_url"] = reading_url

        artifacts.append(artifact)

    class_counts = Counter(item["artifact_class"] for item in artifacts)
    reading_urls = {
        item["reading_url"]
        for item in artifacts
        if item["artifact_class"] == "authored_work" and "reading_url" in item
    }
    manifest: dict[str, Any] = {
        "artifacts": artifacts,
        "generator": {
            "name": "fieldlight-proofs",
            "version": GENERATOR_VERSION,
        },
        "identity": {
            "author": default_author,
            "site": config["site"],
        },
        "protocol": CORPUS_PROTOCOL,
        "snapshot": {
            "inclusion": "all_tracked_blob_files",
            "previous_manifest_sha256": previous_manifest_sha256,
        },
        "source": {
            "commit": commit,
            "commit_time": commit_time,
            "repository": repository_url,
            "tree_oid": tree_oid,
        },
        "summary": {
            "artifact_classes": dict(sorted(class_counts.items())),
            "authored_work_count": class_counts["authored_work"],
            "reading_surface_count": len(reading_urls),
            "tracked_file_count": len(artifacts),
            "tracked_size_bytes": sum(item["size_bytes"] for item in artifacts),
        },
    }
    return manifest


def write_corpus_snapshot(output_dir: Path, manifest: dict[str, Any]) -> tuple[Path, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    checksum_path = output_dir / "manifest.sha256"
    raw = _manifest_bytes(manifest)
    digest = hashlib.sha256(raw).hexdigest()
    checksum = f"{digest}  manifest.json\n"

    if manifest_path.exists() and manifest_path.read_bytes() != raw:
        raise FileExistsError(f"refusing to rewrite immutable snapshot: {manifest_path}")
    if checksum_path.exists() and checksum_path.read_text(encoding="ascii") != checksum:
        raise FileExistsError(f"refusing to rewrite immutable checksum: {checksum_path}")

    if not manifest_path.exists():
        manifest_path.write_bytes(raw)
    if not checksum_path.exists():
        checksum_path.write_text(checksum, encoding="ascii")
    return manifest_path, digest


def _validate_structure(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    unknown_top = sorted(set(manifest) - TOP_LEVEL_FIELDS)
    if unknown_top:
        errors.append(f"unknown top-level fields: {', '.join(unknown_top)}")
    missing_top = sorted(TOP_LEVEL_FIELDS - set(manifest))
    if missing_top:
        errors.append(f"missing top-level fields: {', '.join(missing_top)}")
    if manifest.get("protocol") != CORPUS_PROTOCOL:
        errors.append(f"unsupported protocol: {manifest.get('protocol')}")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return errors + ["artifacts must be a list"]

    paths: list[str] = []
    for index, artifact in enumerate(artifacts):
        prefix = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be an object")
            continue
        unknown = sorted(set(artifact) - ARTIFACT_FIELDS)
        if unknown:
            errors.append(f"{prefix} has unknown fields: {', '.join(unknown)}")

        path = artifact.get("path")
        if not isinstance(path, str) or not path:
            errors.append(f"{prefix}.path must be a non-empty string")
        else:
            paths.append(path)
        if artifact.get("artifact_class") not in ARTIFACT_CLASSES:
            errors.append(f"{prefix}.artifact_class is invalid")
        if type(artifact.get("size_bytes")) is not int or artifact["size_bytes"] < 0:
            errors.append(f"{prefix}.size_bytes must be a non-negative integer")
        if not isinstance(artifact.get("raw_sha256"), str) or not _HEX_64.fullmatch(artifact["raw_sha256"]):
            errors.append(f"{prefix}.raw_sha256 must be lowercase SHA-256 hex")
        if not isinstance(artifact.get("git_blob_oid"), str) or not _GIT_OID.fullmatch(artifact["git_blob_oid"]):
            errors.append(f"{prefix}.git_blob_oid must be a Git object ID")
        if not isinstance(artifact.get("media_type"), str) or not artifact["media_type"]:
            errors.append(f"{prefix}.media_type must be a non-empty string")
        if not isinstance(artifact.get("source_url"), str) or not artifact["source_url"]:
            errors.append(f"{prefix}.source_url must be a non-empty string")
        canonical_hash = artifact.get("canonical_text_sha256")
        if canonical_hash is not None and (
            not isinstance(canonical_hash, str) or not _HEX_64.fullmatch(canonical_hash)
        ):
            errors.append(f"{prefix}.canonical_text_sha256 must be lowercase SHA-256 hex")
        if artifact.get("artifact_class") == "authored_work":
            metadata = artifact.get("metadata")
            if not isinstance(metadata, dict):
                errors.append(f"{prefix}.metadata is required for authored work")
            else:
                if set(metadata) != {"author", "status", "title"}:
                    errors.append(f"{prefix}.metadata must contain only author, status, and title")
                for field in ("author", "status", "title"):
                    if not isinstance(metadata.get(field), str):
                        errors.append(f"{prefix}.metadata.{field} must be a string")
            if canonical_hash is None:
                errors.append(f"{prefix}.canonical_text_sha256 is required for authored work")

    if paths != sorted(paths):
        errors.append("artifact paths must be sorted")
    if len(paths) != len(set(paths)):
        errors.append("artifact paths must be unique")

    summary = manifest.get("summary")
    if isinstance(summary, dict):
        class_counts = Counter(
            item.get("artifact_class")
            for item in artifacts
            if isinstance(item, dict) and isinstance(item.get("artifact_class"), str)
        )
        expected_reading_surfaces = len(
            {
                item["reading_url"]
                for item in artifacts
                if isinstance(item, dict)
                and item.get("artifact_class") == "authored_work"
                and isinstance(item.get("reading_url"), str)
            }
        )
        expected = {
            "artifact_classes": dict(sorted(class_counts.items())),
            "authored_work_count": class_counts["authored_work"],
            "reading_surface_count": expected_reading_surfaces,
            "tracked_file_count": len(artifacts),
            "tracked_size_bytes": sum(
                item.get("size_bytes", 0)
                for item in artifacts
                if isinstance(item, dict) and type(item.get("size_bytes")) is int
            ),
        }
        if summary != expected:
            errors.append("summary does not match artifact records")
    else:
        errors.append("summary must be an object")

    source = manifest.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
    else:
        for field in ("commit", "tree_oid"):
            if not isinstance(source.get(field), str) or not _GIT_OID.fullmatch(source[field]):
                errors.append(f"source.{field} must be a Git object ID")
        for field in ("commit_time", "repository"):
            if not isinstance(source.get(field), str) or not source[field]:
                errors.append(f"source.{field} must be a non-empty string")

    snapshot = manifest.get("snapshot")
    if not isinstance(snapshot, dict):
        errors.append("snapshot must be an object")
    else:
        if snapshot.get("inclusion") != "all_tracked_blob_files":
            errors.append("snapshot.inclusion is invalid")
        previous = snapshot.get("previous_manifest_sha256")
        if previous is not None and (not isinstance(previous, str) or not _HEX_64.fullmatch(previous)):
            errors.append("snapshot.previous_manifest_sha256 must be null or lowercase SHA-256 hex")
    return errors


def verify_corpus_manifest(manifest_path: Path, source_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    raw = manifest_path.read_bytes()
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"manifest is not valid UTF-8 JSON: {exc}"]
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]

    if raw != _manifest_bytes(manifest):
        errors.append("manifest bytes are not in the required deterministic serialization")
    errors.extend(_validate_structure(manifest))

    digest = hashlib.sha256(raw).hexdigest()
    checksum_path = manifest_path.with_name("manifest.sha256")
    if not checksum_path.exists():
        errors.append("manifest.sha256 is missing")
    else:
        expected_line = f"{digest}  manifest.json\n"
        try:
            actual_line = checksum_path.read_text(encoding="ascii")
        except UnicodeDecodeError:
            errors.append("manifest.sha256 is not ASCII")
        else:
            if actual_line != expected_line:
                errors.append("manifest.sha256 does not match manifest.json")

    if source_root is None or errors:
        return errors

    source = manifest.get("source", {})
    commit = source.get("commit")
    tree_oid = source.get("tree_oid")
    if not isinstance(commit, str) or not isinstance(tree_oid, str):
        return errors + ["source commit and tree_oid are required for source verification"]

    source_root = source_root.resolve()
    try:
        actual_commit = _git_text(source_root, "rev-parse", f"{commit}^{{commit}}")
        actual_tree = _git_text(source_root, "rev-parse", f"{commit}^{{tree}}")
    except subprocess.CalledProcessError as exc:
        return errors + [f"source commit is not available: {exc}"]
    if actual_commit != commit:
        errors.append("source commit does not resolve exactly")
    if actual_tree != tree_oid:
        errors.append("source tree_oid does not match the commit")

    tree_entries = {path: (oid, size) for path, oid, size in _tree_entries(source_root, commit)}
    manifest_artifacts = {
        item["path"]: item
        for item in manifest["artifacts"]
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if set(tree_entries) != set(manifest_artifacts):
        errors.append("manifest paths do not exactly match the source commit")
        return errors

    for path in sorted(tree_entries):
        oid, recorded_size = tree_entries[path]
        artifact = manifest_artifacts[path]
        raw_source = bytes(_git(source_root, "cat-file", "blob", oid))
        if artifact.get("git_blob_oid") != oid:
            errors.append(f"{path}: git_blob_oid does not match source commit")
        if artifact.get("size_bytes") != recorded_size or len(raw_source) != recorded_size:
            errors.append(f"{path}: size_bytes does not match source commit")
        if artifact.get("raw_sha256") != sha256_hex(raw_source):
            errors.append(f"{path}: raw_sha256 does not match source commit")
        if "canonical_text_sha256" in artifact:
            actual_canonical = sha256_hex(canonicalize_bytes(raw_source))
            if artifact["canonical_text_sha256"] != actual_canonical:
                errors.append(f"{path}: canonical_text_sha256 does not match source commit")
    return errors
