from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *


params = {
    "connection": {"host": "127.0.0.1", "port": 10443, "username": "admin", "password": "P@ssw0rd"},
}

# INIT
ndo = NDOTemplate(
    params["connection"]["host"],
    params["connection"]["username"],
    params["connection"]["password"],
    params["connection"]["port"],
)


def Example_L3Out():
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
    ndo.add_domain_to_fabric_policy("TLS1_CL_DOM01_FabricPolicy01", "l3Domains", "L3_DOMAIN_BL_DOM02")
    # prepare L3Out config
    l3outconfig = L3OutConfig(
        name="L3OUT_SILA_TEST",
        vrf="VRF_CUSTOMER",
        l3domain="L3_DOMAIN_BL_DOM01",
        nodes=[
            L3OutNodeConfig(nodeID="1101", routerID="10.0.0.1"),
        ],
        routingProtocol="bgp",
        importRouteControl=True,
        interfaces=[
            L3OutIntPortChannel(
                primaryV4="10.0.0.1/30",
                portChannelName="PC_SILA_BL_01",
                bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.0.2", peerAsn=65001)],
            ),
            L3OutIntPhysicalPort(
                primaryV4="10.0.1.1/30",
                nodeID="1101",
                portID="1/30",
                bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.1.2", peerAsn=65001)],
            ),
            L3OutSubIntPortChannel(
                primaryV4="10.0.2.1/30",
                encapVal=3000,
                portChannelName="PC_SILA_BL_02",
                bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.2.2", peerAsn=65001)],
            ),
            L3OutSubIntPhysicalPort(
                primaryV4="10.0.3.1/30",
                encapVal=3000,
                nodeID="1101",
                portID="1/31",
                bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.3.2", peerAsn=65001)],
            ),
            L3OutSVIPortChannel(
                primaryV4="10.0.4.1/30",
                encapVal=2111,
                portChannelName="PC_SILA_BL_03",
                bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.4.2", peerAsn=65001)],
            ),
            L3OutSVIPhysicalPort(
                primaryV4="10.0.5.1/30",
                encapVal=2222,
                nodeID="1101",
                portID="1/32",
                bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.5.2", peerAsn=65001)],
            ),
        ],
    )
    ndo.add_l3out_under_template("TN_NUTTAWUT_TEST_SILA_L3Out_Template", l3outconfig)
    schema = ndo.find_schema_by_name("TN_NUTTAWUT_TEST_Schema01")
    if schema is None:
        return

    ndo.create_ext_epg_under_template(
        schema,
        "Policy_All_Site_template",
        "EPG_L3OUT_CUSTOMER",
        "VRF_CUSTOMER",
        "VRF_Contract_Stretch_Template",
        [
            {
                "site": "SILA",
                "l3OutTemplateName": "TN_NUTTAWUT_TEST_SILA_L3Out_Template",
                "l3outName": "L3OUT_SILA_TEST",
            },
            {
                "site": "TLS1",
                "l3OutTemplateName": "TN_NUTTAWUT_TEST_TLS1_L3Out_Template",
                "l3outName": "L3OUT_TLS_TN_NUTTAWUT",
            },
        ],
        "external epg for test",
    )
    ndo.save_schema(schema)


def Example_create_Tenant_Policies():
    # create tenant policy template
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
        name="RM_TN_NUTTAWUT_TEST",
        entryList=[
            RouteMapEntry(
                order=1,
                name="1",
                action="permit",
                prefixes=prefixes_1,
                attributes=RouteMapAttributes(
                    setAsPath=RouteMapSetAsPath(criteria="prepend", pathASNs=[450001]), setMultiPath=True
                ),
            ),
            RouteMapEntry(order=9, name="9", action="permit", prefixes=prefixes_default),
        ],
    )
    ndo.add_route_map_policy_under_template("TN_NUTTAWUT_TEST_Tenant_Policies_Template", rnconfig)
    # BFD or OSPF interface settings
    bfdconfig = BFDPolicyConfig(minRxInterval=100, minTxInterval=100, echoRxInterval=100)
    ospfconfig = OSPFIntfConfig()
    ndo.add_l3out_intf_routing_policy(
        "TN_NUTTAWUT_TEST_Tenant_Policies_Template", "IF_POLICY_BFD_100", bfdConfig=bfdconfig
    )
    ndo.add_l3out_intf_routing_policy(
        "TN_NUTTAWUT_TEST_Tenant_Policies_Template", "IF_POLICY_OSPF_DEFAULT", ospfIntfConfig=ospfconfig
    )


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
    # Example_L3Out()
