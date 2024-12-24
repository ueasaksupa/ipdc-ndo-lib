from NDOService.services.simple_service import create_service
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
            StaticPortPhy(nodeId="3101", port_name="1/12", port_mode="regular", vlan=2104),
            StaticPortPhy(nodeId="3101", port_name="1/13", port_mode="regular", vlan=2104),
        ],
    ),
    SiteStaticPorts(
        sitename="SILA",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        staticPorts=[StaticPortPhy(nodeId="3101", port_name="1/13", port_mode="regular", vlan=2104)],
    ),
]

ENDPOINTS_EPG_2 = [
    SiteStaticPorts(
        sitename="TLS1",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        staticPorts=[
            StaticPortPhy(nodeId="3101", port_name="1/14", port_mode="regular", vlan=2104),
            StaticPortPhy(nodeId="3101", port_name="1/15", port_mode="regular", vlan=2104),
        ],
    ),
    SiteStaticPorts(
        sitename="SILA",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        staticPorts=[StaticPortPhy(nodeId="3101", port_name="1/14", port_mode="regular", vlan=2104)],
    ),
]

params = ServiceSimpleParameters(
    tenant_name="TN_NUTTAWUT",
    schema_name="TN_NUTTAWUT_Schema01",
    templates=[
        VRFTemplate(
            name="VRF_CONTRACT_STRETCH_TEMPLATE",
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
                    name="BD_L3_CUST_NET_1",
                    linkedVrfTemplate="VRF_CONTRACT_STRETCH_TEMPLATE",
                    linkedVrfName="VRF_CUSTOMER",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(name="EPG_L3_SERVER_1", staticPortPerSite=ENDPOINTS_EPG_1),
                    bdConfig=BridgeDomainConfig(
                        arpFlood=False,
                        subnets=[BridgeDomainSubnet(ip="10.100.0.1/24", description="test from api", scope="public")],
                    ),
                ),
                TemplateBridgeDomain(
                    name="BD_L3_CUST_NET_2",
                    linkedVrfTemplate="VRF_CONTRACT_STRETCH_TEMPLATE",
                    linkedVrfName="VRF_CUSTOMER",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(name="EPG_L3_SERVER_2", staticPortPerSite=ENDPOINTS_EPG_2),
                    bdConfig=BridgeDomainConfig(
                        arpFlood=False,
                        subnets=[BridgeDomainSubnet(ip="10.200.0.1/24", description="test from api", scope="public")],
                    ),
                ),
            ],
        ),
    ],
)


# EXAMPLE OF NON STRETCH BD SERVICE PARAMETER
params_for_non_strech_bd = ServiceSimpleParameters(
    tenant_name="TN_NUTTAWUT",
    schema_name="TN_NUTTAWUT_Schema01",
    templates=[
        # This is the VRF template, default is VZAny type
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
                    name="NON_STRETCH_BD",
                    linkedVrfTemplate="VRF_CONTRACT_STRETCHED_TEMPLATE",
                    linkedVrfName="VRF_CUSTOMER",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(
                        name="EPG_L2_DB_1",
                        staticPortPerSite=ENDPOINTS_EPG_1,
                    ),
                    bdConfig=BridgeDomainConfig(
                        l2Stretch=False,  # This is the key to make it non-stretch
                        # PerSiteSubnet is optional, if you want to assign subnet to each site
                        perSiteSubnet=[
                            ("TLS1", BridgeDomainSubnet(ip="10.1.1.1/24")),  # This is the subnet for TLS1
                            ("SILA", BridgeDomainSubnet(ip="10.2.2.2/24")),  # This is the subnet for SILA
                        ],
                    ),
                ),
            ],
        ),
    ],
)


if __name__ == "__main__":
    ndo = NDOTemplate(host="127.0.0.1", port=10443, username="admin", password="P@ssw0rd")
    create_service(ndo, params)
