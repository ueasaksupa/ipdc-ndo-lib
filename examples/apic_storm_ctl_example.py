from NDOService.core.apic_connector import APICTemplate
from NDOService.core.configurations import *

ST_POL_NAME = "STORM_CONTROL_POLICY_01"

apic_instance = APICTemplate(host="127.0.0.1", username="admin", password="Aci@is2024!!", port=10444)

try:
    apic_instance.create_stormcontrol_policy(ST_POL_NAME)
except Exception as e:
    # already exists exception
    print(e)

apic_instance.apply_stormcontrol_to_interface_policy(ST_POL_NAME, "INT_SILA1_CL_DOM01_PHY_SERVER_1G")
apic_instance.apply_stormcontrol_to_bundle_policy(ST_POL_NAME, "VPC_SILA_TEST")
