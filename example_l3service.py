from NDOService import l3_service
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
            Endpoint(nodeId="3101", port_type="port", port_name="1/14", port_mode="regular", vlan=2104),
            Endpoint(nodeId="3101", port_type="port", port_name="1/15", port_mode="regular", vlan=2104),
        ],
    ),
    SiteEndpoints(
        name="SILA",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        endpoints=[Endpoint(nodeId="3101", port_type="port", port_name="1/14", port_mode="regular", vlan=2104)],
    ),
]

ENDPOINTS_EPG_2 = [
    SiteEndpoints(
        name="TLS1",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        endpoints=[
            Endpoint(nodeId="3101", port_type="port", port_name="1/16", port_mode="regular", vlan=2104),
            Endpoint(nodeId="3101", port_type="port", port_name="1/17", port_mode="regular", vlan=2104),
        ],
    ),
    SiteEndpoints(
        name="SILA",
        epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
        endpoints=[Endpoint(nodeId="3101", port_type="port", port_name="1/15", port_mode="regular", vlan=2104)],
    ),
]

params = L3ServiceParameters(
    connection=NDOConnection(host="127.0.0.1", port=10443, username="admin", password="P@ssw0rd"),
    tenant_name="TN_NUTTAWUT",
    tenant_sites=["SILA", "TLS1"],
    schema_name="TN_NUTTAWUT_Schema01",
    templates=[
        VRFTemplate(
            name="VRF_Contract_Stretch_Template",
            associatedSites=["SILA", "TLS1"],
            filter_name="FLT_IP",
            contract_name="CON_VRF_CUSTOMER",
            vrf_name="VRF_CUSTOMER",
        ),
        MultiEPGTemplate(
            name="Policy_Stretch_AllSite_template",
            associatedSites=["SILA", "TLS1"],
            bds=[
                TemplateBridgeDomain(
                    name="BD_L3_CUST_NET_1",
                    linkedVrfTemplate="VRF_Contract_Stretch_Template",
                    linkedVrfName="VRF_CUSTOMER",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(name="EPG_L3_SERVER_1", endpointPerSite=ENDPOINTS_EPG_1),
                    bdConfig=BridgeDomainConfig(
                        subnets=[
                            BridgeDomainSubnet(ip="10.100.0.1/24", description="test from api"),
                        ]
                    ),
                ),
                TemplateBridgeDomain(
                    name="BD_L3_CUST_NET_2",
                    linkedVrfTemplate="VRF_Contract_Stretch_Template",
                    linkedVrfName="VRF_CUSTOMER",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(name="EPG_L3_SERVER_2", endpointPerSite=ENDPOINTS_EPG_2),
                    bdConfig=BridgeDomainConfig(
                        subnets=[
                            BridgeDomainSubnet(ip="10.200.0.1/24", description="test from api"),
                        ]
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
