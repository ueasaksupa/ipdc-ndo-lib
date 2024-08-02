from NDOService import l2_service
from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *
from NDOService.core.service_parameters import *

"""
This is the example how to call the method to create l2 service on NDO.
"""

ENDPOINTS = [
    SiteStaticPorts(
        sitename="TLS1",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        staticPorts=[
            StaticPortPhy(nodeId="3101", port_name="1/12", port_mode="regular", vlan=2102),
            StaticPortPhy(nodeId="3101", port_name="1/12", port_mode="regular", vlan=2103),
        ],
    ),
    SiteStaticPorts(
        sitename="SILA",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        staticPorts=[
            StaticPortPhy(nodeId="3101", port_name="1/12", port_mode="regular", vlan=2102),
            StaticPortPC(port_name="PC_SILA_CL_01", port_mode="regular", vlan=2103),
        ],
    ),
]


params = ServiceL2Parameters(
    connection=NDOConnection(host="127.0.0.1", port=10443, username="admin", password="P@ssw0rd"),
    tenant_name="TN_NUTTAWUT",
    schema_name="TN_NUTTAWUT_Schema01",
    templates=[
        VRFTemplate(
            filter_name="FLT_IP",
            contract_name="CON_VRF_CUSTOMER",
            vrf_name="VRF_CUSTOMER",
        ),
        EPGsTemplate(
            bds=[
                TemplateBridgeDomain(
                    name="BD_L2_CUST_NET_1",
                    linkedVrfName="VRF_CUSTOMER",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(
                        name="EPG_L2_DB_1",
                        staticPortPerSite=ENDPOINTS,
                    ),
                ),
            ]
        ),
    ],
)

# EXAMPLE HOW TO NON STRETCH BD SERVICE
params_for_non_strech_bd = ServiceL2Parameters(
    connection=NDOConnection(host="127.0.0.1", port=10443, username="admin", password="P@ssw0rd"),
    tenant_name="TN_NUTTAWUT",
    schema_name="TN_NUTTAWUT_Schema01",
    templates=[
        VRFTemplate(
            filter_name="FLT_IP",
            contract_name="CON_VRF_CUSTOMER",
            vrf_name="VRF_CUSTOMER",
        ),
        EPGsTemplate(
            bds=[
                TemplateBridgeDomain(
                    name="NON_STRETCH_BD",
                    linkedVrfName="VRF_CUSTOMER",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(
                        name="EPG_L2_DB_1",
                        staticPortPerSite=ENDPOINTS,
                    ),
                    bdConfig=BridgeDomainConfig(
                        l2Stretch=False,
                        perSiteSubnet=[
                            ("TLS1", BridgeDomainSubnet(ip="10.1.1.1/24")),
                            ("SILA", BridgeDomainSubnet(ip="10.2.2.2/24")),
                        ],
                    ),
                ),
            ]
        ),
    ],
)


def Example_Service_Create():
    # EXAMPLE HOW TO CREATE SERVICE
    #
    l2_service.create(params)


if __name__ == "__main__":
    Example_Service_Create()
