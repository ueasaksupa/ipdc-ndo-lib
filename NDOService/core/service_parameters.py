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
class L3BridgeDomainParams:
    bdConfig: BridgeDomainConfig
    bd_name: str
    anp_name: str
    epg_name: str


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
    extEpg_name: Optional[str] = None


@dataclass(kw_only=True)
class MultiEPGTemplate:
    name: str
    associatedSites: List[str]
    bds: List[TemplateBridgeDomain]
    extEpg_name: Optional[str] = None


@dataclass(kw_only=True)
class VRFTemplate:
    name: str
    associatedSites: List[str]
    filter_name: str
    contract_name: str
    vrf_name: str
    vrfConfig: Optional[VrfConfig] = None


@dataclass(kw_only=True)
class L2ServiceParameters:
    connection: NDOConnection
    tenant_name: str
    tenant_sites: List[str]
    schema_name: str
    templates: List[VRFTemplate | SingleEPGTemplate]


@dataclass(kw_only=True)
class L3ServiceParameters:
    connection: NDOConnection
    tenant_name: str
    tenant_sites: List[str]
    schema_name: str
    templates: List[VRFTemplate | MultiEPGTemplate]
