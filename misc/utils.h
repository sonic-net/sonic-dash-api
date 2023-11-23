#pragma once

#include <string>

#ifdef __cplusplus

namespace dash {

std::string TableNameToTypeUrl(const std::string &table_name);
std::string PbBinaryToJsonString(const std::string &table_name, const std::string &binary);
std::string JsonStringToPbBinary(const std::string &table_name, const std::string &json);

}

#endif

extern "C" {

size_t TableNameToTypeUrl(const char *table_name, char *type_url, size_t buffer_size);
size_t PbBinaryToJsonString(const char *table_name, const char *binary, char *json, size_t buffer_size);
size_t JsonStringToPbBinary(const char *table_name, const char *json, char *binary, size_t buffer_size);

}
