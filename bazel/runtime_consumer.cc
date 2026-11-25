#include <dash_api/utils.h>
#include <dlfcn.h>
#include <google/protobuf/descriptor.h>
#include <google/protobuf/stubs/common.h>
#include <limits.h>
#include <stdlib.h>

#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

static_assert(GOOGLE_PROTOBUF_VERSION == 3021012, "DASH requires Protobuf 3.21.12 headers");

void check_loaded_file(void *symbol, const char *expected, const char *name) {
    Dl_info info = {};
    char expected_path[PATH_MAX] = {};
    char loaded_path[PATH_MAX] = {};
    if (symbol == nullptr || dladdr(symbol, &info) == 0 || info.dli_fname == nullptr ||
        realpath(expected, expected_path) == nullptr || realpath(info.dli_fname, loaded_path) == nullptr ||
        std::strcmp(expected_path, loaded_path) != 0) {
        throw std::runtime_error(std::string("consumer did not load the selected ") + name);
    }
}

int main(int argc, char **argv) {
    if (argc != 3) {
        std::cerr << "expected the source-built DASH and Protobuf library paths\n";
        return 1;
    }

    try {
        GOOGLE_PROTOBUF_VERIFY_VERSION;
        const std::string table = "DASH_APPLIANCE_TABLE";
        const std::string expected = "sonic/dash.appliance.Appliance";
        if (dash::TableNameToTypeUrl(table) != expected) {
            throw std::runtime_error("C++ table-name conversion failed");
        }
        char output[128] = {};
        if (::TableNameToTypeUrl(table.c_str(), output, sizeof(output)) != expected.size() + 1 || output != expected) {
            throw std::runtime_error("C table-name conversion failed");
        }

        const std::string binary = dash::JsonStringToPbBinary(table, "{}");
        const std::string json = dash::PbBinaryToJsonString(table, binary);
        if (json.find('{') == std::string::npos || json.find('}') == std::string::npos) {
            throw std::runtime_error("protobuf JSON round trip failed");
        }

        check_loaded_file(dlsym(RTLD_DEFAULT, "TableNameToTypeUrl"), argv[1], "libdashapi file");
        // A non-inline Protobuf implementation must come from the selected
        // shared library, rather than a static copy inside DASH or the test.
        check_loaded_file(reinterpret_cast<void *>(&google::protobuf::DescriptorPool::generated_pool),
                          argv[2], "libprotobuf file");
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }

    std::cout << "validated the source-built DASH C++/C interfaces with shared Protobuf 3.21.12\n";
    return 0;
}
