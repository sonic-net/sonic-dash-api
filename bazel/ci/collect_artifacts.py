"""Retain source-built DASH/Protobuf tars, symbols and native validation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET


TESTS = {
    "//bazel:source_contract_test": "bazel/source_contract_test",
    "//bazel:runtime_consumer_test": "bazel/runtime_consumer_test",
    "//bazel:utils_test": "bazel/utils_test",
    "//bazel:ha_schema_test": "bazel/ha_schema_test",
    # The public //bazel test suite runs this native Python test.
    "//bazel:python_test": "misc/python_test",
}
DECLARATIONS = (
    ".bazelversion", ".bazelrc", "MODULE.bazel",
    "BUILD.bazel", "bazel/BUILD.bazel", "misc/BUILD.bazel", "Makefile",
    "bazel/installed_tar_test.py", "bazel/source_contract_test.py",
    "bazel/ha_schema.BUILD.bazel", "bazel/ha_schema_test.py", "bazel/ha_schema.md",
)
PACKAGES = {
    "//:libdashapi_pkg": (".tar", "packages/libdashapi.tar"),
    "//:libdashapi_pkg.debug_symbols": (".tar", "packages/libdashapi.debug.tar"),
    "//:protobuf_runtime_pkg": (".tar", "packages/libprotobuf.tar"),
    "//:protobuf_debug_pkg": (".tar", "packages/libprotobuf.debug.tar"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(repo: Path, *arguments: str) -> str:
    result = subprocess.run(arguments, cwd=repo, capture_output=True, text=True)
    require(result.returncode == 0, "command failed: " + " ".join(arguments) + "\n" + result.stderr + result.stdout)
    return result.stdout.strip()


def module_version(text: str, rule: str, name: str = "sonic-build-infra") -> str:
    versions = []
    for stanza in re.findall(r"\b" + rule + r"\s*\((.*?)\)", text, re.DOTALL):
        if re.search(r'\bname\s*=\s*"' + re.escape(name) + r'"', stanza):
            match = re.search(r'\bversion\s*=\s*"([^"]+)"', stanza)
            require(match is not None, name + " declaration has no version")
            versions.append(match.group(1))
    require(len(versions) == 1, "expected exactly one " + name + " declaration")
    return versions[0]


def materialized_files(names: list[str], execution_root: Path, output_base: Path, target: str) -> list[Path]:
    # Source-only external repositories need not remain linked into the
    # execution root after another Bazel command. Resolve that exact
    # cquery path from Bazel's external repository store when necessary.
    paths = [execution_root / name for name in names]
    paths = [
        output_base / name if not path.is_file() and name.startswith("external/") else path
        for name, path in zip(names, paths)
    ]
    require(all(path.is_file() for path in paths), "target output is missing: " + target)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--architecture", choices=("amd64", "arm64"), required=True)
    parser.add_argument("--bazel-config", choices=("", "default", "aarch64"), default="default")
    parser.add_argument("--image", required=True, help="Pinned container image used by the workflow")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for owned in ("provenance.json", "packages", "development", "consumer", "validation/tests", "validation/declarations", "validation/generated"):
        require(not (output / owned).exists(), "output already contains a previous collection: " + owned)

    machine = {"amd64": "x86_64", "arm64": "aarch64"}[args.architecture]
    require(platform.system() == "Linux" and platform.machine() == machine, "runner CPU is not the selected native architecture")
    require(run(repo, "dpkg", "--print-architecture") == args.architecture, "container architecture differs from the native runner")
    os_release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    require(os_release.get("VERSION_CODENAME", "").strip('"') == "trixie", "validation requires native Debian Trixie")

    options = ["--lockfile_mode=update"]
    if args.bazel_config and args.bazel_config != "default":
        options.append("--config=" + args.bazel_config)

    def bazel(command: str, *arguments: str) -> str:
        return run(repo, "bazel", command, *options, *arguments)

    platform_name = {"amd64": "x86_64_trixie", "arm64": "aarch64_trixie"}[args.architecture]
    platform_label = "@sonic_build_infra//platforms:" + platform_name
    mapping = json.loads(bazel("mod", "dump_repo_mapping", ""))
    require(all(re.fullmatch(r"[A-Za-z0-9._+-]+", mapping[name]) is not None
                for name in ("sonic_build_infra", "rules_distroless", "protobuf_legacy", "tar.bzl")),
            "resolved canonical repository is ambiguous")
    canonical = mapping["sonic_build_infra"]
    # Bazel 8 info does not apply the root module's apparent-repository mapping
    # to platform flags. Keep the same platforms, using their resolved labels.
    canonical_platform = "@@" + canonical + "//platforms:" + platform_name
    info_options = ["--platforms=" + canonical_platform, "--host_platform=" + canonical_platform]
    execution_root = Path(bazel("info", *info_options, "execution_root"))
    testlogs = Path(bazel("info", *info_options, "bazel-testlogs"))
    output_base = Path(bazel("info", *info_options, "output_base"))

    def files(target: str) -> list[Path]:
        names = bazel("cquery", "config(" + target + ", target)", "--output=files").splitlines()
        require(bool(names), "target has no materialized outputs: " + target)
        return materialized_files(names, execution_root, output_base, target)

    def retain(source: Path, relative: str | Path) -> None:
        require(source.is_file(), "required artifact is missing: " + str(source))
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        shutil.copymode(source, destination)

    for target, (suffix, destination) in PACKAGES.items():
        candidates = [path for path in files(target) if path.name.endswith(suffix)]
        require(len(candidates) == 1, "expected one package output: " + target)
        retain(candidates[0], destination)
    libraries = files("//:shared_library")
    require(len(libraries) == 1 and libraries[0].name == "libdashapi.so", "expected one source-built DASH library")
    retain(libraries[0], "development/libdashapi.so")
    headers = files("//:generated_headers")
    proto_sources = sorted((repo / "proto").glob("*.proto"))
    expected_headers = {source.stem + ".pb.h" for source in proto_sources} | {"utils.h"}
    require(len(headers) == len(expected_headers) and {path.name for path in headers} == expected_headers, "public headers do not cover every protobuf source and utils.h")
    for header in headers:
        retain(header, Path("development/include/dash_api") / header.name)

    consumers = files("//bazel:runtime_consumer_test")
    require(len(consumers) == 1, "expected one compiled runtime consumer")
    elf_header = run(repo, "readelf", "--file-header", str(consumers[0]))
    elf_machine = {"amd64": "Advanced Micro Devices X86-64", "arm64": "AArch64"}[args.architecture]
    require(re.search(r"Machine:\s+" + re.escape(elf_machine) + r"\s*$", elf_header, re.MULTILINE) is not None, "compiled consumer is not native to the selected architecture")
    retain(consumers[0], "consumer/runtime_consumer_test")

    for test, test_directory in TESTS.items():
        directory = testlogs / test_directory
        result = ET.parse(directory / "test.xml").getroot()
        suites = list(result.iter("testsuite"))
        require(any(int(suite.get("tests", "0")) > 0 for suite in suites), "test result contains no executed cases: " + test)
        require(all(int(suite.get(field, "0")) == 0 for suite in suites for field in ("failures", "errors", "skipped")), "test suite reports incomplete or failed cases: " + test)
        require(not any(element.tag in ("failure", "error", "skipped") for element in result.iter()), "test result is not a complete pass: " + test)
        for filename in ("test.log", "test.xml"):
            retain(directory / filename, Path("validation/tests") / test_directory / filename)

    for declaration in DECLARATIONS:
        retain(repo / declaration, Path("validation/declarations") / declaration)
    for source in proto_sources:
        retain(source, Path("validation/declarations/proto") / source.name)
    for source in files("//:ha_schema_sources"):
        retain(source, Path("validation/ha-schema") / source.name)
    for descriptor in files("//bazel:ha_schema_descriptor"):
        retain(descriptor, Path("validation/ha-schema") / descriptor.name)
    for source in sorted([*(repo / "bazel").rglob("*.bzl"), *(repo / "misc").glob("*.bzl")]):
        retain(source, Path("validation/declarations") / source.relative_to(repo))
    # Extension-only repositories need not have a symlink in the action execroot.
    root_module = (repo / "MODULE.bazel").read_text()
    resolved_modules = {}
    for key, name, apparent in (
        ("infrastructure", "sonic-build-infra", "sonic_build_infra"),
        ("tar", "tar.bzl", "tar.bzl"),
        ("distroless", "rules_distroless", "rules_distroless"),
        ("protobuf", "protobuf-legacy", "protobuf_legacy"),
    ):
        repository = mapping[apparent]
        fetched_module = output_base / "external" / repository / "MODULE.bazel"
        require(fetched_module.is_file(), "resolved " + name + " MODULE.bazel is missing")
        version = module_version(root_module, "bazel_dep", name)
        require(module_version(fetched_module.read_text(), "module", name) == version,
                "resolved " + name + " version differs from the declaration")
        retain(fetched_module, "validation/declarations/resolved-" + name + ".MODULE.bazel")
        resolved_modules[key] = {
            "version": version,
            "canonical_repository": repository,
            "module_sha256": sha256(fetched_module),
        }
    # The registry module forwards its public targets to the Debian-patched source repository.
    protobuf_module = mapping["protobuf_legacy"]
    source_mapping = json.loads(bazel("mod", "dump_repo_mapping", protobuf_module))
    protobuf_source = source_mapping["protobuf_source"]
    require(re.fullmatch(r"[A-Za-z0-9._+-]+", protobuf_source) is not None,
            "resolved Protobuf source repository is ambiguous")
    for declaration in ("BUILD.bazel", "bazel/source.bzl"):
        retain(output_base / "external" / protobuf_module / declaration,
               Path("validation/declarations/protobuf-module") / declaration)
    protobuf_root = output_base / "external" / protobuf_source
    for declaration in (
        "BUILD.bazel", "protobuf.bzl", "defs.bzl", "sonic/targets.bzl",
        "src/google/protobuf/stubs/common.h", "src/google/protobuf/compiler/main.cc",
    ):
        retain(protobuf_root / declaration, Path("validation/declarations/protobuf-source") / declaration)
    version_header = (protobuf_root / "src/google/protobuf/stubs/common.h").read_text()
    require(re.search(r"^#define GOOGLE_PROTOBUF_VERSION 3021012$", version_header, re.MULTILINE) is not None,
            "resolved Protobuf headers are not 3.21.12")
    protoc_version = (output / "validation/protoc-version.txt").read_text().strip()
    require(protoc_version == "libprotoc 3.21.12", "source compiler version differs from its headers/runtime")
    source_actions = json.loads((output / "validation/source-actions.json").read_text())
    actions = source_actions.get("actions", [])
    protobuf_actions = [action for action in actions
                        if protobuf_source + "/" in " ".join(action.get("arguments", []))]
    counts = {mnemonic: sum(action.get("mnemonic") == mnemonic for action in protobuf_actions)
              for mnemonic in ("CppCompile", "ProtoCompile")}
    require(all(counts.values()), "source actions omit upstream Protobuf compilation or generation")
    resolved_modules["protobuf"].update({
        "compiler_version": protoc_version,
        "source_repository": protobuf_source,
        "source_action_counts": counts,
    })
    graph = json.loads(bazel("mod", "graph", "--output=json"))
    require(isinstance(graph, dict) and bool(graph), "resolved module graph is empty")
    (output / "validation/module-graph.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n")

    # This is generated evidence from this native build, not a source input.
    lockfile = repo / "MODULE.bazel.lock"
    require(not run(repo, "git", "ls-files", "--", lockfile.name), "dependency lock must not be tracked")
    run(repo, "git", "check-ignore", "--quiet", lockfile.name)
    require(lockfile.is_file(), "Bazel did not generate a dependency lock")
    require(isinstance(json.loads(lockfile.read_text()).get("lockFileVersion"), int), "generated dependency lock has no format version")
    generated_lock = "validation/generated/MODULE.bazel.lock"
    retain(lockfile, generated_lock)

    inventory = {
        path.relative_to(output).as_posix(): {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(output.rglob("*")) if path.is_file()
    }
    provenance = {
        "schema_version": 2,
        "scope": "Source-built Protobuf 3.21.12 compiler/shared runtime and generated DASH C++/Python APIs, C++ library, SWIG extension and CLI; runtime/debug tars, native C++/Python tests, installed consumers, complete inventory and matching split-symbol validation.",
        "source": {
            "revision": run(repo, "git", "rev-parse", "HEAD"),
            "tree": run(repo, "git", "rev-parse", "HEAD^{tree}"),
            "tracked_worktree_dirty": bool(run(repo, "git", "status", "--porcelain", "--untracked-files=no")),
        },
        "environment": {
            "architecture": args.architecture,
            "uname_machine": platform.machine(),
            "distribution": "trixie",
            "container_image_input": args.image,
            "bazel": run(repo, "bazel", "--version"),
            "bazel_config": args.bazel_config,
            "platform": platform_label,
        },
        "github": {
            name.removeprefix("GITHUB_").lower(): os.environ[name]
            for name in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB", "GITHUB_WORKFLOW", "GITHUB_EVENT_NAME", "GITHUB_SHA")
            if name in os.environ
        },
        "package_targets": list(PACKAGES),
        "protobuf_sources": [source.relative_to(repo).as_posix() for source in proto_sources],
        "infrastructure": resolved_modules["infrastructure"],
        "distroless": resolved_modules["distroless"],
        "protobuf": resolved_modules["protobuf"],
        "dependency_resolution": {
            "lockfile_mode": "update",
            "generated_lockfile": generated_lock,
            "lockfile_tracked": False,
        },
        "tests": list(TESTS),
        "files": inventory,
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    print(f"Retained {len(inventory)} files for native {args.architecture} validation in {output}")


if __name__ == "__main__":
    main()
