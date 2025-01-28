from dataclasses import dataclass, field
from typing import List, Literal, Optional
from .configurations import *


@dataclass(kw_only=True)
class SiteStaticPorts:
    """
    ### Parameter Notes:
    - sitename : site name
    - epg_phy_domain : Name of physical domain that defined in the fabric policy
    - staticPorts : List of StaticPortPhy | StaticPortPC | StaticPortVPC
    """

    sitename: str
    epg_phy_domain: str
    staticPorts: List[StaticPortPhy | StaticPortPC | StaticPortVPC]


@dataclass(kw_only=True)
class TemplateExternalEPG:
    name: str
    linkedVrfSchema: str | None = None
    linkedVrfTemplate: str
    linkedVrfName: str
    associatedL3Out: List[ExternalEpgToL3OutBinding]
    subnets: List[ExternalEpgSubnet] = field(default_factory=list)


@dataclass(kw_only=True)
class TemplateEPG:
    name: str
    staticPortPerSite: List[SiteStaticPorts]
    epg_description: str = ""
    mCastSource: bool = False
    proxyArp: bool = False


@dataclass(kw_only=True)
class TemplateBridgeDomain:
    name: str
    linkedVrfSchema: str | None = None
    linkedVrfTemplate: str
    linkedVrfName: str
    anp_name: str
    epg: TemplateEPG
    bdConfig: BridgeDomainConfig


@dataclass(kw_only=True)
class EPGsTemplate:
    name: str
    associatedSites: List[str] | Literal["_all_"]
    bds: List[TemplateBridgeDomain]
    externalEPG: Optional[TemplateExternalEPG] = None


@dataclass(kw_only=True)
class VRFTemplate:
    name: str
    associatedSites: List[str] | Literal["_all_"]
    filter_name: str
    contract_name: str
    vrf_name: str
    vrfConfig: Optional[VrfConfig] = None


@dataclass(kw_only=True)
class L3OutTemplatePerSite:
    name: str
    site: str
    l3outConfig: L3OutConfig


@dataclass(kw_only=True)
class TenantPolicyTemplate:
    name: str
    site: str
    routemapConfig: RouteMapConfig
    bfdConfig: BFDPolicyConfig | None = None


@dataclass(kw_only=True)
class ServiceSimpleParameters:
    tenant_name: str
    tenant_sites: List[str] | None = None
    schema_name: str
    templates: List[VRFTemplate | EPGsTemplate]


@dataclass(kw_only=True)
class ServiceL3OutParameters:
    tenant_name: str
    tenant_sites: List[str] | None = None
    schema_name: str
    templates: List[VRFTemplate | EPGsTemplate]
    l3outTemplatePerSite: List[L3OutTemplatePerSite]
    tenantPolTemplates: List[TenantPolicyTemplate]
