# Copilot Instructions for sonic-dash-api

## Project Overview

sonic-dash-api defines the DASH (Disaggregated API for SONiC Hosts) API using Protocol Buffers for the SONiC project. It provides the protobuf schema for the DASH APP DB, enabling gNMI-oriented northbound API access. The compiled protobuf definitions produce both C++ shared libraries and Python packages used by other DASH components to encode/decode database entries.

## Architecture

```
sonic-dash-api/
├── proto/                  # Protobuf definitions — the core of this repo
│   ├── types.proto         # Common types (IpAddress, IpPrefix, enums)
│   ├── acl_group.proto     # ACL group entry
│   ├── acl_rule.proto      # ACL rule entry
│   ├── acl_in.proto        # Inbound ACL
│   ├── acl_out.proto       # Outbound ACL
│   ├── eni.proto           # Elastic Network Interface
│   ├── eni_route.proto     # ENI routing
│   ├── route.proto         # Route entry
│   ├── route_type.proto    # Route type definitions
│   ├── route_rule.proto    # Route rules
│   ├── route_group.proto   # Route groups
│   ├── vnet.proto          # Virtual network
│   ├── vnet_mapping.proto  # VNet mapping
│   ├── tunnel.proto        # Tunnel configuration
│   ├── ha_scope.proto      # HA scope entry
│   ├── ha_set.proto        # HA set entry
│   ├── meter.proto         # Metering
│   ├── qos.proto           # QoS policies
│   └── ...                 # Additional proto files
├── misc/                   # C++ utilities, SWIG wrappers, tests
│   ├── *.cpp / *.h         # C++ helper code
│   ├── utils.i             # SWIG interface for Python bindings
│   └── pypkg/dash_api/     # Python package output directory
├── debian/                 # Debian packaging
├── Makefile                # Build orchestration
├── .azure-pipelines/       # CI pipeline definitions
└── azure-pipelines.yml     # Top-level CI config
```

### Key Concepts
- **Protobuf-first**: All DASH APP DB entries are defined as protobuf messages
- **Dual output**: Builds produce both a C++ shared library (`libdashapi.so`) and a Python package (`dash_api`)
- **SWIG bindings**: Python access to C++ utilities via SWIG-generated wrappers
- **Redis encoding**: Protobuf bytes are stored as values in Redis; keys follow a naming convention derived from the Key message fields

## Language & Style

- **Primary languages**: Protocol Buffers (schema), C++ (library/utilities), Python (bindings)
- **C++ standard**: C++14
- **Protobuf conventions**:
  - File names: `underscore_case.proto` (e.g., `acl_rule.proto`)
  - Message names: `CamelCase` (e.g., `AclRule`)
  - Key messages: Entry name + `Key` suffix (e.g., `AclRuleKey`)
  - List items: Entry name + `Item` suffix (e.g., `RouteTypeItem`)
  - Fields: `underscore_case` (e.g., `src_addr`)
  - Enums: `CamelCase` name, `UPPER_CASE` fields with enum name prefix (e.g., `IP_VERSION_IPV4`)
- **One message per file**: Each proto file contains exactly one entry message and its key message (except `types.proto`)

### Redis DB Naming
- Table names: `DASH_<ENTRY_NAME>_TABLE` (e.g., `DASH_ACL_RULE_TABLE`)
- Keys: Fields from the Key message joined with `:` separator
- Values: Protobuf-serialized bytes of the entry message

## Build Instructions

```bash
# Install dependencies
sudo apt install -y protobuf-compiler libprotobuf-dev python3-dev swig

# Build everything (C++ proto, shared lib, Python proto, SWIG bindings, tests)
make all

# Individual targets
make compile_cpp_proto    # Generate C++ from proto files
make dashapi.so           # Build libdashapi.so
make compile_py_proto     # Generate Python from proto files
make swig                 # Build Python SWIG bindings

# Clean
make clean

# Install
sudo make install

# Build Debian package
dpkg-buildpackage -us -uc -b
```

## Testing

```bash
# Run tests (part of default build)
make test

# Tests are located in misc/tests/
```

## PR Guidelines

- **Signed-off-by**: REQUIRED on all commits (`git commit -s`)
- **CLA**: Sign the Linux Foundation EasyCLA before contributing
- **Single commit per PR**: Squash commits before merge
- **Proto file rules**: Follow the protobuf conventions strictly — one entry + one key per file
- **Reference issues**: Link related GitHub issues or DASH HLD documents

## Dependencies

- **protobuf**: Protocol Buffers compiler and runtime (C++ and Python)
- **SWIG**: For generating Python bindings from C++ code
- **DASH HLD**: Schema follows the [DASH APP DB specification](https://github.com/sonic-net/DASH/blob/main/documentation/general/dash-sonic-hld.md)
- **sonic-dash-ha**: Consumes these proto definitions for HA services

## Gotchas

- **Proto3 optional**: Uses `--experimental_allow_proto3_optional` flag — ensure your protoc version supports it
- **Naming matters**: Redis table/key naming is derived mechanically from proto message names; inconsistent naming breaks DB interop
- **SWIG regeneration**: Changes to C++ utilities require SWIG interface updates in `misc/utils.i`
- **Python package structure**: Generated Python files go into `misc/pypkg/dash_api/` — don't manually edit generated `*_pb2.py` files
- **Backward compatibility**: Changing proto field numbers or removing fields breaks wire compatibility with existing DB entries
- **Build order**: `compile_cpp_proto` must complete before `dashapi.so` and `swig` targets
