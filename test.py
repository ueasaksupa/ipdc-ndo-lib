from NDOService.services.simple_service import create_service
from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *
from NDOService.core.service_parameters import *
import pprint

ndo = NDOTemplate(host="172.31.1.24", port=443, username="admin", password="P@ssw0rd")


schema = ndo.find_schema_by_name("TN_NUTTAWUT_Schema01")
if not schema:
    print("Schema not found")
    exit(1)

#
# BD TEST
############################################################################################################


# tname = "POLICY_SITEA"
# bdname = "BD_REPLEACE_TEST"
# # linkedVrfSchema="....", # if you want to link to another schema
# linkedVrfTemplate = "VRF_CONTRACT_STRETCHED_TEMPLATE"
# linkedVrfName = "VRF_CUSTOMER"
# bdConfig = BridgeDomainConfig(
#     unicastRouting=True,
#     l2Stretch=False,
#     l2UnknownUnicast="flood",
#     description="REPLACE OLD ONE",
#     perSiteSubnet=[("SiteA", BridgeDomainSubnet(ip="10.1.2.1/24"))],
# )

# ndo.create_bridge_domain_under_template(
#     schema=schema,
#     template_name=tname,
#     linked_vrf_template=linkedVrfTemplate,
#     linked_vrf_name=linkedVrfName,
#     bd_name=bdname,
#     bd_config=bdConfig,
#     replace=True,
# )

# ndo.save_schema(schema)

#
# ROUTE MAP TEST
############################################################################################################


# ROUTE_MAP_CONFIG = RouteMapConfig(
#     name="RM_SiteA_TN_NUTTAWUT",
#     entryList=[
#         RouteMapEntry(
#             order=2,
#             name="2",
#             action="permit",
#             prefixes=[RouteMapPrefix(prefix="20.101.0.0/24")],
#         ),
#         RouteMapEntry(
#             order=9,
#             name="9",
#             action="permit",
#             prefixes=[RouteMapPrefix(prefix="0.0.0.0/0", aggregate=True, fromPfxLen=0, toPfxLen=32)],
#         ),
#     ],
# )

# ndo.add_route_map_policy_under_template(
#     template_name="TN_NUTTAWUT_Tenant_Policies_SiteA", rnConfig=ROUTE_MAP_CONFIG, replace=True
# )

#
# L3OUT TEST
############################################################################################################


# l3outconfig = L3OutConfig(
#     name="L3OUT_SITEA_TEST_2",
#     vrf="VRF_TEST_NUTTAWUT",
#     l3domain="L3_DOMAIN_BL_DOM01",
#     nodes=[
#         L3OutNodeConfig(
#             nodeID="3102",
#             routerID="10.0.0.2",
#         ),
#     ],
#     routingProtocol="bgp",
#     importRouteControl=True,
#     importRouteMap="RM_L3OUT_TEST_BGP_IN",
#     exportRouteMap="RM_L3OUT_TEST_BGP_OUT",
#     interfaces=[
#         # L3OutIntPhysicalPort(
#         #     primaryV4="20.0.1.2/30",
#         #     secondaryAddrs=["15.1.1.1/16"],
#         #     nodeID="3102",
#         #     portID="1/31",
#         #     bgpPeers=[
#         #         L3OutBGPPeerConfig(
#         #             peerAddressV4="10.10.10.2",
#         #             peerAsn=65001,
#         #             localAsn=6500011,
#         #             localAsnConfig="no-prepend",
#         #             importRouteMap="RM_L3OUT_TEST_BGP_IN",
#         #             exportRouteMap="RM_L3OUT_TEST_BGP_OUT",
#         #         )
#         #     ],
#         # ),
#         L3OutIntPhysicalPort(
#             primaryV4="20.0.2.2/30",
#             secondaryAddrs=["15.1.2.1/16"],
#             nodeID="3102",
#             portID="1/32",
#             bgpPeers=[
#                 L3OutBGPPeerConfig(
#                     peerAddressV4="10.10.12.2",
#                     peerAsn=65001,
#                     localAsn=6500011,
#                     localAsnConfig="no-prepend",
#                 )
#             ],
#         ),
#     ],
#     interfaceRoutingPolicy="L3OUT_BFD_100",
# )

# ndo.add_l3out_under_template("TN_NUTTAWUT_SiteA_L3Out_Template", l3outconfig, operation="merge")


#
# External EPG TEST
############################################################################################################


# EEPG_L3OUT_INFO = [
#     ExternalEpgToL3OutBinding(
#         site="SiteA",
#         l3outTemplate="TN_NUTTAWUT_SiteA_L3Out_Template",
#         l3outName="L3OUT_SITEA_TEST",
#     )
# ]
# ndo.create_ext_epg_under_template(
#     schema=schema,
#     template_name="POLICY_SITEA",
#     epg_name="EPG_L3OUT_CUSTOMER",
#     linked_vrf_name="VRF_CUSTOMER",
#     linked_vrf_template="VRF_CONTRACT_STRETCHED_TEMPLATE",
#     l3outToSiteInfo=EEPG_L3OUT_INFO,
#     epg_desc="external epg for test edited",
#     replace=False,
# )

