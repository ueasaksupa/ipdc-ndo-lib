"""
This is just alias typing for remembering return object of the method
for more detail about each JSON object please refer to json schema in NDOObjectSchema directory
"""

# NDOObjectSchema/site.json
type Site = dict

# NDOObjectSchema/tenant.json
type Tenant = dict

# NDOObjectSchema/schema.json
type Schema = dict

type Template = dict  # schema.templates
type Filter = dict  # schema.templates.filters
type Contract = dict  # schema.template.contracts
type ExtEPG = dict  # schema.template.externalEpgs
type EPG = dict  # schema.template.anps.epgs
type Vrf = dict  # schema.template.vrfs
type BD = dict  # schema.template.bds
type ANP = dict  # schema.template.anps

# NDOObjectSchema/template.json
type FabricPolicy = dict  # template.fabricPolicyTemplate
type FabricResourcePolicy = dict  # template.fabricResourceTemplate
type TenantPolTemplate = dict  # template.tenantPolicyTemplate
type L3OutTemplate = dict  # template.l3outTemplate

# NDOObjectSchema/interfaceSetting.json
type IntSettingPolicy = dict

# NDOObjectSchema/vpcsummary.json
type VPCResourcePolicy = dict

# NDOObjectSchema/pcsummary.json
type PCResourcePolicy = dict
