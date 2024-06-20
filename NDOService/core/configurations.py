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


@dataclass
class L3OutNodeConfig:
    nodeID: str
    routerID: str
    podID: str = "1"
    useRouteIDAsLoopback: bool = False


@dataclass
class L3OutBGPControl:
    allowSelfAS: bool = False
    asOverride: bool = False
    disablePeerASCheck: bool = False
    nextHopSelf: bool = False
    sendCommunity: bool = False
    sendExtendedCommunity: bool = False
    sendDomainPath: bool = False


@dataclass
class L3OutBGPPeerControl:
    bfd: bool = True
    disableConnectedCheck: bool = False


@dataclass
class L3OutBGPPeerConfig:
    peerAddressV4: str
    peerAsn: int
    peerAddressV6: str = None
    adminState: str = "enabled"
    authEnabled: bool = False
    allowedSelfASCount: str = 3
    ebpgMultiHopTTL: str = 1
    localAsnConfig: str = "none"
    bgpControls: L3OutBGPControl = field(default_factory=L3OutBGPControl)
    peerControls: L3OutBGPPeerControl = field(default_factory=L3OutBGPPeerControl)


@dataclass
class L3OutInterfaceConfig:
    type: Literal["interfaces", "subInterfaces", "sviInterfaces"]
    portType: Literal["port", "pc"]
    encapVal: int
    bgpPeers: List[L3OutBGPPeerConfig]
    encapType: Literal["vlan", "vxlan"] = "vlan"
    primaryV4: str = None
    primaryV6: str = None
    portChannelName: str = None
    nodeID: str = None
    path: str = None
    podID: str = "1"


@dataclass
class L3OutConfig:
    """
    Parameter documentation:
    name : the name of L3OUT template
    vrf : the VRF name for this L3OUT
    nodes : List of L3OutNodeConfig object
    routingProtocol : either bgp or ospf
    exportRouteMap : name of route map in Tenant policy
    interfaces : List of L3OutInterfaceConfig object
    """

    name: str
    vrf: str
    l3domain: str
    nodes: List[L3OutNodeConfig]
    routingProtocol: Literal["bgp", "ospf"]
    exportRouteMap: str
    interfaces: List[L3OutInterfaceConfig]