# ndo.change_ext_epg_l3out_binding(
#     schema=schema, template_name="POLICY_SITEA", epg_name="EPG_L3OUT_CUSTOMER", l3outToSiteInfo=EEPG_L3OUT_INFO
# )

# ndo.save_schema(schema)

#
# Fabric Resource TEST
################################################################################################

# ndo.create_fabric_resource("NUTTAWUT_Fabric_resource", "SiteA")
# ndo.add_port_to_fabric_resource(
#     "NUTTAWUT_Fabric_resource",
#     port_config=PortChannelResource(
#         name="TEST_30_31",
#         node="3102",
#         memberInterfaces="1/30-31",
#         interfaceDescriptions=[
#             IntfDescription(nodeID="3102", interfaceID="1/30", description="TEST_30"),
#             IntfDescription(nodeID="3102", interfaceID="1/31", description="TEST_31"),
#         ],
#     ),
#     intf_policy_name="INT_SiteA_PC_SPAN_SWITCH",
# )

# ndo.add_port_to_fabric_resource(
#     "NUTTAWUT_Fabric_resource",
#     port_config=PhysicalIntfResource(
#         name="TEST_34",
#         nodes=["3102"],
#         interfaces="1/34",
#         # interfaceDescriptions=[
#         #     IntfDescription(interfaceID="1/34", description="TEST_34"),
#         # ],
#     ),
#     intf_policy_name="INT_SERVER_1G",
# )


#
# test adding static rotue prefix to existing l3out
# prefixes = [L3OutStaticRouteConfig(prefix="10.2.2.0/24", nextHops=[L3OutStaticRouteNextHop(nextHopIP="1.1.1.1")])]
# ndo.add_static_route_prefixes_to_l3out(
#     "TN_NUTTAWUT_SiteA_L3Out_Template", "L3OUT_TEST_DOM01_STATIC_01", "3103", prefixes
# )


#
# test merge route map
# ROUTE_MAP_CONFIG = RouteMapConfig(
#     name="RM_SiteA_TN_NUTTAWUT",
#     entryList=[
#         RouteMapEntry(
#             order=5,
#             name="5",
#             action="permit",
#             prefixes=[RouteMapPrefix(prefix="10.111.222.0/24")],
#             # attributes=RouteMapAttributes(setAsPath=RouteMapSetAsPath(criteria="prepend", pathASNs=[65111])),
#         ),
#         RouteMapEntry(
#             order=9,
#             name="9",
#             action="permit",
#             prefixes=[RouteMapPrefix(prefix="0.0.0.0/0", aggregate=True, fromPfxLen=0, toPfxLen=32)],
#         ),
#     ],
# )
# ndo.add_route_map_policy_under_template(
#     template_name="TN_NUTTAWUT_Tenant_Policies_SiteA", rnConfig=ROUTE_MAP_CONFIG, operation="merge"
# )


# Test adding tenant policies IGMP interface policy
# ndo.add_igmp_int_pol_under_template(
#     template_name="TN_NUTTAWUT_Tenant_Policies_SiteA",
#     igmpIntPolConfig=IGMPInterfacePolicyConfig(
#         name="IGMP_INT_POL_TEST",
#         igmpVersion="v2",
#         enableV3ASM=True,
#     )
# )


# Test adding tenant policies IGMP Snooping policy
# ndo.add_igmp_snoop_pol_under_template(
#     template_name="TN_NUTTAWUT_Tenant_Policies_SiteA",
#     igmpSnoopPol=IGMPSnoopingPolicyConfig(
#         name="IGMP_SNOOP_POL_TEST",
#         igmpVersion="v3",
#         enableFastLeave=True,
#     ),
#     operation="replace"
# )


# Test adding interface setting policy (Physical Interface)
ndo.create_intf_setting_policy(
    fabric_pol_name="NUTTAWUT_Fabric_policies",
    settings=PhysicalInterfaceSettingPolConfig(
        name="INT_POL_TEST", domain="NUTTAWUT_TEST_DOM", speed="10G", enableCDP=True, autoNegotiate="on-enforce"
    ),
)

# Test adding interface setting policy (Port Channel Interface)
ndo.create_intf_setting_policy(
    fabric_pol_name="NUTTAWUT_Fabric_policies",
    settings=PCInterfaceSettingPolConfig(
        name="INT_POL_TEST_PC", domain="NUTTAWUT_TEST_DOM", speed="10G", enableCDP=True, autoNegotiate="on-enforce", portChannelMode="off"
    ),
)
