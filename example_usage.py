from NDOService import l2_service
from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *

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
    "deployment_mode": "...",  # all_site, sigle_site
    "tenant_name": "TN_NUTTAWUT_TEST",
    "schema_name": "TN_NUTTAWUT_TEST_Schema01",
    "filter_name": "FLT_IP",
    "contract_name": "CON_VRF_CUSTOMER",
    "vrf_template_name": "VRF_Contract_Stretch_Template",
    "bd_template_name": "Policy_All_Site_template",
    "vrf_name": "VRF_CUSTOMER",
    "bd_name": "BD_CUSTOMER",
    "anp_name": "AP_CUSTOMER",
    "epg_name": "EPG_CUSTOMER",
}

# INIT
ndo = NDOTemplate(
    params["connection"]["host"],
    params["connection"]["username"],
    params["connection"]["password"],
    params["connection"]["port"],
)


def Example_create_Tenant_Policies():
    # policy template
    ndo.create_tenant_policies_template(
        "TN_NUTTAWUT_TEST_Tenant_Policies_Template", ["SILA", "TLS1"], "TN_NUTTAWUT_TEST"
    )
    # prepare prefixes config for RouteMap
    prefixes_1 = [
        RouteMapPrefix(prefix="10.100.0.0/24"),
        RouteMapPrefix(prefix="10.200.0.0/24"),
    ]
    prefixes_default = [RouteMapPrefix(prefix="0.0.0.0/0", aggregate=True, fromPfxLen=0, toPfxLen=32)]
    rnconfig = RouteMapConfig(
        name="RN_TEST",
        entryList=[
            RouteMapEntry(order=1, name="1", action="permit", prefixes=prefixes_1),
            RouteMapEntry(order=9, name="9", action="permit", prefixes=prefixes_default),
        ],
    )
    ndo.add_route_map_policy("TN_NUTTAWUT_TEST_Tenant_Policies_Template", rnconfig)
    # BFD or OSPF interface settings
    bfdconfig = BFDPolicyConfig(minRxInterval=100, minTxInterval=100, echoRxInterval=100)
    ospfconfig = OSPFIntfConfig()
    ndo.add_l3out_intf_routing_policy(
        "TN_NUTTAWUT_TEST_Tenant_Policies_Template", "IF_POLICY_BFD_100", bfdConfig=bfdconfig
    )
    ndo.add_l3out_intf_routing_policy(
        "TN_NUTTAWUT_TEST_Tenant_Policies_Template", "IF_POLICY_OSPF_DEFAULT", ospfIntfConfig=ospfconfig
    )
    # L3out template
    ndo.create_l3out_template("TN_NUTTAWUT_TEST_SILA_L3Out_Template", "SILA", "TN_NUTTAWUT_TEST")
    ndo.create_l3out_template("TN_NUTTAWUT_TEST_TLS1_L3Out_Template", "TLS1", "TN_NUTTAWUT_TEST")
    # create L3 domain
    ndo.add_domain_to_fabric_policy(
        "SILA1_CL_DOM01_FabricPolicy01", "l3Domains", "L3_DOMAIN_BL_DOM01", "VLAN_SERVER_CL_DOM01_01"
    )
    ndo.add_domain_to_fabric_policy(
        "TLS1_CL_DOM01_FabricPolicy01", "l3Domains", "L3_DOMAIN_BL_DOM01", "VLAN_SERVER_CL_DOM01_01"
    )
    # prepare L3Out config
    l3outconfig = L3OutConfig(
        name="L3OUT_SILA_TEST",
        vrf="VRF_CUSTOMER",
        l3domain="L3_DOMAIN_BL_DOM01",
        nodes=[
            L3OutNodeConfig(nodeID="1101", routerID="10.0.0.1"),
        ],
        routingProtocol="bgp",
        exportRouteMap="RN_TEST",
        interfaces=[
            L3OutInterfaceConfig(
                type="subInterfaces",
                portType="pc",
                primaryV4="10.0.0.1/30",
                encapVal=3000,
                portChannelName="PC_SILA_BL_01",
                bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.0.2", peerAsn=65001)],
            ),
        ],
    )
    ndo.add_l3out_under_template("TN_NUTTAWUT_TEST_SILA_L3Out_Template", l3outconfig)


def Example_Service_Create():
    # EXAMPLE HOW TO CREATE SERVICE
    #
    bd_subnet = BridgeDomainSubnet("10.0.0.1/24", "test from api")
    bd_config = BridgeDomainParams()
    l2_service.create(**params, bd_config=bd_config)


def Example_Fabric_Template():
    # EXAMPLE HOW TO CREATE FABRIC POLICIES/RESOURCES

    # example - To create fabric_policy
    ndo.create_fabric_policy("TLS1_nuttawut_test_by_script", "TLS1")

    # example - To create fabric_resource
    ndo.create_fabric_resource("TLS1_nuttawut_test_by_script", "TLS1")

    # example - To add vlan to pool
    ndo.add_vlans_to_pool("TLS1_nuttawut_test_by_script", "VLAN_SERVER_CL_TEST", [3013, 3014])

    vpc_port_config = VPCResource(
        name="VPC_SILA_TEST",
        node1Details=VPCNodeDetails("3101", "1/14"),
        node2Details=VPCNodeDetails("3102", "1/14"),
    )
    pc_port_config = PortChannelResource(
        name="PC_SILA_TEST",
        node="3102",
        memberInterfaces="1/15,1/16",
    )
    phy_port_config = PhysicalIntfResource(
        name="PHY_TEST",
        nodes=["3102"],
        interfaces="1/17",
    )
    ndo.add_port_to_fabric_resource(
        "SILA_CL_DOM01_ResourcePolicy01", phy_port_config, "INT_SILA1_CL_DOM01_PHY_SERVER_1G"
    )
    ndo.add_port_to_fabric_resource(
        "SILA_CL_DOM01_ResourcePolicy01", pc_port_config, "INT_SILA1_CL_DOM01_VPC_SERVER_1G"
    )
    ndo.add_port_to_fabric_resource(
        "SILA_CL_DOM01_ResourcePolicy01", vpc_port_config, "INT_SILA1_CL_DOM01_VPC_SERVER_1G"
    )


if __name__ == "__main__":
    # Example_Fabric_Template()
    Example_create_Tenant_Policies()
