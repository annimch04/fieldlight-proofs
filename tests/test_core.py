import tempfile
import unittest
from pathlib import Path

from fieldlight_proofs.core import (
    build_manifest,
    canonicalize_bytes,
    mine_proof,
    opreturn_payload,
    verify_manifest,
)


class CoreTests(unittest.TestCase):
    def test_canonicalize_bytes_normalizes_line_endings_and_space(self) -> None:
        raw = b"\n\nhello  \r\nworld\t\r\n\r\n"
        self.assertEqual(canonicalize_bytes(raw), b"hello\nworld\n")

    def test_mine_build_verify_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            article = tmp_path / "article.md"
            article.write_text("# Title\n\nBody\n", encoding="utf-8")

            proof = mine_proof(
                article,
                url="https://fieldlight.com/title",
                title="Title",
                zeros=2,
                source_path="article.md",
            )
            manifest = build_manifest([proof], zeros=2, created_at="2026-07-07T00:00:00Z")

            self.assertTrue(proof.proof_sha256.startswith("00"))
            self.assertEqual(verify_manifest(manifest, base_dir=tmp_path), [])
            self.assertTrue(opreturn_payload(manifest).startswith("fieldlight:v1:"))

    def test_verify_rejects_tampered_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            article = tmp_path / "article.md"
            article.write_text("Body\n", encoding="utf-8")
            proof = mine_proof(article, url="https://fieldlight.com/body", title="Body", zeros=1)
            manifest = build_manifest([proof], zeros=1, created_at="2026-07-07T00:00:00Z")
            manifest["articles"][0]["title"] = "Changed"

            errors = verify_manifest(manifest, base_dir=tmp_path)
            self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
