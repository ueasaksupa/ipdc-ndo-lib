from dataclasses import dataclass, field
from typing import List, Literal, Optional
from .configurations import *


@dataclass(kw_only=True)
class NDOConnection:
    host: str
    port: int
    username: str
    password: str


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
    linkedVrfTemplate: str = "VRF_Contract_Stretch_Template"
    linkedVrfName: str
    associatedL3Out: List[EEPGL3OutInfo]


@dataclass(kw_only=True)
class TemplateEPG:
    name: str
    staticPortPerSite: List[SiteStaticPorts]


@dataclass(kw_only=True)
class TemplateBridgeDomain:
    name: str
    linkedVrfTemplate: str = "VRF_Contract_Stretch_Template"
    linkedVrfName: str
    anp_name: str
    epg: TemplateEPG
    bdConfig: Optional[BridgeDomainConfig] = None


@dataclass(kw_only=True)
class EPGsTemplate:
    name: str = "Policy_Stretch_AllSite_template"
    associatedSites: List[str] | None = None
    bds: List[TemplateBridgeDomain]
    externalEPG: Optional[TemplateExternalEPG] = None


@dataclass(kw_only=True)
class VRFTemplate:
    name: str = "VRF_Contract_Stretch_Template"
    associatedSites: List[str] | None = None
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
class TenantPolicyTenplate:
    name: str
    site: str
    routemapConfig: RouteMapConfig
    bfdConfig: BFDPolicyConfig | None = None


@dataclass(kw_only=True)
class ServiceL2Parameters:
    connection: NDOConnection
    tenant_name: str
    tenant_sites: List[str] | None = None
    schema_name: str
    templates: List[VRFTemplate | EPGsTemplate]


@dataclass(kw_only=True)
class ServiceL3Parameters:
    connection: NDOConnection
    tenant_name: str
    tenant_sites: List[str] | None = None
    schema_name: str
    templates: List[VRFTemplate | EPGsTemplate]


@dataclass(kw_only=True)
class ServiceL3OutParameters:
    connection: NDOConnection
    tenant_name: str
    tenant_sites: List[str] | None = None
    schema_name: str
    templates: List[VRFTemplate | EPGsTemplate]
    l3outTemplatePerSite: List[L3OutTemplatePerSite]
    tenantPolTemplates: List[TenantPolicyTenplate]
