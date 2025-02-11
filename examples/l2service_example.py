from NDOService.services.simple_service import create_service
from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *
from NDOService.core.service_parameters import *

"""
This is the example how to call the method to create l2 service on NDO.
"""

ENDPOINTS = [
    SiteStaticPorts(
        sitename="SiteA",
        epg_phy_domain="PHY_DOM_01",
        staticPorts=[
            StaticPortPhy(nodeId="3101", port_name="1/10", port_mode="regular", vlan=2000),
            StaticPortPhy(nodeId="3101", port_name="1/11", port_mode="regular", vlan=2000),
            # StaticPortPC(port_name="PC_NAME", port_mode="regular", vlan=2200),  # example of port-channel, you have to make sure that the PC is already created in the fabric
            # StaticPortVPC(port_name="VPC_NAME", port_mode="regular", vlan=2300), # example of vPC, you have to make sure that the VPC is already created in the fabric
        ],
    ),
]


params = ServiceSimpleParameters(
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
                    name="BD_L2_CUST_NET_1",
                    # linkedVrfSchema="....", # if you want to link to another schema
                    linkedVrfTemplate="VRF_CONTRACT_STRETCHED_TEMPLATE",
                    linkedVrfName="VRF_CUSTOMER",
                    anp_name="AP_CUSTOMER",
                    epg=TemplateEPG(
                        name="EPG_L2_DB_1",
                        staticPortPerSite=ENDPOINTS,
                    ),
                    bdConfig=BridgeDomainConfig(unicastRouting=False),
                ),
            ],
        ),
    ],
)


if __name__ == "__main__":
    ndo = NDOTemplate(host="172.31.1.24", port=443, username="admin", password="P@ssw0rd", delay=1.5)
    create_service(ndo, params, replace=False)
