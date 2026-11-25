"""Artifact collection must retain source-only external schema files."""
from pathlib import Path
import tempfile
import unittest

from collect_artifacts import materialized_files


class MaterializedFilesTest(unittest.TestCase):
    def test_external_source_without_execution_root_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "external/+_repo_rules+dash_ha_schema/proto/types.proto"
            source = root / name
            source.parent.mkdir(parents=True)
            source.write_text('syntax = "proto3";\n')
            self.assertEqual(materialized_files([name], root / "execroot", root, "//:ha_schema_sources"), [source])

    def test_generated_output_keeps_execution_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "bazel-out/bin/bazel/ha_schema.pb"
            output = root / "execroot" / name
            output.parent.mkdir(parents=True)
            output.write_bytes(b"descriptor")
            self.assertEqual(materialized_files([name], root / "execroot", root, "//bazel:ha_schema_descriptor"), [output])

    def test_missing_source_remains_a_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "target output is missing"):
                materialized_files(["external/schema/missing.proto"], root / "execroot", root, "//:ha_schema_sources")


if __name__ == "__main__":
    unittest.main()
