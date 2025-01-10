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


def Example_Fabric_Template():
    # EXAMPLE HOW TO CREATE FABRIC POLICIES/RESOURCES

    # example - To create fabric_policy
    ndo.create_fabric_policy("TLS1_nuttawut_test_by_script", "TLS1")

    # example - To create fabric_resource
    ndo.create_fabric_resource("TLS1_nuttawut_test_by_script", "TLS1")

    # example - To add vlan to pool
    ndo.add_vlans_to_pool("TLS1_nuttawut_test_by_script", "VLAN_SERVER_CL_TEST", [3013, 3014, (3015, 3100)])

    # example - To add domain to fabric policy
    ndo.add_domain_to_fabric_policy("TLS1_nuttawut_test_by_script", "domains", "TLS1_CL_DOM01", "VLAN_SERVER_CL_TEST")

    # example VPC resource config
    vpc_port_config = VPCResource(
        name="VPC_SILA_TEST",
        node1Details=VPCNodeDetails("3101", "1/14"),
        node2Details=VPCNodeDetails("3102", "1/14"),
    )
    # example PC resource config
    pc_port_config = PortChannelResource(
        name="PC_SILA_TEST",
        node="3102",
        memberInterfaces="1/15,1/16",
    )
    # example Physical resource config
    phy_port_config = PhysicalIntfResource(
        name="PHY_TEST",
        nodes=["3102"],
        interfaces="1/17",
    )
    # Add port resource to fabric resource policy
    ndo.add_port_to_fabric_resource(
        "SILA_CL_DOM01_ResourcePolicy01", phy_port_config, "INT_SILA1_CL_DOM01_PHY_SERVER_1G"
    )
    ndo.add_port_to_fabric_resource(
        "SILA_CL_DOM01_ResourcePolicy01", pc_port_config, "INT_SILA1_CL_DOM01_VPC_SERVER_1G"
    )
    ndo.add_port_to_fabric_resource(
        "SILA_CL_DOM01_ResourcePolicy01", vpc_port_config, "INT_SILA1_CL_DOM01_VPC_SERVER_1G"
    )
