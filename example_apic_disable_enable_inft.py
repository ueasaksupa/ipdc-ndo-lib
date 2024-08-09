from NDOService.core.apic_connector import APICTemplate
from NDOService.core.configurations import *

apic_instance = APICTemplate(host="127.0.0.1", username="admin", password="Aci@is2024!!", port=10444)

# Disable port 1/12 on leaf 3101
apic_instance.disable_port("1/12", "3101")

# Enable port 1/12 on leaf 3101
apic_instance.enable_port("1/12", "3101")
