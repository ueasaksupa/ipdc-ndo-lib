"""
This is just alias typing for remembering return object of the method
for more detail about each JSON object please refer to json schema in NDOObjectSchema directory
"""

# NDOObjectSchema/site.json
Site = dict

# NDOObjectSchema/tenant.json
Tenant = dict

# NDOObjectSchema/schema.json
Schema = dict

Template = dict  # schema.templates
Filter = dict  # schema.templates.filters
Contract = dict  # schema.template.contracts
ExtEPG = dict  # schema.template.externalEpgs
EPG = dict  # schema.template.anps.epgs
Vrf = dict  # schema.template.vrfs
BD = dict  # schema.template.bds
ANP = dict  # schema.template.anps

# NDOObjectSchema/template.json
FabricPolicy = dict  # template.fabricPolicyTemplate
FabricResourcePolicy = dict  # template.fabricResourceTemplate
TenantPolTemplate = dict  # template.tenantPolicyTemplate
L3OutTemplate = dict  # template.l3outTemplate

# NDOObjectSchema/interfaceSetting.json
IntSettingPolicy = dict

# NDOObjectSchema/vpcsummary.json
VPCResourcePolicy = dict

# NDOObjectSchema/pcsummary.json
PCResourcePolicy = dict
