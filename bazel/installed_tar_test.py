"""Exercise DASH's extracted runtime tar with its declared runtime dependencies."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile


LIBRARY = Path("/usr/lib/libdashapi.so")
PACKAGE = Path("/usr/lib/python3/dist-packages/dash_api")
EXTENSION = PACKAGE / "_utils.so"
CLI = Path("/usr/bin/dash_api_utils")
TABLE = b"DASH_APPLIANCE_TABLE"
DOCUMENT = {
    "sip": {"ipv4": 16777482},
    "vm_vni": 4321,
    "local_region_id": 100,
    "outbound_direction_lookup": "dst_mac",
    "trusted_vnis_list": [{"value": 100}],
}
JSON_INPUT = json.dumps(DOCUMENT).encode()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(*arguments: str, input: bytes | None = None) -> bytes:
    result = subprocess.run(arguments, input=input, capture_output=True, env={**os.environ, "LC_ALL": "C"})
    require(result.returncode == 0, "command failed: " + " ".join(arguments) + "\n" + result.stderr.decode(errors="replace") + result.stdout.decode(errors="replace"))
    return result.stdout


def check_loaded_path(actual: str, expected: Path) -> None:
    require(Path(actual).resolve() == expected.resolve(), "expected installed file " + str(expected) + ", loaded " + actual)


def loaded_symbol_path(symbol) -> Path:
    class DlInfo(ctypes.Structure):
        _fields_ = [
            ("filename", ctypes.c_char_p), ("base", ctypes.c_void_p),
            ("symbol", ctypes.c_char_p), ("address", ctypes.c_void_p),
        ]

    dladdr = ctypes.CDLL(None).dladdr
    dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(DlInfo)]
    dladdr.restype = ctypes.c_int
    info = DlInfo()
    require(dladdr(ctypes.cast(symbol, ctypes.c_void_p), ctypes.byref(info)) != 0 and bool(info.filename), "cannot locate the loaded implementation")
    return Path(info.filename.decode()).resolve()


def check_protobuf(library, runtime_tar: Path) -> dict:
    # Resolve an implementation symbol through each DASH DSO's dependencies.
    # Its location and bytes must match the source-built dependency archive.
    symbol = getattr(library, "_ZN6google8protobuf14DescriptorPool14generated_poolEv")
    loaded = loaded_symbol_path(symbol)
    with tarfile.open(runtime_tar) as archive:
        candidates = [member for member in archive if member.isfile() and member.name.endswith("/libprotobuf.so.32.0.12")]
        require(len(candidates) == 1, "expected one source-built Protobuf runtime ELF")
        member = candidates[0]
        stream = archive.extractfile(member)
        require(stream is not None, "source-built Protobuf runtime is unreadable")
        expected_hash = hashlib.sha256(stream.read()).hexdigest()
        check_loaded_path(str(loaded), Path("/") / member.name.removeprefix("./"))
    require(hashlib.sha256(loaded.read_bytes()).hexdigest() == expected_hash, "loaded Protobuf differs from the source-built runtime tar")
    return {"loaded_library": str(loaded), "sha256": expected_hash}


def check_c_api(runtime_tar: Path) -> dict:
    # This phase runs separately from the SWIG consumer. Both legacy ELF files
    # embed DASH's descriptors and should not register them into one process.
    library = ctypes.CDLL(str(LIBRARY))
    name = library.TableNameToTypeUrl
    name.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t]
    name.restype = ctypes.c_size_t
    name_size = name(TABLE, None, 0)
    require(0 < name_size < 4096, "C API returned an invalid type URL size")
    output = ctypes.create_string_buffer(name_size)
    require(name(TABLE, output, name_size) == name_size, "C API type URL size changed")
    require(output.value == b"sonic/dash.appliance.Appliance", "installed C API type URL differs")

    loaded = str(loaded_symbol_path(name))
    check_loaded_path(loaded, LIBRARY)

    encode = library.JsonStringToPbBinary
    encode.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t]
    encode.restype = ctypes.c_size_t
    length = encode(TABLE, JSON_INPUT, None, 0)
    require(0 < length < 1024 * 1024, "installed C API returned an invalid protobuf size")
    buffer = ctypes.create_string_buffer(length)
    require(encode(TABLE, JSON_INPUT, buffer, length) == length, "C API protobuf size changed")
    binary = buffer.raw

    decode = library.PbBinaryToJsonString
    decode.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
    decode.restype = ctypes.c_size_t
    json_length = decode(TABLE, buffer, length, None, 0)
    require(0 < json_length < 1024 * 1024, "installed C API returned an invalid JSON size")
    decoded = ctypes.create_string_buffer(json_length)
    require(decode(TABLE, buffer, length, decoded, json_length) == json_length, "C API JSON size changed")
    require(json.loads(decoded.value) == DOCUMENT, "installed C API JSON/protobuf round trip changed content")
    return {"loaded_library": loaded, "serialized_hex": binary.hex(), "protobuf": check_protobuf(library, runtime_tar)}


def check_python(proto_dir: Path, runtime_tar: Path) -> dict:
    package = importlib.import_module("dash_api")
    check_loaded_path(package.__file__, PACKAGE / "__init__.py")
    sources = sorted(proto_dir.glob("*.proto"))
    require(bool(sources), "no schema sources found under " + str(proto_dir))
    for source in sources:
        module_name = source.stem + "_pb2"
        module = importlib.import_module("dash_api." + module_name)
        check_loaded_path(module.__file__, PACKAGE / (module_name + ".py"))
        require((PACKAGE / (module_name + ".pyi")).is_file(), "installed typing stub is missing: " + module_name)
        require(module.DESCRIPTOR.name == source.name, "installed module has the wrong descriptor: " + module_name)

    utils = importlib.import_module("dash_api.utils")
    extension = importlib.import_module("dash_api._utils")
    check_loaded_path(utils.__file__, PACKAGE / "utils.py")
    check_loaded_path(extension.__file__, EXTENSION)
    binary = utils.JsonStringToPbBinary(TABLE, JSON_INPUT)
    require(isinstance(binary, bytes) and bool(binary), "installed SWIG extension did not return protobuf bytes")
    require(json.loads(utils.PbBinaryToJsonString(TABLE, binary)) == DOCUMENT, "installed SWIG JSON/protobuf round trip changed content")

    # Cross-check the compiled serializer against an installed generated schema,
    # including proto3 optional-field presence, with the system Python runtime.
    appliance = importlib.import_module("dash_api.appliance_pb2").Appliance.FromString(binary)
    require(appliance.vm_vni == DOCUMENT["vm_vni"] and appliance.HasField("outbound_direction_lookup"), "installed Python schema cannot read the SWIG serialization")
    timestamp_module = importlib.import_module("dash_api.ha_scope_state_pb2")
    state = timestamp_module.HaScopeState()
    state.last_updated_time.seconds = 123
    require(timestamp_module.HaScopeState.FromString(state.SerializeToString()).last_updated_time.seconds == 123, "installed timestamp schema cannot round trip")
    return {"loaded_extension": extension.__file__, "schema_count": len(sources), "serialized_hex": binary.hex(), "protobuf": check_protobuf(ctypes.CDLL(str(EXTENSION)), runtime_tar)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proto-dir", type=Path, default=Path(__file__).resolve().parents[1] / "proto")
    parser.add_argument("--protobuf-runtime-tar", type=Path, required=True)
    parser.add_argument("--phase", choices=("c-api", "python"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    require(not os.environ.get("LD_LIBRARY_PATH"), "unset LD_LIBRARY_PATH before testing the installed tar")
    require(not os.environ.get("PYTHONPATH"), "unset PYTHONPATH before testing the installed tar")
    require(all(path.is_file() for path in (LIBRARY, EXTENSION, CLI)), "DASH runtime tar is not installed at its standard paths")
    proto_dir = args.proto_dir.resolve()
    if args.phase:
        record = check_c_api(args.protobuf_runtime_tar) if args.phase == "c-api" else check_python(proto_dir, args.protobuf_runtime_tar)
        print(json.dumps(record, sort_keys=True))
        return

    dependencies = {}
    for binary in (LIBRARY, EXTENSION):
        dynamic = run("readelf", "--dynamic", str(binary)).decode()
        needed = re.findall(r"Shared library: \[([^]]+)\]", dynamic)
        require("libprotobuf.so.32" in needed, "installed ELF omits the selected full protobuf ABI: " + str(binary))
        require(not any(name.startswith("libprotobuf-lite") for name in needed), "installed ELF unnecessarily requires protobuf-lite: " + str(binary))
        if binary == EXTENSION:
            require(not any(name.startswith("libpython") for name in needed), "installed Python extension links against libpython")
        dependencies[str(binary)] = needed

    # Use separate native consumers, matching the existing Make deployment.
    script = str(Path(__file__).resolve())
    phase_args = ["--proto-dir", str(proto_dir), "--protobuf-runtime-tar", str(args.protobuf_runtime_tar.resolve())]
    c_api = json.loads(run(sys.executable, script, "--phase=c-api", *phase_args))
    python = json.loads(run(sys.executable, script, "--phase=python", *phase_args))
    require(c_api["serialized_hex"] == python["serialized_hex"], "installed C and Python APIs produce different protobuf bytes")
    require(c_api["protobuf"] == python["protobuf"], "DASH C and Python extensions load different Protobuf runtimes")

    run(str(CLI), "--help")
    cli_binary = run(str(CLI), "--to_proto", "-t", TABLE.decode(), input=JSON_INPUT)
    require(cli_binary.hex() == c_api["serialized_hex"], "installed CLI serialization differs from the installed C/Python APIs")
    cli_json = run(str(CLI), "--to_json", "-t", TABLE.decode(), input=cli_binary)
    require(json.loads(cli_json) == DOCUMENT, "installed CLI JSON/protobuf round trip changed content")
    print(json.dumps({
        "result": "passed",
        "interpreter": sys.executable,
        "loaded_library": c_api["loaded_library"],
        "loaded_extension": python["loaded_extension"],
        "schema_count": python["schema_count"],
        "cli": str(CLI),
        "needed": dependencies,
        "protobuf": c_api["protobuf"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Installed DASH tar validation failed: " + str(error), file=sys.stderr)
        sys.exit(1)
