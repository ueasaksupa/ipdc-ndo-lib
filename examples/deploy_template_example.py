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


def Example_Deploy_Schema_Template():
    ndo.deploy_schema_template("TN_NUTTAWUT_Schema01", "VRF_Contract_Stretch_Template")
    ndo.deploy_schema_template("TN_NUTTAWUT_Schema01", "Policy_Stretch_AllSite_template")


def Example_Deploy_Template():
    ndo.deploy_policies_template("TN_NUTTAWUT_Tenant_Policies_TLS1")


def Example_Undeploy_site():
    ndo.undeploy_template_from_sites("TN_NUTTAWUT_Schema01", "Policy_Stretch_AllSite_template", ["SILA", "TLS1"])
    ndo.undeploy_template_from_sites("TN_NUTTAWUT_Schema01", "VRF_Contract_Stretch_Template", ["SILA", "TLS1"])
