from dataclasses import dataclass, field
from typing import List, Literal


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


@dataclass
class L3OutConfig:
    name: str


@dataclass
class RouteMapPrefix:
    prefix: str
    fromPfxLen: int = 0
    toPfxLen: int = 0
    aggregate: bool = False


@dataclass
class RouteMapEntry:
    order: int
    name: str
    action: Literal["permit", "deny"]
    prefixes: list[RouteMapPrefix]


@dataclass
class RouteMapConfig:
    name: str
    entryList: list[RouteMapEntry]
    description: str = ""


@dataclass
class BFDPolicyConfig:
    adminState: Literal["enabled", "disabled"] = "enabled"
    detectionMultiplier: int = 3
    minRxInterval: int = 50
    minTxInterval: int = 50
    echoAdminState: Literal["enabled", "disabled"] = "enabled"
    echoRxInterval: int = 50
    ifControl: bool = False


@dataclass
class OSPFIntfConfig:
    networkType: Literal["broadcast", "pointToPoint"] = "broadcast"
    prio: int = 1
    cost: int = 0
    advertiseSubnet: bool = False
    bfd: bool = False
    ignoreMtu: bool = False
    passiveParticipation: bool = False
    helloInterval: int = 10
    deadInterval: int = 40
    retransmitInterval: int = 5
    transmitDelay: int = 1
