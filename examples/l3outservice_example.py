from NDOService.services.l3out_service import create_service
from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *
from NDOService.core.service_parameters import *

"""
This is the example how to call the method to create l3 service on NDO.
"""

ENDPOINTS_EPG_1 = [
    SiteStaticPorts(
        sitename="TLS1",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        staticPorts=[
            StaticPortPhy(nodeId="3102", port_name="1/14", port_mode="regular", vlan=2105),
            StaticPortPhy(nodeId="3102", port_name="1/15", port_mode="regular", vlan=2105),
        ],
    ),
    SiteStaticPorts(
        sitename="SILA",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        staticPorts=[StaticPortPhy(nodeId="3102", port_name="1/14", port_mode="regular", vlan=2105)],
    ),
]

ENDPOINTS_EPG_2 = [
    SiteStaticPorts(
        sitename="TLS1",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        staticPorts=[
            StaticPortPhy(nodeId="3102", port_name="1/16", port_mode="regular", vlan=2105),
            StaticPortPhy(nodeId="3102", port_name="1/17", port_mode="regular", vlan=2105),
        ],
    ),
    SiteStaticPorts(
        sitename="SILA",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        staticPorts=[StaticPortPhy(nodeId="3102", port_name="1/15", port_mode="regular", vlan=2105)],
    ),
]

L3OUT_SILA_CONFIG = L3OutConfig(
    name="L3OUT_SILA_TN_NUTTAWUT",
    vrf="VRF_CUST_L3OUT",
    l3domain="L3_DOMAIN_BL_DOM01",
    nodes=[
        L3OutNodeConfig(
            nodeID="1101",
            routerID="10.1.1.1",
            staticRoutes=[
                L3OutStaticRouteConfig(prefix="10.100.0.0/24", nextHops=[L3OutStaticRouteNextHop(nextHopIP="1.1.1.1")])
            ],
        )
    ],
    routingProtocol="bgp",
    exportRouteMap="RM_SILA_TN_NUTTAWUT",
    interfaces=[
        L3OutSubIntPortChannel(
            primaryV4="10.0.2.1/30",
            encapVal=3000,
            portChannelName="PC_SILA_BL_01",
            bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.2.2", peerAsn=65001)],
        ),
    ],
    interfaceRoutingPolicy="IF_POLICY_SILA_BFD_100",
)

L3OUT_TLS1_CONFIG = L3OutConfig(
    name="L3OUT_TLS1_TN_NUTTAWUT",
    vrf="VRF_CUST_L3OUT",
    l3domain="L3_DOMAIN_BL_DOM01",
    nodes=[L3OutNodeConfig(nodeID="1101", routerID="10.2.2.2")],
    routingProtocol="bgp",
    exportRouteMap="RM_TLS1_TN_NUTTAWUT",
    importRouteControl=True,
    importRouteMap="RM_TLS1_TN_NUTTAWUT",
    interfaces=[
        L3OutSubIntPortChannel(
            primaryV4="10.0.2.1/30",
            encapVal=3000,
            portChannelName="PC_TLS1_BL_01",
            bgpPeers=[L3OutBGPPeerConfig(peerAddressV4="10.0.2.2", peerAsn=65001)],
        ),
    ],
    interfaceRoutingPolicy="IF_POLICY_TLS1_BFD_100",
)

ROUTE_MAP_CONFIG_S = RouteMapConfig(
    name="RM_SILA_TN_NUTTAWUT",
    entryList=[
        RouteMapEntry(
            order=1,
            name="1",
            action="permit",
            prefixes=[RouteMapPrefix(prefix="10.201.0.0/24")],
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

ROUTE_MAP_CONFIG_T = RouteMapConfig(
    name="RM_TLS1_TN_NUTTAWUT",
    entryList=[
        RouteMapEntry(
            order=1,
            name="1",
            action="permit",
            prefixes=[RouteMapPrefix(prefix="10.101.0.0/24")],
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

params = ServiceL3OutParameters(
    tenant_name="TN_NUTTAWUT",
    tenant_sites=["SILA", "TLS1"],
    schema_name="TN_NUTTAWUT_Schema01",
    tenantPolTemplates=[
        TenantPolicyTemplate(name="TN_NUTTAWUT_Tenant_Policies_SILA", site="SILA", routemapConfig=ROUTE_MAP_CONFIG_S),
        TenantPolicyTemplate(name="TN_NUTTAWUT_Tenant_Policies_TLS1", site="TLS1", routemapConfig=ROUTE_MAP_CONFIG_T),
    ],
    l3outTemplatePerSite=[
        L3OutTemplatePerSite(name="TN_NUTTAWUT_TEST_SILA_L3Out_Template", site="SILA", l3outConfig=L3OUT_SILA_CONFIG),
        L3OutTemplatePerSite(name="TN_NUTTAWUT_TEST_TLS1_L3Out_Template", site="TLS1", l3outConfig=L3OUT_TLS1_CONFIG),
    ],
    templates=[
        VRFTemplate(
            name="VRF_CONTRACT_STRETCHED_TEMPLATE",
            associatedSites=["SiteA"],
            vrf_name="VRF_CUSTOMER",
            filter_name="FLT_IP",
            contract_name="CON_VRF_CUSTOMER",
        ),
        EPGsTemplate(
            name="POLICY_SITEA",
            associatedSites=["SiteA"],
            bds=[
                TemplateBridgeDomain(
                    name="BD_L3OUT_CUST_NET_1",
                    linkedVrfTemplate="VRF_CONTRACT_STRETCHED_TEMPLATE",
                    linkedVrfName="VRF_CUST_L3OUT",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(name="EPG_L3_SERVER_3_EXT", staticPortPerSite=ENDPOINTS_EPG_1),
                    bdConfig=BridgeDomainConfig(
                        arpFlood=False, subnets=[BridgeDomainSubnet(ip="10.101.0.1/24", description="test from api")]
                    ),
                ),
                TemplateBridgeDomain(
                    name="BD_L3OUT_CUST_NET_2",
                    linkedVrfTemplate="VRF_CONTRACT_STRETCHED_TEMPLATE",
                    linkedVrfName="VRF_CUST_L3OUT",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(name="EPG_L3_SERVER_4_EXT", staticPortPerSite=ENDPOINTS_EPG_2),
                    bdConfig=BridgeDomainConfig(
                        arpFlood=False, subnets=[BridgeDomainSubnet(ip="10.201.0.1/24", description="test from api")]
                    ),
                ),
            ],
            externalEPG=TemplateExternalEPG(
                name="EPG_L3OUT_CUST_NET_3",
                linkedVrfTemplate="VRF_CONTRACT_STRETCHED_TEMPLATE",
                linkedVrfName="VRF_CUST_L3OUT",
                associatedL3Out=[
                    ExternalEpgToL3OutBinding(
                        site="SILA",
                        l3outTemplate="TN_NUTTAWUT_TEST_SILA_L3Out_Template",
                        l3outName="L3OUT_SILA_TN_NUTTAWUT",
                    ),
                    ExternalEpgToL3OutBinding(
                        site="TLS1",
                        l3outTemplate="TN_NUTTAWUT_TEST_TLS1_L3Out_Template",
                        l3outName="L3OUT_TLS1_TN_NUTTAWUT",
                    ),
                ],
            ),
        ),
    ],
)


if __name__ == "__main__":
    ndo = NDOTemplate(host="127.0.0.1", port=10443, username="admin", password="P@ssw0rd", delay=0.5)
    create_service(ndo, params)
