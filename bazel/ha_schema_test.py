"""Verify HA's original source bytes and protobuf wire-field identities."""
import hashlib
from pathlib import Path
import sys
from google.protobuf import descriptor_pb2

EXPECTED = {
    "ha_set_config.proto": "3aac48716f7e82c5ed231ec04cc1e965ab47aecd5785ea9d7bec5cdd3b93d1ea",
    "ha_scope_config.proto": "a5df9f029dd4b10fb8933eab353b0612e158323be43264c3ec6124ab074d16af",
    "types.proto": "0b1644d63d353923f33aa4e561f7181119db49715e0f745063cbe3a81f2c73a9",
}

sources = {Path(name).name: Path(name) for name in sys.argv[2:]}
assert set(sources) == set(EXPECTED), sources
for name, digest in EXPECTED.items():
    assert hashlib.sha256(sources[name].read_bytes()).hexdigest() == digest, name
schema = descriptor_pb2.FileDescriptorSet.FromString(Path(sys.argv[1]).read_bytes())
files = {file.name: file for file in schema.file}
assert set(files) == set(EXPECTED), files.keys()
key = next(message for message in files["ha_scope_config.proto"].message_type if message.name == "HaScopeConfigKey")
assert [(field.name, field.number, field.type) for field in key.field] == [
    ("ha_scope_id", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
    ("vdpu_id", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
]
print("Three exact 18a29c schema sources and original HA wire field numbers verified")
