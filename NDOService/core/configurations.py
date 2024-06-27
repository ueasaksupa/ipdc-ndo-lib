from dataclasses import dataclass, field
from typing import List, Literal


@dataclass(kw_only=True)
class Endpoint:
    """
    Example Endpoint parameter
    nodeId: 1101
    port_type: "port"
    port_name: 1/20
    port_mode: "regular"
    vlan: 2000
    """

    nodeId: str
    port_type: Literal["port", "vpc", "dpc"]
    port_name: str
    port_mode: Literal["regular", "native", "untagged"]
    vlan: int


@dataclass(kw_only=True)
class BridgeDomainSubnet:
    ip: str = ""
    description: str = ""
    scope: Literal["private", "public"] = "private"
    shared: bool = False
    querier: bool = False
    noDefaultGateway: bool = False
    virtual: bool = False
    primary: bool = False
    ipDPLearning: Literal["enabled", "disabled"] = "enabled"


@dataclass(kw_only=True)
class BridgeDomainConfig:
    description: str = ""
    l2UnknownUnicast: Literal["proxy", "flood"] = "proxy"
    intersiteBumTrafficAllow: bool = True
    optimizeWanBandwidth: bool = True
    l2Stretch: bool = True
    l3MCast: bool = False
    unkMcastAct: Literal["opt-flood", "flood"] = "flood"
    v6unkMcastAct: Literal["opt-flood", "flood"] = "flood"
    arpFlood: bool = True
    multiDstPktAct: Literal["bd-flood", "encap-flood", "drop"] = "bd-flood"
    unicastRouting: bool = True
    subnets: List[BridgeDomainSubnet] = field(default_factory=list)


@dataclass
class VrfConfig:
    description: str = ""
    l3MCast: bool = False
    preferredGroup: bool = False
    vzAnyEnabled: bool = True
    ipDataPlaneLearning: Literal["enabled", "disabled"] = "enabled"


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
    nodes: List[str] = field(default_factory=list)
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
    interfaceDescriptions: List[IntfDescription] = field(default_factory=list)
    description: str = ""


@dataclass(kw_only=True)
class RouteMapSetAsPath:
    criteria: Literal["prepend", "prepend-last-as"]
    pathASNs: List[int]
    asnCount: int | None = None


@dataclass(kw_only=True)
class RouteMapAttributes:
    setAsPath: RouteMapSetAsPath | None = None
    setPreference: int | None = None
    setNextHopPropagate: bool | None = None
    setMultiPath: bool | None = None
    setWeight: int | None = None


@dataclass(kw_only=True)
class RouteMapPrefix:
    prefix: str
    fromPfxLen: int = 0
    toPfxLen: int = 0
    aggregate: bool = False


@dataclass(kw_only=True)
class RouteMapEntry:
    order: int
    name: str
    action: Literal["permit", "deny"]
    prefixes: List[RouteMapPrefix]
    attributes: RouteMapAttributes | None = None


@dataclass(kw_only=True)
class RouteMapConfig:
    name: str
    entryList: List[RouteMapEntry]
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


@dataclass(kw_only=True)
class L3OutNodeConfig:
    nodeID: str
    routerID: str
    podID: str = "1"
    useRouteIDAsLoopback: bool = False


@dataclass(kw_only=True)
class L3OutBGPControl:
    allowSelfAS: bool = False
    asOverride: bool = False
    disablePeerASCheck: bool = False
    nextHopSelf: bool = False
    sendCommunity: bool = False
    sendExtendedCommunity: bool = False
    sendDomainPath: bool = False


@dataclass(kw_only=True)
class L3OutBGPPeerControl:
    bfd: bool = True
    disableConnectedCheck: bool = False


@dataclass(kw_only=True)
class L3OutBGPPeerConfig:
    peerAddressV4: str
    peerAsn: int
    peerAddressV6: str | None = None
    adminState: Literal["enabled", "disabled"] = "enabled"
    authEnabled: bool = False
    allowedSelfASCount: int = 3
    ebpgMultiHopTTL: int = 1
    localAsnConfig: str = "none"
    bgpControls: L3OutBGPControl = field(default_factory=L3OutBGPControl)
    peerControls: L3OutBGPPeerControl = field(default_factory=L3OutBGPPeerControl)


@dataclass(kw_only=True)
class L3OutIntPhysicalPort:
    primaryV4: str
    nodeID: str
    portID: str
    bgpPeers: List[L3OutBGPPeerConfig]
    type: Literal["interfaces"] = "interfaces"
    portType: Literal["port", "pc"] = "port"
    primaryV6: str | None = None
    podID: str = "1"


@dataclass(kw_only=True)
class L3OutIntPortChannel:
    primaryV4: str
    portChannelName: str
    bgpPeers: List[L3OutBGPPeerConfig]
    type: Literal["interfaces"] = "interfaces"
    portType: Literal["port", "pc"] = "pc"
    primaryV6: str | None = None


@dataclass(kw_only=True)
class L3OutSubIntPhysicalPort(L3OutIntPhysicalPort):
    encapVal: int
    type: Literal["subInterfaces"] = "subInterfaces"
    encapType: Literal["vlan", "vxlan"] = "vlan"


@dataclass(kw_only=True)
class L3OutSubIntPortChannel(L3OutIntPortChannel):
    encapVal: int
    type: Literal["subInterfaces"] = "subInterfaces"
    encapType: Literal["vlan", "vxlan"] = "vlan"


@dataclass(kw_only=True)
class L3OutSVIPhysicalPort(L3OutSubIntPhysicalPort):
    encapVal: int
    type: Literal["sviInterfaces"] = "sviInterfaces"
    encapType: Literal["vlan", "vxlan"] = "vlan"
    sviMode: Literal["trunk", "access", "access8021p"] = "trunk"


@dataclass(kw_only=True)
class L3OutSVIPortChannel(L3OutSubIntPortChannel):
    encapVal: int
    type: Literal["sviInterfaces"] = "sviInterfaces"
    encapType: Literal["vlan", "vxlan"] = "vlan"
    sviMode: Literal["trunk", "access", "access8021p"] = "trunk"


type L3OutInterfaceConfig = L3OutIntPortChannel | L3OutIntPhysicalPort
type L3OutSubInterfaceConfig = L3OutSubIntPhysicalPort | L3OutSubIntPortChannel
type L3OutSviInterfaceConfig = L3OutSVIPhysicalPort | L3OutSVIPortChannel


@dataclass(kw_only=True)
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
    routingProtocol: Literal["bgp", "static"]
    interfaces: List[L3OutInterfaceConfig | L3OutSubInterfaceConfig | L3OutSviInterfaceConfig]
    exportRouteMap: str | None = None
    importRouteMap: str | None = None
    importRouteControl: bool = False


@dataclass(kw_only=True)
class EEPGL3OutInfo:
    site: str
    l3outTemplate: str
    l3outName: str
