from NDOService.core.ndo_connector import NDOTemplate
from NDOService.core.configurations import *


params = {
    "connection": {"host": "127.0.0.1", "port": 10443, "username": "admin", "password": "P@ssw0rd"},
}

# INIT
ndo = NDOTemplate(
    params["connection"]["host"],
    params["connection"]["username"],
    params["connection"]["password"],
    params["connection"]["port"],
)


def Example_create_Tenant_Policies():
    # create tenant policy template
    ndo.create_tenant_policies_template("TN_NUTTAWUT_Tenant_Policies_SILA", ["SILA"], "TN_NUTTAWUT")
    # prepare prefixes config for RouteMap
    prefixes_1 = [RouteMapPrefix(prefix="10.100.0.0/24"), RouteMapPrefix(prefix="10.200.0.0/24")]
    prefixes_default = [RouteMapPrefix(prefix="0.0.0.0/0", aggregate=True, fromPfxLen=0, toPfxLen=32)]
    rnconfig = RouteMapConfig(
        name="RM_TN_NUTTAWUT_TEST",
        entryList=[
            RouteMapEntry(
                order=1,
                name="1",
                action="permit",
                prefixes=prefixes_1,
                attributes=RouteMapAttributes(
                    setAsPath=RouteMapSetAsPath(criteria="prepend", pathASNs=[450001]),
                ),
            ),
            RouteMapEntry(order=9, name="9", action="permit", prefixes=prefixes_default),
        ],
    )
    # Add route map to to tenant policy
    ndo.add_route_map_policy_under_template("TN_NUTTAWUT_Tenant_Policies_SILA", rnconfig)

    # BFD or OSPF interface settings
    bfdconfig = BFDPolicyConfig(minRxInterval=100, minTxInterval=100, echoRxInterval=100)
    ospfconfig = OSPFIntfConfig()

    # Add interface routing policy to tenant policy
    ndo.add_l3out_intf_routing_policy("TN_NUTTAWUT_Tenant_Policies_SILA", "IF_POLICY_BFD_100", bfdConfig=bfdconfig)
    ndo.add_l3out_intf_routing_policy(
        "TN_NUTTAWUT_Tenant_Policies_SILA", "IF_POLICY_OSPF_DEFAULT", ospfIntfConfig=ospfconfig
    )

    ndo.add_route_map_prefix_to_policy(
        "TN_NUTTAWUT_Tenant_Policies_SILA", "RM_SILA_TN_NUTTAWUT", 1, RouteMapPrefix(prefix="99.0.0.0/24")
    )
