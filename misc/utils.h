#pragma once

#include <string>

namespace dash {

std::string TableNameToTypeUrl(const std::string &table_name);
std::string PbBinaryToJsonString(const std::string &table_name, const std::string &binary);
std::string JsonStringToPbBinary(const std::string &table_name, const std::string &json);

}
