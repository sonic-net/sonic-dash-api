#include <utils.h>

#include <string>
#include <map>
#include <set>
#include <vector> 
#include <utility>

#include <boost/filesystem.hpp>

#include <gtest/gtest.h>

using namespace std;
using namespace dash;

#ifndef PROTO_PATH
#define PROTO_PATH "../../proto"
#endif

TEST(Utils, ValidUrlConversion)
{
    map<string, string> valid_conversion_mapping = {
        {"sonic/dash.acl_group.AclGroup", "DASH_ACL_GROUP_TABLE"},
        {"sonic/dash.acl_in.AclIn", "DASH_ACL_IN_TABLE"},
        {"sonic/dash.acl_out.AclOut", "DASH_ACL_OUT_TABLE"},
        {"sonic/dash.acl_rule.AclRule", "DASH_ACL_RULE_TABLE"},
        {"sonic/dash.appliance.Appliance", "DASH_APPLIANCE_TABLE"},
        {"sonic/dash.eni.Eni", "DASH_ENI_TABLE"},
        {"sonic/dash.eni_route.EniRoute", "DASH_ENI_ROUTE_TABLE"},
        {"sonic/dash.meter_policy.MeterPolicy", "DASH_METER_POLICY_TABLE"},
        {"sonic/dash.meter_rule.MeterRule", "DASH_METER_RULE_TABLE"},
        {"sonic/dash.meter.Meter", "DASH_METER_TABLE"},
        {"sonic/dash.pa_validation.PaValidation", "DASH_PA_VALIDATION_TABLE"},
        {"sonic/dash.prefix_tag.PrefixTag", "DASH_PREFIX_TAG_TABLE"},
        {"sonic/dash.qos.Qos", "DASH_QOS_TABLE"},
        {"sonic/dash.route_group.RouteGroup", "DASH_ROUTE_GROUP_TABLE"},
        {"sonic/dash.route_rule.RouteRule", "DASH_ROUTE_RULE_TABLE"},
        {"sonic/dash.route_type.RouteType", "DASH_ROUTE_TYPE_TABLE"},
        {"sonic/dash.route.Route", "DASH_ROUTE_TABLE"},
        {"sonic/dash.routing_appliance.RoutingAppliance", "DASH_ROUTING_APPLIANCE_TABLE"},
        {"sonic/dash.tunnel.Tunnel", "DASH_TUNNEL_TABLE"},
        {"sonic/dash.vnet_mapping.VnetMapping", "DASH_VNET_MAPPING_TABLE"},
        {"sonic/dash.vnet.Vnet", "DASH_VNET_TABLE"},
        {"sonic/dash.ha_scope.HaScope", "DASH_HA_SCOPE_TABLE"},
        {"sonic/dash.ha_set.HaSet", "DASH_HA_SET_TABLE"},
        {"sonic/dash.ha_set_config.HaSetConfig", "DASH_HA_SET_CONFIG_TABLE"},
        {"sonic/dash.ha_scope_config.HaScopeConfig", "DASH_HA_SCOPE_CONFIG_TABLE"},
        {"sonic/dash.ha_set_state.HaSetState", "DASH_HA_SET_STATE_TABLE"},
        {"sonic/dash.ha_scope_state.HaScopeState", "DASH_HA_SCOPE_STATE_TABLE"},
    };
    set<string> ignore_files = {
        "types.proto"
    };

    // Check valid mapping include all proto files
    for (auto &p : boost::filesystem::directory_iterator(PROTO_PATH))
    {
        if (p.path().extension() == ".proto" 
            && ignore_files.find(p.path().filename().string()) == ignore_files.end())
        {
            auto file_name_without_extension = p.path().filename().string().substr(0, p.path().filename().string().size() - 6);
            auto type_url = "sonic/dash." + file_name_without_extension + ".";
            bool exist = false;
            for (auto &pair : valid_conversion_mapping)
            {
                if (pair.first.find(type_url) == 0)
                {
                    exist = true;
                    break;
                }
            }
            EXPECT_TRUE(exist) << "Missing type url for " << p.path().filename().string();
        }
    }

    for (auto &pair : valid_conversion_mapping)
    {
        EXPECT_EQ(pair.first, TableNameToTypeUrl(pair.second));
    }
}

TEST(Utils, InvalidUrlConversion)
{
    EXPECT_THROW(TableNameToTypeUrl(""), runtime_error);
    EXPECT_THROW(TableNameToTypeUrl("DASH_ROUTE"), runtime_error);
    EXPECT_THROW(TableNameToTypeUrl("DASH_ABC_ROUTE"), runtime_error);
}

TEST(Utils, ValidJsonConversion)
{
    string jsonStr;
    EXPECT_NO_THROW(jsonStr = PbBinaryToJsonString("DASH_ROUTE_RULE_TABLE", ""));
    EXPECT_FALSE(jsonStr.empty());
    EXPECT_NO_THROW(JsonStringToPbBinary("DASH_ROUTE_RULE_TABLE", jsonStr));
}

TEST(Utils, InvalidJsonConversion)
{
    EXPECT_THROW(JsonStringToPbBinary("DASH_ROUTE_RULE_TABLE", "invalid json"), runtime_error);
}

TEST(Utils, CInterface)
{
    char type_url[256];
    EXPECT_EQ(TableNameToTypeUrl("DASH_ROUTE_RULE_TABLE", type_url, sizeof(type_url)), 32);
    EXPECT_EQ(string(type_url), "sonic/dash.route_rule.RouteRule");

    const std::string json_str1 = 
    "{\n"
    " \"action_type\": \"ROUTING_TYPE_UNSPECIFIED\",\n"
    " \"routing_type\": \"ROUTING_TYPE_VNET\",\n"
    " \"vnet\": \"Vnet2\"\n"
    "}\n";

    char binary[256] = {0};
    size_t binary_size = 0;
    EXPECT_NO_THROW(binary_size = JsonStringToPbBinary("DASH_ROUTE_TABLE", json_str1.c_str(), binary, sizeof(binary)));
    EXPECT_GT(binary_size, 0);

    char json[256] = {0};
    EXPECT_NO_THROW(PbBinaryToJsonString("DASH_ROUTE_TABLE", binary, binary_size, json, sizeof(json)));
    EXPECT_EQ(string(json), json_str1);

    const std::string json_str2 =
    "{\n"
    " \"sip\": {\n"
    "  \"ipv4\": 16777482\n"
    " },\n"
    " \"vm_vni\": 4321,\n"
    " \"local_region_id\": 100,\n"
    " \"outbound_direction_lookup\": \"dst_mac\"\n"
    "}\n";

    binary_size = 0;
    EXPECT_NO_THROW(binary_size = JsonStringToPbBinary("DASH_APPLIANCE_TABLE", json_str2.c_str(), binary, sizeof(binary)));
    EXPECT_GT(binary_size, 0);

    EXPECT_NO_THROW(PbBinaryToJsonString("DASH_APPLIANCE_TABLE", binary, binary_size, json, sizeof(json)));
    EXPECT_EQ(string(json), json_str2);
}
