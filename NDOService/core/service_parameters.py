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
class SiteEndpoints:
    name: str
    epg_phy_domain: str
    endpoints: List[Endpoint]


@dataclass(kw_only=True)
class TemplateExternalEPG:
    name: str
    linkedVrfTemplate: str
    linkedVrfName: str
    associatedL3Out: List[EEPGL3OutInfo]


@dataclass(kw_only=True)
class TemplateEPG:
    name: str
    endpointPerSite: List[SiteEndpoints]


@dataclass(kw_only=True)
class TemplateBridgeDomain:
    name: str
    linkedVrfTemplate: str
    linkedVrfName: str
    anp_name: str
    epg: TemplateEPG
    bdConfig: Optional[BridgeDomainConfig] = None


@dataclass(kw_only=True)
class SingleEPGTemplate:
    name: str
    associatedSites: List[str]
    bd: TemplateBridgeDomain
    externalEPG: Optional[TemplateExternalEPG] = None


@dataclass(kw_only=True)
class MultiEPGTemplate:
    name: str
    associatedSites: List[str]
    bds: List[TemplateBridgeDomain]
    externalEPG: Optional[TemplateExternalEPG] = None


@dataclass(kw_only=True)
class VRFTemplate:
    name: str
    associatedSites: List[str]
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
    routemapConfig: RouteMapConfig
    bfdConfig: BFDPolicyConfig | None = None


@dataclass(kw_only=True)
class L2ServiceParameters:
    connection: NDOConnection
    tenant_name: str
    tenant_sites: List[str] | None = None
    schema_name: str
    templates: List[VRFTemplate | SingleEPGTemplate]


@dataclass(kw_only=True)
class L3ServiceParameters:
    connection: NDOConnection
    tenant_name: str
    tenant_sites: List[str] | None = None
    schema_name: str
    templates: List[VRFTemplate | MultiEPGTemplate]


@dataclass(kw_only=True)
class L3OutServiceParameters:
    connection: NDOConnection
    tenant_name: str
    tenant_sites: List[str] | None = None
    schema_name: str
    templates: List[VRFTemplate | MultiEPGTemplate]
    l3outTemplatePerSite: List[L3OutTemplatePerSite]
    tenantPolTemplate: TenantPolicyTenplate
