"""Place this component's generated Python modules beside its SWIG bindings."""

def _python_proto_package_impl(ctx):
    python = []
    stubs = []
    for source in ctx.files.srcs:
        if not source.basename.endswith("_pb2.py") and not source.basename.endswith("_pb2.pyi"):
            fail("Expected generated Python protobuf output, got {}".format(source.path))
        output = ctx.actions.declare_file("pypkg/dash_api/" + source.basename)
        ctx.actions.symlink(output = output, target_file = source)
        if output.extension == "py":
            python.append(output)
        else:
            stubs.append(output)
    return [
        DefaultInfo(files = depset(python + stubs)),
        OutputGroupInfo(python = depset(python), pyi = depset(stubs)),
    ]

python_proto_package = rule(
    implementation = _python_proto_package_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = True, mandatory = True),
    },
)
