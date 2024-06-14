import os
from pprint import pprint
from .core.configurations import *
from .core.ndo_connector import NDOTenantTemplate


def create(**kwargs):
    """
    For create L2 service
    """
    ndo = NDOTenantTemplate(
        kwargs["connection"]["host"],
        kwargs["connection"]["username"],
        kwargs["connection"]["password"],
        kwargs["connection"]["port"],
    )
    # prepare configuration opject
    bd_config = BridgeDomainParams() if "bd_config" not in kwargs else kwargs["bd_config"]
    vrf_config = VrfParams() if "vrf_config" not in kwargs else kwargs["vrf_config"]

    tenant = ndo.create_tenant(kwargs["tenant_name"], kwargs["sites"])
    # get schema by name if schema was not been created before, It will be created automatically
    schema = ndo.create_schema(kwargs["schema_name"])

    # ----- CREATE TEMPLATE ------
    # prepare empty VRF template
    ndo.create_template(schema, kwargs["vrf_template_name"], tenant["id"])
    # associate site to template
    ndo.add_site_to_template(schema, kwargs["vrf_template_name"], kwargs["sites"])
    # ----- CREATE TEMPLATE ------
    # prepare empty policies template
    ndo.create_template(schema, kwargs["bd_template_name"], tenant["id"])
    # associate site to template
    ndo.add_site_to_template(schema, kwargs["bd_template_name"], kwargs["sites"])

    # update schema
    schema = ndo.save_schema(schema)

    # ----- CREATE OBJECTS UNDER TEMPLATE ------
    # create filter under template
    ndo.create_filter_under_template(schema, kwargs["vrf_template_name"], kwargs["filter_name"])
    # create contract under template
    ndo.create_contract_under_template(
        schema, kwargs["vrf_template_name"], kwargs["contract_name"], kwargs["filter_name"]
    )
    # create VRF under template
    ndo.create_vrf_under_template(
        schema, kwargs["vrf_template_name"], kwargs["vrf_name"], kwargs["contract_name"], vrf_config
    )
    # create Bridge-Domain under template
    ndo.create_bridge_domain_under_template(
        schema,
        kwargs["vrf_template_name"],
        kwargs["bd_template_name"],
        kwargs["vrf_name"],
        kwargs["bd_name"],
        bd_config,
    )
    # create Application Profile under template
    anp = ndo.create_anp_under_template(schema, kwargs["bd_template_name"], kwargs["anp_name"])
    # create EPG under ANP
    ndo.create_epg_under_template(schema, anp, kwargs["bd_template_name"], kwargs["bd_name"], kwargs["epg_name"])
    # update schema
    schema = ndo.save_schema(schema)

    # ----- ADD PHYSICAL PORT PER SITE ------
    # add physical domain and device port to EPG per site
    for site in kwargs["sites"]:
        ndo.add_phy_domain_to_epg(
            schema,
            kwargs["bd_template_name"],
            kwargs["anp_name"],
            kwargs["epg_name"],
            site["epg_phy_domain"],
            site["name"],
        )
        ndo.add_static_port_to_epg(
            schema, kwargs["bd_template_name"], kwargs["anp_name"], kwargs["epg_name"], site["name"], site["endpoints"]
        )

    # update schema
    schema = ndo.save_schema(schema)
    print("=" * os.get_terminal_size().columns)
    pprint(schema)
    print("=" * os.get_terminal_size().columns)


if __name__ == "__main__":
    """
    This is the example how to call the method to create l2 service on NDO.
    Required params:
        connection:
            host: NDO host ip/hostname
            username: NDO username
            password: NDO password
            port: NDO port [default 443]
        sites: array of string of site name ex. ["site1", "site2"]
        tenant: Tenant name
        schema: Schema name
        vrf_template: Name of the template for VRF
        bd_template: Name of the template for BD
        vrf: VRF name
        bd: Bridge-domaon name
        anp: Application profile name
        epg: EPG name
    """

    params = {
        "connection": {"host": "127.0.0.1", "port": 10443, "username": "admin", "password": "P@ssw0rd"},
        "sites": [
            {
                "name": "TLS1",
                "endpoints": [
                    {"node": "3101", "port_type": "port", "port_name": "eth1/13", "port_mode": "regular", "vlan": 2103}
                ],
                "epg_phy_domain": "PHY_DOMAIN_SERVER_CL_DOM01_01",
            },
            {
                "name": "SILA",
                "endpoints": [
                    {"node": "3101", "port_type": "port", "port_name": "eth1/13", "port_mode": "regular", "vlan": 2103}
                ],
                "epg_phy_domain": "PHY_DOMAIN_SERVER_CL_DOM01_01",
            },
        ],
        "tenant_name": "TN_NUTTAWUT_TEST",
        "schema_name": "TN_NUTTAWUT_TEST_Schema01",
        "filter_name": "FLT_IP",
        "contract_name": "CON_VRF_CUSTOMER",
        "vrf_template_name": "VRF_Contract_Stretch_Template",
        "bd_template_name": "Policy_All_Site_template",
        "vrf_name": "VRF_CUSTOMER",
        "bd_name": "BD_CUSTOMER",
        "anp_name": "AP_CUSTOMER",
        "epg_name": "EPG_CUSTOMER",
    }
    create(**params)
