# Bazel source build

Bazel generates C++ and Python bindings from every `proto/*.proto`, compiles
DASH's utility library and SWIG extension, and produces runtime and matching
debug tar archives. Native AMD64 and ARM64 builds are supported on Debian
Trixie with Bazel 8.5.1 and Python 3.13. Other configurations, including ARMHF
and Bookworm, continue to use the existing Make build.

```sh
# Run inside native Debian Trixie. Add --config=aarch64 on ARM64.
bazel build //:libdashapi_pkg //:libdashapi_pkg.debug_symbols \
  //:protobuf_runtime_pkg //:protobuf_debug_pkg
bazel test --test_output=errors \
  //bazel:utils_test //bazel:python_test \
  //bazel:runtime_consumer_test //bazel:source_contract_test
```

The contract test depends on all four archives, so the test command also builds
them. Archive inspection requires `tar`, `binutils`, and `gdb`.

## Targets and deployment

| Target | Output |
| --- | --- |
| `//:dashapi` | Public C++ headers and the source-built shared library |
| `//:shared_library` | Linked `libdashapi.so` |
| `//misc:dash_api` | Generated Python modules and SWIG extension for Bazel consumers |
| `//:libdashapi_pkg` | Runtime/install tar with Make's installed paths |
| `//:libdashapi_pkg.debug_symbols` | Detached symbols for the packaged library and extension |
| `//:protobuf_runtime_pkg` | Source-built shared Protobuf runtime and license |
| `//:protobuf_debug_pkg` | Matching Protobuf debug symbols |

The runtime tar installs headers under `/usr/include/dash_api`,
`libdashapi.so` under `/usr/lib`, Python modules, typing stubs and the SWIG
extension under `/usr/lib/python3/dist-packages/dash_api`, and the
`/usr/bin/dash_api_utils` CLI. One install mapping defines both package inputs
and their destination paths and modes.

The library's SONAME is `libdashapi.so`. Every protobuf descriptor is retained
for dynamic JSON conversion. The Python extension resolves Python symbols
from its interpreter without linking `libpython`. Both DASH ELF files depend on
`libprotobuf.so.32`; the full Protobuf runtime is not statically embedded in them.
Stage the Protobuf dependency tar alongside DASH; it installs the shared library
under `/usr/lib/<multiarch>` with its SONAME symlink. Its separate debug tar
provides the matching build-ID symbols.

`sonic_deploy_tar(force_debug_build = True)` produces the stripped runtime
and detached symbols from the same linked ELF files. Symbols install under
`/usr/lib/debug/.build-id`; `DebugSymbolsInfo` lets downstream debug containers
collect them while extending the matching runtime image. Containers can consume
the tars directly. This component does not define Bazel DEB or container targets.

## Dependencies

[`MODULE.bazel`](../MODULE.bazel) declares versions and
[`.bazelrc`](../.bazelrc) uses the maintained SONiC registry `main` branch,
plus Bazel Central Registry for CI and local commands. The SONiC registry provides the source-built Protobuf compiler and runtime.
Build Infra supplies the tar packaging rules and execution tools.
The root `.bazelrc` supplies
`--remote_download_regex=(^|.*/)tools/build_tools/kernel_runtime_(amd64|arm64)(/.*)?$`
for its cached kernel-tool trees. Dependencies do not import their `.bazelrc`,
so downstream roots selecting this infrastructure need the same option; a
command using `--ignore_all_rc_files` must pass it explicitly. CI records the
current maintained registry revision for the run; the checked-in
default stays on `main`.

| Dependency | Role |
| --- | --- |
| Upstream Protobuf v21.12 (3.21.12) | Source-built compiler and shared C++ runtime from one release, using upstream build definitions through `protobuf-legacy` |
| SWIG 4.3.0 | Execution-side wrapper generation through shared SONiC rules |
| Debian Boost Filesystem and System 1.83 | Target libraries for the existing C++ utility tests |
| Hash-pinned Python wheels | Protobuf 6.33.5 for Bazel consumers; Click and Pytest for tests |
| Debian `python3-protobuf` 3.21.12 | System-Python validation of the installed tars |

DASH and its C++ Protobuf compiler/runtime are compiled from source; pinned APT
packages and wheels supply the other dependencies. The separate Python runtime
versions above remain intentional consumer inputs. Distroless `0.9.4.sonic.20` carries the native protobuf header fix and the
declared-tool support required by the selected infrastructure. It sorts above
older dependency requests without a root override. CI verifies
the resolved infrastructure, Distroless and Protobuf declarations and retains the module graph.

The root pins `tar.bzl@0.10.5.sonic.2`, including a root override because
dependency overrides do not propagate. Its `default_mtime` API is required by
`//:libdashapi_pkg_rttar` for reproducible deployment archives. CI retains the
fetched tar-module declaration alongside the infrastructure declaration.

The deployed runtime needs the source-built Protobuf runtime tar plus `libc6`,
`libgcc-s1`, `libstdc++6`, Python 3.13, `python3-click`, and `python3-protobuf`.
[CI](../.github/workflows/bazel.yml) installs those remaining dependencies and its inspection tools
from the same signed Debian snapshots as the shared toolchain, inside a
digest-pinned Trixie image. Snapshot dates and the image digest are recorded in
the workflow; actual APT sources and installed versions are retained as evidence.

`MODULE.bazel.lock` is ignored and generated in update mode from a fresh
checkout. CI retains it under `validation/generated/MODULE.bazel.lock` and
checks that tracked files stay clean. Keep package locks, versions, source
integrity values pinned; follow the maintained registry branch and do not commit
this generated lock.

## Validation and artifacts

| Test | Coverage |
| --- | --- |
| `utils_test` | Existing five C++ utility tests |
| `python_test` | Every generated module and stub, optional/timestamp behavior, and the existing CLI roundtrip test |
| `runtime_consumer_test` | C++/C API behavior, exact 3.21.12 headers, and loading of the selected DASH and shared Protobuf files |
| `source_contract_test` | Complete tar inventory, ownership, modes, architecture, SONAME, dependencies, build IDs, debuglink checksums and GDB source-line lookup |
| `installed_tar_test.py` (CI) | Installed C/Python/SWIG/CLI roundtrips with system Python and standard paths; loaded Protobuf bytes match its runtime tar without custom library search paths |

The utility suite calls Protobuf through `libdashapi`. Its test environment
preloads the declared `@protobuf_legacy//:shared_library` runfile so that this
indirect dependency cannot fall back to a host library. The library and TAR
targets retain their production link and installation settings.

Required source checks are `Bazel (AMD64)` and `Bazel (ARM64)`. Both run the
four Bazel tests uncached, extract the built tars with their external runtime
dependencies, and run installed-consumer validation. Their Actions artifacts are:

- `sonic-dash-api-packages-<architecture>-<revision>`: DASH and Protobuf runtime/debug tars,
  headers, linked library, compiled consumer and SHA-256 provenance.
- `sonic-dash-api-validation-<architecture>-<revision>`: test results,
  build/test events, generation/compilation actions, environment and dependency
  records, declarations and the generated lock.

Evidence identifies the tested revision and architecture. Symbol checks cover
DASH's two ELF outputs and the shared Protobuf runtime, including source-line
lookup through all three matching debug files. CI also records `libprotoc 3.21.12`
and the source generation and compilation actions.
