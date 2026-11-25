"""Exercise the generated Python package and the repository's original CLI test."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys

import pytest
from python.runfiles import runfiles


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-test", required=True)
    parser.add_argument("--proto-paths", required=True, nargs="+")
    args = parser.parse_args()
    resolver = runfiles.Create()
    if resolver is None:
        raise RuntimeError("Bazel runfiles are unavailable")

    # A successful SWIG import alone does not validate the generated Python
    # schemas: import every schema and its typing stub from the same package.
    modules = []
    logical_paths = [path for group in args.proto_paths for path in group.split()]
    for logical_path in logical_paths:
        module = importlib.import_module("dash_api." + Path(logical_path).stem + "_pb2")
        source = Path(module.__file__)
        if not source.with_suffix(".pyi").is_file():
            raise RuntimeError(f"Generated typing stub is missing for {source}")
        if module.DESCRIPTOR.name != Path(logical_path).name:
            raise RuntimeError(f"Unexpected descriptor for {logical_path}")
        modules.append(module)
    if not modules:
        raise RuntimeError("No generated protobuf modules were checked")

    # Exercise the well-known timestamp import as well as DASH's sibling-module
    # imports, and retain proto3 optional-field presence through serialization.
    from dash_api import appliance_pb2, ha_scope_state_pb2

    appliance = appliance_pb2.Appliance(outbound_direction_lookup="dst_mac")
    copied = appliance_pb2.Appliance.FromString(appliance.SerializeToString())
    if not copied.HasField("outbound_direction_lookup"):
        raise RuntimeError("Proto3 optional field presence was lost")
    state = ha_scope_state_pb2.HaScopeState()
    state.last_updated_time.seconds = 123
    state_copy = ha_scope_state_pb2.HaScopeState.FromString(state.SerializeToString())
    if state_copy.last_updated_time.seconds != 123:
        raise RuntimeError("Timestamp protobuf round trip failed")

    print(f"Validated {len(modules)} generated Python protobuf modules and typing stubs")
    legacy_test = resolver.Rlocation(args.legacy_test)
    if not legacy_test or not Path(legacy_test).is_file():
        raise RuntimeError("The repository's original CLI test is missing")
    return pytest.main([legacy_test, "-q", "-p", "no:cacheprovider"])


if __name__ == "__main__":
    sys.exit(main())
