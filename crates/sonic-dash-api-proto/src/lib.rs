use crate::types::ip_address::Ip;
use crate::types::IpAddress;
use std::collections::HashMap;
use swss_common::CxxString;

pub mod ha_scope_config {
    include!(concat!(env!("OUT_DIR"), "/dash.ha_scope_config.rs"));
}

pub mod ha_set_config {
    include!(concat!(env!("OUT_DIR"), "/dash.ha_set_config.rs"));
}

pub mod types {
    include!(concat!(env!("OUT_DIR"), "/dash.types.rs"));
}

pub fn ip_to_string(ip: &IpAddress) -> String {
    match &ip.ip {
        Some(Ip::Ipv4(addr)) => std::net::Ipv4Addr::from(*addr).to_string(),
        Some(Ip::Ipv6(addr)) => {
            use std::net::Ipv6Addr;
            let bytes: [u8; 16] = addr.clone().try_into().unwrap_or([0; 16]);
            Ipv6Addr::from(bytes).to_string()
        }
        _ => "".to_string(),
    }
}

pub fn decode_from_field_values<T: for<'de> serde::Deserialize<'de>>(
    field_values: &HashMap<String, CxxString>,
) -> Result<T, serde_json::Error> {
    let json_str = field_values.get("json").unwrap();
    let s = json_str.to_string_lossy().into_owned();
    serde_json::from_str(&s)
}
