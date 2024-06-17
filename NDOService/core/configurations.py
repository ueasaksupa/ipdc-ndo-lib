from dataclasses import dataclass, field
from typing import List


@dataclass
class BridgeDomainSubnet:
    ip: str = ""
    description: str = ""
    scope: str = "private"  # private, public
    shared: bool = False
    querier: bool = False
    noDefaultGateway: bool = False
    virtual: bool = False
    primary: bool = False
    ipDPLearning: str = "enabled"  # enabled, disabled


@dataclass
class BridgeDomainParams:
    description: str = ""
    l2UnknownUnicast: str = "proxy"  # flood, proxy
    intersiteBumTrafficAllow: bool = True
    optimizeWanBandwidth: bool = True
    l2Stretch: bool = True
    l3MCast: bool = False
    unkMcastAct: str = "flood"  # flood, opt-flood
    v6unkMcastAct: str = "flood"  # flood, opt-flood
    arpFlood: bool = True
    multiDstPktAct: str = "bd-flood"  # bd-flood, encap-flood, drop
    unicastRouting: bool = True
    subnets: List[BridgeDomainSubnet] = field(default_factory=list)


@dataclass
class VrfParams:
    description: str = ""
    l3MCast: bool = False
    preferredGroup: bool = False
    vzAnyEnabled: bool = True
    ipDataPlaneLearning: str = "enabled"  # enabled, disabled


@dataclass
class IntfDescription:
    nodeID: str
    interfaceID: str
    description: str


@dataclass
class VPCNodeDetails:
    node: str
    memberInterfaces: str


@dataclass
class PhysicalIntfResource:
    name: str
    interfaces: str
    policy: str = ""
    nodes: list[str] = field(default_factory=list)
    interfaceDescriptions: List[IntfDescription] = field(default_factory=list)
    description: str = ""


@dataclass
class PortChannelResource:
    name: str
    node: str
    memberInterfaces: str
    policy: str = ""
    interfaceDescriptions: List[IntfDescription] = field(default_factory=list)
    description: str = ""


@dataclass
class VPCResource:
    name: str
    node1Details: VPCNodeDetails
    node2Details: VPCNodeDetails
    policy: str = ""
    interfaceDescriptions: list[IntfDescription] = field(default_factory=list)
    description: str = ""
