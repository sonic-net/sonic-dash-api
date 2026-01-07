fn main() {
    let proto_path = "../../proto".to_string();

    let mut proto_config = prost_build::Config::new();

    proto_config.type_attribute("dash.ha_scope_config.HaScopeConfig", "use sonicdb_derive::SonicDb;");

    proto_config.type_attribute("dash.ha_scope_config.HaScopeConfig", "use prost::Message;");

    proto_config.type_attribute("dash.ha_scope_config.HaScopeConfig", "#[derive(SonicDb)]");

    proto_config.type_attribute(
        "dash.ha_scope_config.HaScopeConfig",
        "#[sonicdb(table_name = \"DASH_HA_SCOPE_CONFIG_TABLE\", key_separator = \":\", db_name = \"APPL_DB\", is_proto = \"true\",)]",
    );

    proto_config.type_attribute(
        "dash.ha_scope_config.HaScopeConfig",
        "#[derive(serde::Serialize, serde::Deserialize)]",
    );

    proto_config.type_attribute(
        "dash.ha_scope_config.DesiredHaState",
        "#[derive(strum_macros::Display)]",
    );

    proto_config.type_attribute("dash.ha_set_config.HaSetConfig", "use sonicdb_derive::SonicDb;");

    proto_config.type_attribute("dash.ha_set_config.HaSetConfig", "use prost::Message;");

    proto_config.type_attribute("dash.ha_set_config.HaSetConfig", "#[derive(SonicDb)]");

    proto_config.type_attribute(
        "dash.ha_set_config.HaSetConfig",
        "#[sonicdb(table_name = \"DASH_HA_SET_CONFIG_TABLE\", key_separator = \":\", db_name = \"APPL_DB\", is_proto = \"true\",)]",
    );

    proto_config.type_attribute(
        "dash.ha_set_config.HaSetConfig",
        "#[derive(serde::Serialize, serde::Deserialize)]",
    );

    proto_config.type_attribute(
        "dash.types.IpAddress",
        "#[derive(serde::Serialize, serde::Deserialize)]",
    );

    proto_config
        .compile_protos(
            &[
                format!("{proto_path}/ha_set_config.proto"),
                format!("{proto_path}/ha_scope_config.proto"),
                format!("{proto_path}/types.proto"),
            ],
            &[proto_path],
        )
        .unwrap();

    // --- PATCH GENERATED CODE FOR SERDE ON ONEOF ENUMS ---
    let out_dir = std::env::var("OUT_DIR").unwrap();
    let types_rs = std::path::Path::new(&out_dir).join("dash.types.rs");
    let content = std::fs::read_to_string(&types_rs).unwrap();
    let patched = content.replace(
        "#[derive(Clone, PartialEq, ::prost::Oneof)]\n    pub enum Ip {",
        "#[derive(Clone, PartialEq, ::prost::Oneof)]\n    #[derive(serde::Serialize, serde::Deserialize)]\n    pub enum Ip {"
    );
    std::fs::write(&types_rs, patched).unwrap();
}
