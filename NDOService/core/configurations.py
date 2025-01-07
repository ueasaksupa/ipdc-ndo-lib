from dataclasses import dataclass, field
from typing import List, Literal


@dataclass(kw_only=True)
class StaticPortPhy:
    nodeId: str
    port_type: Literal["port"] = "port"
    port_name: str
    port_mode: Literal["regular", "native", "untagged"]
    vlan: int


@dataclass(kw_only=True)
class StaticPortPC:
    port_type: Literal["dpc"] = "dpc"
    port_name: str
    port_mode: Literal["regular", "native", "untagged"]
    vlan: int


@dataclass(kw_only=True)
class StaticPortVPC:
    port_type: Literal["vpc"] = "vpc"
    port_name: str
    port_mode: Literal["regular", "native", "untagged"]
    vlan: int


@dataclass(kw_only=True)
class EPGConfig:
    """
    Parameters:
    - epg_desc : description of EPG
    - linked_template : name of the template that BridgeDomain is linked to
    - linked_bd : name of the BridgeDomain that EPG is linked to
    - linked_schema : (optional) name of the schema that EPG is linked to, default is the same schema as the linked_bd
    - proxyArp : enable or disable proxy ARP
    - mCastSource : enable or disable multicast source
    - preferredGroup : enable or disable preferred group
    - intraEpg : intra EPG enforcement [unenforced, enforced]
    """

    epg_desc: str = ""
    linked_template: str
    linked_bd: str
    linked_schema: str | None = None
    proxyArp: bool = False
    mCastSource: bool = False
    preferredGroup: bool = False
    intraEpg: Literal["unenforced", "enforced"] = "unenforced"


@dataclass(kw_only=True)
class BridgeDomainSubnet:
    """
    ### Note scope defination :
    - ip : IP address with prefix format `(ww.xx.yy.zz/aa)`
    - scope private is equal to `Private to VRF`
    - scope public is equal to `Advertised Externally`
    """

    ip: str = ""
    description: str = ""
    scope: Literal["private", "public"] = "public"
    shared: bool = False
    querier: bool = False
    noDefaultGateway: bool = False
    virtual: bool = False
    primary: bool = False
    ipDPLearning: Literal["enabled", "disabled"] = "enabled"


@dataclass(kw_only=True)
class BridgeDomainConfig:
    """
    Parameters:
    - l2Stretch : if True it will create L2 stretch BD, if False subnets and intersiteBumTrafficAllow properties are ignored
    - perSiteSubnet : List of tuple with site name and BridgeDomainSubnet object. Its only used when l2Stretch is False
    """

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
    perSiteSubnet: List[tuple[str, BridgeDomainSubnet]] = field(default_factory=list)


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
    """
    ### Parameter Notes:
    - prefix : IP address with prefix format `(ww.xx.yy.zz/aa)`
    """

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
    detectionMultiplier: int = 3
    minRxInterval: int = 50
    minTxInterval: int = 50
    adminState: Literal["enabled", "disabled"] = "enabled"
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
class L3OutStaticRouteNextHop:
    """
    ### Parameter Notes:
    - nextHopIP : IP address format (ww.xx.yy.zz)
    - preference : is `Administrative Distance`
    """

    nextHopIP: str
    preference: int = 0


@dataclass(kw_only=True)
class L3OutStaticRouteConfig:
    """
    ### Parameter Notes:
    - prefix : IP address with prefix format `(ww.xx.yy.zz/aa)`
    - fallbackPref : is `Administrative Distance` incase the AD in each nexthop is unspecified it will fallback to use this AD. Default is 1
    - nullNextHop : if it true `it will create a static route to Null0`
    """

    prefix: str
    fallbackPref: int = 1
    enableBFDTracking: bool = False
    nullNextHop: bool = False
    nextHops: List[L3OutStaticRouteNextHop]


@dataclass(kw_only=True)
class L3OutNodeConfig:
    """
    ### Parameter Notes:
    nodeID : node id example "1101"
    routerID : IP address format (ww.xx.yy.zz)
    """

    nodeID: str
    routerID: str
    podID: str = "1"
    useRouteIDAsLoopback: bool = False
    staticRoutes: List[L3OutStaticRouteConfig] = field(default_factory=list)


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
    importRouteMap: str | None = None
    exportRouteMap: str | None = None
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


L3OutInterfaceConfig = L3OutIntPortChannel | L3OutIntPhysicalPort
L3OutSubInterfaceConfig = L3OutSubIntPhysicalPort | L3OutSubIntPortChannel
L3OutSviInterfaceConfig = L3OutSVIPhysicalPort | L3OutSVIPortChannel


@dataclass(kw_only=True)
class L3OutConfig:
    """
    Parameter documentation:
    - name : the name of L3OUT template
    - vrf : the VRF name for this L3OUT
    - l3domain : name of L3 domain
    - nodes : List of L3OutNodeConfig object
    - routingProtocol : either bgp or ospf
    - exportRouteMap : name of route map in Tenant policy
    - interfaces : List of L3OutInterfaceConfig object
    - pimEnabled : PIM setting default is disabled
    - interfaceRoutingPolicy : name of L3Out Interface Routing Policy in Tenant policy
    """

    name: str
    vrf: str
    l3domain: str
    nodes: List[L3OutNodeConfig]
    routingProtocol: Literal["bgp"] | None = None
    interfaces: List[L3OutInterfaceConfig | L3OutSubInterfaceConfig | L3OutSviInterfaceConfig]
    exportRouteMap: str | None = None
    importRouteMap: str | None = None
    importRouteControl: bool = False
    pimEnabled: bool = False
    interfaceRoutingPolicy: str | None = None


@dataclass(kw_only=True)
class ExternalEpgToL3OutBinding:
    site: str
    l3outTemplate: str
    l3outName: str


@dataclass(kw_only=True)
class StormCtlConfig:
    """
    ### Note:
    - action : either drop or shutdown
    - soakInstCount : The packets exceeding the threshold are dropped for <sec> seconds and the port is shutdown on the <sec>th second
    """

    broadcastPPS: int = 1000
    broadcastMaxBurstPPS: int = 1000
    multicastPPS: int = 1000
    multicastMaxBurstPPS: int = 1000
    unicastPPS: int = 500
    unicastMaxBurstPPS: int = 500
    action: Literal["drop", "shutdown"] = "drop"
    soakInstCount: int = 3
