import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from fieldlight_proofs.corpus import (
    CORPUS_PROTOCOL,
    build_corpus_manifest,
    verify_corpus_manifest,
    write_corpus_snapshot,
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class CorpusTests(unittest.TestCase):
    def make_repo(self, root: Path) -> tuple[Path, dict[str, object], str]:
        repo = root / "source"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Fieldlight Test")
        git(repo, "config", "user.email", "fieldlight@example.com")

        (repo / "essay.md").write_text(
            '---\ntitle: "Essay"\nstatus: "Published"\nauthor: "Anni McHenry"\n---\n\n# Essay\n',
            encoding="utf-8",
        )
        (repo / "README.md").write_text("# Source\n", encoding="utf-8")
        (repo / "image.png").write_bytes(b"\x89PNG\r\n\x1a\nbinary")
        archive = repo / "archive"
        archive.mkdir()
        (archive / "posts.jsonl").write_text('{"id": 1}\n', encoding="utf-8")
        tools = repo / "tools"
        tools.mkdir()
        (tools / "build.py").write_text("print('ok')\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "Create source corpus")
        commit = git(repo, "rev-parse", "HEAD")
        config: dict[str, object] = {
            "author": "Anni McHenry",
            "default_reading_url_template": "https://fieldlight.com/writing/{slug}/",
            "reading_url_overrides": {},
            "repository_url": "https://github.com/annimch04/example",
            "site": "https://fieldlight.com",
        }
        return repo, config, commit

    def test_snapshot_is_complete_deterministic_and_source_verifiable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, config, commit = self.make_repo(root)
            manifest = build_corpus_manifest(repo, commit, config)

            first_path, first_digest = write_corpus_snapshot(root / "first", manifest)
            second_path, second_digest = write_corpus_snapshot(
                root / "second",
                build_corpus_manifest(repo, commit, config),
            )

            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(first_digest, second_digest)
            self.assertEqual(manifest["protocol"], CORPUS_PROTOCOL)
            self.assertEqual(manifest["summary"]["tracked_file_count"], 5)
            self.assertEqual(manifest["summary"]["authored_work_count"], 1)
            self.assertEqual(manifest["summary"]["reading_surface_count"], 1)
            self.assertEqual(verify_corpus_manifest(first_path, source_root=repo), [])

            artifacts = {item["path"]: item for item in manifest["artifacts"]}
            self.assertEqual(artifacts["essay.md"]["artifact_class"], "authored_work")
            self.assertEqual(artifacts["image.png"]["artifact_class"], "derivative")
            self.assertEqual(artifacts["archive/posts.jsonl"]["artifact_class"], "public_archive")
            self.assertEqual(artifacts["tools/build.py"]["artifact_class"], "tooling")
            self.assertEqual(
                artifacts["image.png"]["raw_sha256"],
                hashlib.sha256((repo / "image.png").read_bytes()).hexdigest(),
            )

    def test_verify_rejects_manifest_mutation_even_with_rewritten_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, config, commit = self.make_repo(root)
            manifest = build_corpus_manifest(repo, commit, config)
            manifest["bitcoin_anchor"] = {"txid": "not-allowed"}
            raw = (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()

            snapshot = root / "snapshot"
            snapshot.mkdir()
            manifest_path = snapshot / "manifest.json"
            manifest_path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            (snapshot / "manifest.sha256").write_text(
                f"{digest}  manifest.json\n",
                encoding="ascii",
            )

            errors = verify_corpus_manifest(manifest_path, source_root=repo)
            self.assertTrue(any("unknown top-level fields" in error for error in errors))

    def test_snapshot_writer_refuses_to_rewrite_an_immutable_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, config, commit = self.make_repo(root)
            manifest = build_corpus_manifest(repo, commit, config)
            snapshot = root / "snapshot"
            write_corpus_snapshot(snapshot, manifest)

            changed = dict(manifest)
            changed["identity"] = dict(manifest["identity"])
            changed["identity"]["author"] = "Someone Else"

            with self.assertRaises(FileExistsError):
                write_corpus_snapshot(snapshot, changed)

    def test_verifier_reports_malformed_artifact_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, config, commit = self.make_repo(root)
            manifest = build_corpus_manifest(repo, commit, config)
            manifest["artifacts"][0]["artifact_class"] = None
            raw = (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()

            snapshot = root / "snapshot"
            snapshot.mkdir()
            manifest_path = snapshot / "manifest.json"
            manifest_path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            (snapshot / "manifest.sha256").write_text(
                f"{digest}  manifest.json\n",
                encoding="ascii",
            )

            errors = verify_corpus_manifest(manifest_path)
            self.assertTrue(any("artifact_class is invalid" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
