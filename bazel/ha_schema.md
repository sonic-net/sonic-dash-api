# Original DASH HA schema

`//:ha_schema_sources` exports the three unmodified schema files selected by
sonic-dash-ha commit `5a2508a404569298d8958937dd4de772ba67b129` through its
Git submodule `18a29c1c8a21aeb22a4893c786564acaf8212156`. The HA repository
continues to own its original prost/tonic Rust generators and adapter library.

This older schema is deliberate: `HaScopeConfigKey` assigns `ha_scope_id=1`
and `vdpu_id=2`; the current API assigns `vdpu_id=1` and `ha_scope_id=2`.
The current C++/Python API and its normal `proto_sources` target are unchanged.
A standard Bazel HTTP archive retains the original source revision and integrity.
`//bazel:ha_schema_test` checks every source hash and the actual protoc-produced
wire descriptor. Changing the selected HA schema is a separate product update.
