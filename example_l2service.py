from NDOService import l2_service
from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *
from NDOService.core.service_parameters import *

"""
This is the example how to call the method to create l2 service on NDO.
Required params:
    connection:
        host: NDO host ip/hostname
        username: NDO username
        password: NDO password
        port: NDO port [default 443]
    sites: array of dictionary of site.
        name: site name
        endpoints: Array of endpoint in the selected site
            node: node name
            port_type: either port, vpc or dpc
            port_name: port name ex. 1/13
            port_mode: port mode select one of the [regular, native, untagged]
            vlan: vlan number
        epg_phy_domain: Physical domain for EPG
    tenant_name: Tenant name
    schema_name: Schema name
    vrf_template_name: Name of the template for VRF
    bd_template_name: Name of the template for BD
    vrf_name: VRF name
    bd_name: Bridge-domaon name
    anp_name: Application profile name
    epg_name: EPG name
"""

params = L2ServiceParameters(
    connection=NDOConnection(host="127.0.0.1", port=10443, username="admin", password="P@ssw0rd"),
    sites=[
        SiteParameters(
            name="TLS1",
            epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
            endpoints=[Endpoint(nodeId="3101", port_type="port", port_name="eth1/13", port_mode="regular", vlan=2103)],
        ),
        SiteParameters(
            name="SILA",
            epg_phy_domain="PHY_DOMAIN_SERVER_CL_DOM01_01",
            endpoints=[Endpoint(nodeId="3101", port_type="port", port_name="eth1/13", port_mode="regular", vlan=2103)],
        ),
    ],
    tenant_name="TN_NUTTAWUT",
    schema_name="TN_NUTTAWUT_Schema01",
    filter_name="FLT_IP",
    contract_name="CON_VRF_CUSTOMER",
    vrf_template_name="VRF_Contract_Stretch_Template",
    bd_template_name="Policy_AllSite_template",
    vrf_name="VRF_CUSTOMER",
    bd_name="BD_CUSTOMER",
    anp_name="AP_CUSTOMER",
    epg_name="EPG_CUSTOMER",
)

# INIT ndo object
ndo = NDOTemplate(
    params.connection.host,
    params.connection.username,
    params.connection.password,
    params.connection.port,
)


def Example_Service_Create():
    # BridgeDomainConfig is for customize BD parameters
    # in this example, show how to add ip gateway for l2 each subnet
    bd_config = BridgeDomainConfig(
        subnets=[
            BridgeDomainSubnet(ip="10.0.0.1/24", description="test from api"),
        ]
    )
    params.bdConfig = bd_config
    # EXAMPLE HOW TO CREATE SERVICE
    #
    l2_service.create(params)


if __name__ == "__main__":
    Example_Service_Create()
