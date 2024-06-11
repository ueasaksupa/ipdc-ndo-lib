from NDOService import l2_service
from NDOService.core.ndo_connector import NDOTenantTemplate

"""
This is the example how to call the method to create l2 service on NDO.
Required params:
    connection:
        host: NDO host ip/hostname
        username: NDO username
        password: NDO password
        port: NDO port [default 443]
    sites: array of dictionary of site.
        name: site name
        endpoints: Array of endpoint in the selected site
            node: node name
            port_type: either vpc or port
            port_name: port name ex. eth1/13
            port_mode: port mode select one of the [regular, native, untagged]
            vlan: vlan number
        epg_phy_domain: Physical domain for EPG
    tenant_name: Tenant name
    schema_name: Schema name
    vrf_template_name: Name of the template for VRF
    bd_template_name: Name of the template for BD
    vrf_name: VRF name
    bd_name: Bridge-domaon name
    anp_name: Application profile name
    epg_name: EPG name
"""


params = {
    "connection": {"host": "127.0.0.1", "port": 10443, "username": "admin", "password": "P@ssw0rd"},
    "sites": [
        {
            "name": "TLS1",
            "endpoints": [
                {"node": "3101", "port_type": "port", "port_name": "eth1/13", "port_mode": "regular", "vlan": 2103}
            ],
            "epg_phy_domain": "PHY_DOMAIN_SERVER_CL_DOM01_01",
        },
        {
            "name": "SILA",
            "endpoints": [
                {"node": "3101", "port_type": "port", "port_name": "eth1/13", "port_mode": "regular", "vlan": 2103}
            ],
            "epg_phy_domain": "PHY_DOMAIN_SERVER_CL_DOM01_01",
        },
    ],
    "tenant_name": "TN_NUTTAWUT_TEST",
    "schema_name": "TN_NUTTAWUT_TEST_Schema01",
    "vrf_template_name": "VRF_Contract_Stretch_Template",
    "bd_template_name": "Policy_All_Site_template",
    "vrf_name": "VRF_CUSTOMER",
    "bd_name": "BD_CUSTOMER",
    "anp_name": "AP_CUSTOMER",
    "epg_name": "EPG_CUSTOMER",
}

l2_service.create(**params)

ndo = NDOTenantTemplate(
    params["connection"]["host"],
    params["connection"]["username"],
    params["connection"]["password"],
    params["connection"]["port"],
)
ndo.create_fabric_policy("TLS1_nuttawut_test_by_script", "TLS1")
ndo.create_fabric_resource("TLS1_nuttawut_test_by_script", "TLS1")
ndo.add_vlans_to_pool("TLS1_nuttawut_test_by_script", "VLAN_SERVER_CL_TEST", [3013, 3014])
