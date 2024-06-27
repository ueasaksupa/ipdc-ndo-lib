from NDOService import l2_service
from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *
from NDOService.core.service_parameters import *

""" TODO
This is the example how to call the method to create l2 service on NDO.
"""

params = L2ServiceParameters(
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
        SingleEPGTemplate(
            name="Policy_Stretch_AllSite_template",
            associatedSites=["SILA", "TLS1"],
            bd=TemplateBridgeDomain(
                name="BD_L2_CUST_NET_1",
                linkedVrfTemplate="VRF_Contract_Stretch_Template",
                linkedVrfName="VRF_CUSTOMER",
                anp_name="AP_CUSTOMER",
                epg=TemplateEPG(
                    name="EPG_L2_DB_1",
                    endpointPerSite=[
                        SiteEndpoints(
                            name="TLS1",
                            epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
                            endpoints=[
                                Endpoint(
                                    nodeId="3101", port_type="port", port_name="1/12", port_mode="regular", vlan=2103
                                ),
                                Endpoint(
                                    nodeId="3101", port_type="port", port_name="1/13", port_mode="regular", vlan=2103
                                ),
                            ],
                        ),
                        SiteEndpoints(
                            name="SILA",
                            epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
                            endpoints=[
                                Endpoint(
                                    nodeId="3101", port_type="port", port_name="1/13", port_mode="regular", vlan=2103
                                )
                            ],
                        ),
                    ],
                ),
                bdConfig=BridgeDomainConfig(unicastRouting=False, l2UnknownUnicast="flood"),
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
    l2_service.create(params)


if __name__ == "__main__":
    Example_Service_Create()
