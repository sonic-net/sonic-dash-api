#include <gtest/gtest.h>
#include <unistd.h>

#include <iostream>
#include <string>

// The existing suite enumerates "proto". Locate its declared source data in
// both standalone and external-module runfiles before entering the suite.
int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "expected a declared protobuf input path\n";
        return 1;
    }
    const std::string source(argv[1]);
    const auto proto = source.rfind("/proto/");
    const std::string root = proto == std::string::npos ? "." : source.substr(0, proto);
    if (chdir(root.c_str()) != 0) {
        std::cerr << "cannot enter protobuf source root: " << root << '\n';
        return 1;
    }
    for (int i = 1; i + 1 < argc; ++i) {
        argv[i] = argv[i + 1];
    }
    --argc;
    argv[argc] = nullptr;
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
