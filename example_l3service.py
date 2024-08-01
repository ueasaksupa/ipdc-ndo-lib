from NDOService import l3_service
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

params = ServiceL3Parameters(
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
                    name="BD_L3_CUST_NET_1",
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
    l3_service.create(params)


if __name__ == "__main__":
    Example_Service_Create()
