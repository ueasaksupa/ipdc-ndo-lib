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


def Example_deletion():
    schema = ndo.find_schema_by_name("TN_NUTTAWUT_Schema01")
    if schema is None:
        return
    ndo.delete_vrf_under_template(schema, "VRF_Contract_Stretch_Template", "VRF_CUSTOMER")
    ndo.delete_egp_under_template(schema, "Policy_Stretch_AllSite_template", "AP_CUSTOMER", "EPG_L2_DB_1")
    ndo.delete_bridge_domain_under_template(schema, "Policy_Stretch_AllSite_template", "BD_L2_CUST_NET_1")
    ndo.save_schema(schema)
