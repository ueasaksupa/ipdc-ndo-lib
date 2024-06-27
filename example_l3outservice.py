from NDOService import l3out_service
from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *
from NDOService.core.service_parameters import *

""" TODO
This is the example how to call the method to create l2 service on NDO.
"""

ENDPOINTS_EPG_1 = [
    SiteEndpoints(
        name="TLS1",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        endpoints=[
            Endpoint(nodeId="3102", port_type="port", port_name="1/14", port_mode="regular", vlan=2105),
            Endpoint(nodeId="3102", port_type="port", port_name="1/15", port_mode="regular", vlan=2105),
        ],
    ),
    SiteEndpoints(
        name="SILA",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        endpoints=[Endpoint(nodeId="3102", port_type="port", port_name="1/14", port_mode="regular", vlan=2105)],
    ),
]

ENDPOINTS_EPG_2 = [
    SiteEndpoints(
        name="TLS1",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        endpoints=[
            Endpoint(nodeId="3102", port_type="port", port_name="1/16", port_mode="regular", vlan=2105),
            Endpoint(nodeId="3102", port_type="port", port_name="1/17", port_mode="regular", vlan=2105),
        ],
    ),
    SiteEndpoints(
        name="SILA",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        endpoints=[Endpoint(nodeId="3102", port_type="port", port_name="1/15", port_mode="regular", vlan=2105)],
    ),
]

L3OUT_SILA_CONFIG = L3OutConfig(
    name="L3OUT_SILA_TN_NUTTAWUT",
    vrf="VRF_CUST_L3OUT",
    l3domain="L3_DOMAIN_BL_DOM01",
    nodes=[L3OutNodeConfig(nodeID="1101", routerID="10.1.1.1")],
    routingProtocol="bgp",
    importRouteControl=True,
    interfaces=[
        L3OutSubIntPhysicalPort(
            primaryV4="10.0.3.1/30",
            encapVal=3000,
            nodeID="1101",
            portID="1/31",
            bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.3.2", peerAsn=65001)],
        )
    ],
)

L3OUT_TLS1_CONFIG = L3OutConfig(
    name="L3OUT_TLS1_TN_NUTTAWUT",
    vrf="VRF_CUST_L3OUT",
    l3domain="L3_DOMAIN_BL_DOM01",
    nodes=[L3OutNodeConfig(nodeID="1101", routerID="10.2.2.2")],
    routingProtocol="bgp",
    importRouteControl=True,
    interfaces=[
        L3OutSubIntPhysicalPort(
            primaryV4="10.0.3.1/30",
            encapVal=3000,
            nodeID="1101",
            portID="1/31",
            bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.3.2", peerAsn=65001)],
        )
    ],
)

ROUTE_MAP_CONFIG = RouteMapConfig(
    name="RM_TN_NUTTAWUT_TEST",
    entryList=[
        RouteMapEntry(
            order=1,
            name="1",
            action="permit",
            prefixes=[
                RouteMapPrefix(prefix="10.101.0.0/24"),
                RouteMapPrefix(prefix="10.201.0.0/24"),
            ],
            attributes=RouteMapAttributes(
                setAsPath=RouteMapSetAsPath(criteria="prepend", pathASNs=[450001]), setMultiPath=True
            ),
        ),
        RouteMapEntry(
            order=9,
            name="9",
            action="permit",
            prefixes=[RouteMapPrefix(prefix="0.0.0.0/0", aggregate=True, fromPfxLen=0, toPfxLen=32)],
        ),
    ],
)

params = L3OutServiceParameters(
    connection=NDOConnection(host="127.0.0.1", port=10443, username="admin", password="P@ssw0rd"),
    tenant_name="TN_NUTTAWUT",
    tenant_sites=["SILA", "TLS1"],
    schema_name="TN_NUTTAWUT_Schema01",
    tenantPolTemplate=TenantPolicyTenplate(
        name="TN_NUTTAWUT_Tenant_Policies_Template", routemapConfig=ROUTE_MAP_CONFIG
    ),
    l3outTemplatePerSite=[
        L3OutTemplatePerSite(name="TN_NUTTAWUT_TEST_SILA_L3Out_Template", site="SILA", l3outConfig=L3OUT_SILA_CONFIG),
        L3OutTemplatePerSite(name="TN_NUTTAWUT_TEST_TLS1_L3Out_Template", site="TLS1", l3outConfig=L3OUT_TLS1_CONFIG),
    ],
    templates=[
        VRFTemplate(
            name="VRF_Contract_Stretch_Template",
            associatedSites=["SILA", "TLS1"],
            filter_name="FLT_IP",
            contract_name="CON_VRF_CUST_L3OUT",
            vrf_name="VRF_CUST_L3OUT",
        ),
        MultiEPGTemplate(
            name="Policy_Stretch_AllSite_template",
            associatedSites=["SILA", "TLS1"],
            bds=[
                TemplateBridgeDomain(
                    name="BD_L3_CUST_NET_1",
                    linkedVrfTemplate="VRF_Contract_Stretch_Template",
                    linkedVrfName="VRF_CUST_L3OUT",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(name="EPG_L3_SERVER_3_EXT", endpointPerSite=ENDPOINTS_EPG_1),
                    bdConfig=BridgeDomainConfig(
                        subnets=[
                            BridgeDomainSubnet(ip="10.101.0.1/24", description="test from api"),
                        ]
                    ),
                ),
                TemplateBridgeDomain(
                    name="BD_L3_CUST_NET_2",
                    linkedVrfTemplate="VRF_Contract_Stretch_Template",
                    linkedVrfName="VRF_CUST_L3OUT",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(name="EPG_L3_SERVER_4_EXT", endpointPerSite=ENDPOINTS_EPG_2),
                    bdConfig=BridgeDomainConfig(
                        subnets=[
                            BridgeDomainSubnet(ip="10.201.0.1/24", description="test from api"),
                        ]
                    ),
                ),
            ],
            externalEPG=TemplateExternalEPG(
                name="EPG_L3OUT_CUST_NET_3",
                linkedVrfTemplate="VRF_Contract_Stretch_Template",
                linkedVrfName="VRF_CUST_L3OUT",
                associatedL3Out=[
                    EEPGL3OutInfo(
                        site="SILA",
                        l3outTemplate="TN_NUTTAWUT_TEST_SILA_L3Out_Template",
                        l3outName="L3OUT_SILA_TN_NUTTAWUT",
                    ),
                    EEPGL3OutInfo(
                        site="TLS1",
                        l3outTemplate="TN_NUTTAWUT_TEST_TLS1_L3Out_Template",
                        l3outName="L3OUT_TLS1_TN_NUTTAWUT",
                    ),
                ],
            ),
        ),
    ],
)

# INIT ndo object
ndo = NDOTemplate(
    params.connection.host,
    params.connection.username,
    params.connection.password,
    params.connection.port,
)


def Example_Service_Create():
    # EXAMPLE HOW TO CREATE SERVICE
    #
    l3out_service.create(params)


if __name__ == "__main__":
    Example_Service_Create()
