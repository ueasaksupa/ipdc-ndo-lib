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
    # prepare L3Out config
    l3outconfig = L3OutConfig(
        name="L3OUT_SILA_TEST",
        vrf="VRF_CUSTOMER",
        l3domain="L3_DOMAIN_BL_DOM01",
        nodes=[
            L3OutNodeConfig(
                nodeID="1101",
                routerID="10.0.0.1",
            ),
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
                secondaryAddrs=["8.1.1.1/16"],
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

    EEPG_L3OUT_INFO = [
        ExternalEpgToL3OutBinding(
            site="SILA",
            l3outTemplate="TN_NUTTAWUT_TEST_SILA_L3Out_Template",
            l3outName="L3OUT_SILA_TEST",
        ),
        ExternalEpgToL3OutBinding(
            site="TLS1",
            l3outTemplate="TN_NUTTAWUT_TEST_TLS1_L3Out_Template",
            l3outName="L3OUT_TLS_TN_NUTTAWUT",
        ),
    ]
    ndo.create_ext_epg_under_template(
        schema=schema,
        template_name="POLICY_SITEA",
        epg_name="EPG_L3OUT_CUSTOMER",
        linked_vrf_name="VRF_CUST_L3OUT",
        linked_vrf_template="VRF_CONTRACT_STRETCHED_TEMPLATE",
        l3outToSiteInfo=EEPG_L3OUT_INFO,
        epg_desc="external epg for test",
        eepg_subnets=[ExternalEpgSubnet(ip="77.1.1.0/24")],
    )
    ndo.save_schema(schema)
