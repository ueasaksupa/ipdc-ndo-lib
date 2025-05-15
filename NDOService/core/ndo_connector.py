from .path_const import *
from .types import *
from .configurations import *

from pprint import pprint
from dataclasses import asdict
from typing import Literal, Any, Tuple
import requests
import urllib3
import time
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NDOTemplate:
    def __init__(self, host, username, password, port=443, delay: None | float = None) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.domain = "local"
        self.base_path = f"https://{self.host}:{port}"
        self.sitename_id_map = {}
        self.siteid_name_map = {}
        self.fabric_res_phyif_map = {}
        self.session = requests.Session()
        self.delay = delay
        # LOGIN
        self.login()

    # ** INTERNAL ONLY ** UTIL METHODs

    def __get_port_resource_path(
        self, staticport: StaticPortPhy | StaticPortPC | StaticPortVPC, site_name: str, pod: str, strict_check: bool
    ):
        path = ""
        if staticport.port_type == "vpc":
            vpc_resource = self.find_vpc_by_name(staticport.port_name, site_name)
            if not vpc_resource:
                raise Exception(
                    f"VPC resource name {staticport.port_name} does not exist in the Fabric Resource Policy."
                )
            path = vpc_resource["path"]
        elif staticport.port_type == "dpc":
            pc_resource = self.find_pc_by_name(staticport.port_name, site_name)
            if not pc_resource:
                raise Exception(
                    f"PC resource name {staticport.port_name} does not exist in the Fabric Resource Policy."
                )
            path = pc_resource["path"]
        elif staticport.port_type == "port":
            portId = staticport.port_name.replace("eth", "")
            if strict_check and portId not in self.fabric_res_phyif_map[f"{site_name}__{staticport.nodeId}"]:
                raise ValueError(
                    f"You're adding port({staticport.nodeId}-{portId}) that hasn't been defined in the fabric resource yet. Please define port in fabric resource before create the service."
                )

            path = f"topology/{pod}/paths-{staticport.nodeId}/pathep-[eth{portId}]"
        else:
            raise ValueError(f"port_type {staticport.port_type} is not supported")

        return path

    def __append_fabricRes_intf_object(
        self, key: str, template: dict, port_config: PhysicalIntfResource | PortChannelResource | VPCResource
    ):
        if not template[key]:
            template[key] = [asdict(port_config)]
            return
        # check whether the object name already exist.
        filter_object = list(filter(lambda i: i["name"] == port_config.name, template[key]))
        if len(filter_object) > 0:
            print(f"  |--- {key} name {port_config.name} already exist.")
            return
        template[key].append(asdict(port_config))

    def __append_l3out_to_external_epg_site(
        self, schema: dict, template_name: str, eepg_name: str, l3outList: List[ExternalEpgToL3OutBinding]
    ) -> None:
        for l3out in l3outList:
            for site in schema["sites"]:
                if site["siteId"] != self.sitename_id_map[l3out.site] or site["templateName"] != template_name:
                    continue

                l3outTemplate = self.find_l3out_template_by_name(l3out.l3outTemplate)
                if l3outTemplate is None:
                    raise ValueError(f"L3out template {l3out.l3outTemplate} does not exist.")
                l3outObject = list(
                    filter(lambda l: l["name"] == l3out.l3outName, l3outTemplate["l3outTemplate"]["l3outs"])
                )
                if len(l3outObject) == 0:
                    raise Exception(f"L3out {l3out.l3outName} does not exist in template {l3out.l3outTemplate}")

                sitePayload = {
                    "externalEpgRef": {"templateName": template_name, "externalEpgName": eepg_name},
                    "l3outRef": l3outObject[0]["uuid"],
                }
                # check if l3out already exist in the site
                eepg_site = list(filter(lambda s: eepg_name in s["externalEpgRef"], site["externalEpgs"]))
                if len(eepg_site) > 0:
                    eepg_site[0]["l3outRef"] = l3outObject[0]["uuid"]
                else:
                    site["externalEpgs"].append(sitePayload)

    def __generate_routeMap_attr_payload(self, attrs: RouteMapAttributes) -> dict:
        actionFields = {}
        if attrs.setNextHopPropagate is not None:
            actionFields["setNextHopPropagate"] = attrs.setNextHopPropagate
        if attrs.setPreference is not None:
            actionFields["setPreference"] = attrs.setPreference
        if attrs.setWeight is not None:
            actionFields["setWeight"] = attrs.setWeight
        if attrs.setMultiPath is not None:
            actionFields["setMultiPath"] = attrs.setMultiPath
            if attrs.setMultiPath:
                actionFields["setNextHopPropagate"] = True
        if attrs.setAsPath is not None:
            actionFields["setAsPath"] = (
                [
                    {
                        "criteria": attrs.setAsPath.criteria,
                        "pathASNs": [
                            {"asn": asn, "order": i} for i, asn in enumerate(attrs.setAsPath.pathASNs, start=1)
                        ],
                        "asnCount": attrs.setAsPath.asnCount,
                    }
                ]
                if attrs.setAsPath
                else None
            )
        return actionFields

    def __generate_routeMap_entry_payload(self, entry: RouteMapEntry) -> dict:
        prefixes = []
        for prefix in entry.prefixes:
            prefixes.append(
                {
                    "prefix": prefix.prefix,
                    "fromPfxLen": prefix.fromPfxLen,
                    "toPfxLen": prefix.toPfxLen,
                    "aggregate": prefix.aggregate,
                }
            )
        entryPayload = {
            "rtMapContext": {"order": entry.order, "name": entry.name, "action": entry.action},
            "matchRule": [{"matchPrefixList": prefixes}],
        }
        if entry.attributes is not None:
            entryPayload["setAction"] = [self.__generate_routeMap_attr_payload(entry.attributes)]
        return entryPayload

    def __merge_routeMap_payload(self, currentRM: dict, rmConfig: RouteMapConfig) -> None:
        # indexing current entry
        entIndex = {}
        prefixIndex = {}
        for entry in currentRM["rtMapEntryList"]:
            entryName = entry["rtMapContext"]["name"]
            entIndex[entryName] = entry
            for prefix in entry["matchRule"][0]["matchPrefixList"]:
                prefixKey = entryName + "_" + prefix["prefix"]
                prefixIndex[prefixKey] = prefix

        for rmEntry in rmConfig.entryList:
            if rmEntry.name not in entIndex:
                currentRM["rtMapEntryList"].append(self.__generate_routeMap_entry_payload(rmEntry))
                continue

            entry = entIndex[rmEntry.name]
            if "matchRule" not in entry:
                entry["matchRule"] = [
                    {
                        "matchPrefixList": [
                            {
                                "prefix": p.prefix,
                                "fromPfxLen": p.fromPfxLen,
                                "toPfxLen": p.toPfxLen,
                                "aggregate": p.aggregate,
                            }
                            for p in rmEntry.prefixes
                        ]
                    }
                ]
            else:
                for p in rmEntry.prefixes:
                    key = rmEntry.name + "_" + p.prefix
                    if key not in prefixIndex:
                        entry["matchRule"][0]["matchPrefixList"].append(
                            {
                                "prefix": p.prefix,
                                "fromPfxLen": p.fromPfxLen,
                                "toPfxLen": p.toPfxLen,
                                "aggregate": p.aggregate,
                            }
                        )
                    else:
                        prefixIndex[key]["fromPfxLen"] = p.fromPfxLen
                        prefixIndex[key]["toPfxLen"] = p.toPfxLen
                        prefixIndex[key]["aggregate"] = p.aggregate

            if rmEntry.attributes is not None:
                actionFields = self.__generate_routeMap_attr_payload(rmEntry.attributes)
                if "setAction" not in entry:
                    entry["setAction"] = [actionFields]
                else:
                    entry["setAction"][0].update(actionFields)

    def __generate_routeMap_payload(self, rnConfig: RouteMapConfig):
        entryList = []
        for entry in rnConfig.entryList:
            entryList.append(self.__generate_routeMap_entry_payload(entry))
        completed_payload = {"name": rnConfig.name, "description": rnConfig.description, "rtMapEntryList": entryList}
        return completed_payload

    def __generate_l3out_bgppeer_payload(self, tenant_id: str, bgpPeers: List[L3OutBGPPeerConfig]) -> List:
        peer_payload = []
        for peer in bgpPeers:
            if peer.importRouteMap is None and peer.exportRouteMap is None:
                peer_payload.append(asdict(peer))
            else:
                print(
                    f"  |--- Apply routeMap in peer level for peer: {peer.peerAddressV4 if peer.peerAddressV4 else peer.peerAddressV6}"
                )
                tmp = asdict(peer)
                if peer.importRouteMap is not None:
                    im_routemap = self.find_template_object_by_name(
                        peer.importRouteMap, f"type=routeMap&tenant-id={tenant_id}"
                    )
                    if im_routemap is None:
                        raise Exception(f"RouteMap {peer.importRouteMap} does not exist.")
                    tmp["importRouteMapRef"] = im_routemap["uuid"]
                if peer.exportRouteMap is not None:
                    ex_routemap = self.find_template_object_by_name(
                        peer.exportRouteMap, f"type=routeMap&tenant-id={tenant_id}"
                    )
                    if ex_routemap is None:
                        raise Exception(f"RouteMap {peer.exportRouteMap} does not exist.")
                    tmp["exportRouteMapRef"] = ex_routemap["uuid"]

                peer_payload.append(tmp)
        return peer_payload

    def __generate_l3out_phyintf(
        self, tenant_id: str, site_name: str, intfConfig: L3OutInterfaceConfig, intfRoutingPol: str | None
    ) -> dict:
        sec_ip_payload = (
            [{"address": ip} for ip in intfConfig.secondaryAddrs] if intfConfig.secondaryAddrs is not None else None
        )
        INTF_PAYLOAD = {
            "group": "IF_GROUP_POLICY" if intfRoutingPol is not None else "",
            "pathType": intfConfig.portType,
            "addresses": {
                "primaryV4": intfConfig.primaryV4,
                "primaryV6": intfConfig.primaryV6,
                "secondary": sec_ip_payload,
            },
            "mac": "00:22:BD:F8:19:FF",
            "mtu": "inherit",
            "bgpPeers": self.__generate_l3out_bgppeer_payload(tenant_id, intfConfig.bgpPeers),
        }
        if isinstance(intfConfig, L3OutIntPortChannel):
            pcintf = self.find_pc_by_name(intfConfig.portChannelName, site_name)
            if pcintf is None:
                raise Exception(f"PortChannel {intfConfig.portChannelName} does not exist in the fabric resource.")
            INTF_PAYLOAD["pathRef"] = pcintf["uuid"]
        elif isinstance(intfConfig, L3OutIntPhysicalPort):
            INTF_PAYLOAD["podID"] = intfConfig.podID
            INTF_PAYLOAD["nodeID"] = intfConfig.nodeID
            INTF_PAYLOAD["path"] = f"eth{intfConfig.portID.removeprefix('eth')}"

        return INTF_PAYLOAD

    def __generate_l3out_subintf(
        self, tenant_id: str, site_name: str, intfConfig: L3OutSubInterfaceConfig, intfRoutingPol: str | None
    ) -> dict:
        INTF_PAYLOAD = self.__generate_l3out_phyintf(tenant_id, site_name, intfConfig, intfRoutingPol)
        INTF_PAYLOAD["encap"] = {"encapType": intfConfig.encapType, "value": intfConfig.encapVal}
        return INTF_PAYLOAD

    def __generate_l3out_svivpcintf(
        self, tenant_id: str, site_name: str, intfConfig: L3OutSVIVPC, intfRoutingPol: str | None
    ) -> dict:
        sec_ip_payload = (
            [{"address": ip} for ip in intfConfig.secondaryAddrs] if intfConfig.secondaryAddrs is not None else None
        )
        INTF_PAYLOAD = {
            "group": "IF_GROUP_POLICY" if intfRoutingPol is not None else "",
            "pathType": "vpc",
            "addresses": {
                "primaryV4": intfConfig.a_primaryV4,
                "primaryV6": intfConfig.a_primaryV6,
                "secondary": sec_ip_payload,
            },
            "sideBAddresses": {
                "primaryV4": intfConfig.b_primaryV4,
                "primaryV6": intfConfig.b_primaryV6,
                "secondary": sec_ip_payload,
            },
            "mac": "00:22:BD:F8:19:FF",
            "mtu": "inherit",
            "bgpPeers": self.__generate_l3out_bgppeer_payload(tenant_id, intfConfig.bgpPeers),
        }

        vpcintf = self.find_vpc_by_name(intfConfig.vpcName, site_name)
        if vpcintf is None:
            raise Exception(f"PortChannel {intfConfig.vpcName} does not exist in the fabric resource.")
        INTF_PAYLOAD["pathRef"] = vpcintf["uuid"]
        INTF_PAYLOAD["encap"] = {"encapType": intfConfig.encapType, "value": intfConfig.encapVal}
        return INTF_PAYLOAD

    def __generate_l3out_sviintf(
        self, tenant_id: str, site_name: str, intfConfig: L3OutSviInterfaceConfig, intfRoutingPol: str | None
    ) -> dict:
        if isinstance(intfConfig, L3OutSVIVPC):
            INTF_PAYLOAD = self.__generate_l3out_svivpcintf(tenant_id, site_name, intfConfig, intfRoutingPol)
        else:
            INTF_PAYLOAD = self.__generate_l3out_subintf(tenant_id, site_name, intfConfig, intfRoutingPol)
        INTF_PAYLOAD["svi"] = {"encapScope": "local", "autostate": intfConfig.autoState, "mode": intfConfig.sviMode}
        return INTF_PAYLOAD

    def __generate_l3out_interface_payload(self, template: dict, payload: dict, l3outConfig: L3OutConfig) -> None:
        payload["interfaces"] = []
        payload["subInterfaces"] = []
        payload["sviInterfaces"] = []
        tenant_id = template["l3outTemplate"]["tenantId"]
        for intf in l3outConfig.interfaces:
            if intf.portType not in ["port", "pc", "vpc"]:
                raise ValueError(f"portType {intf.portType} is not supported")
            if intf.type == "interfaces":
                payload["interfaces"].append(
                    self.__generate_l3out_phyintf(
                        tenant_id,
                        self.siteid_name_map[template["l3outTemplate"]["siteId"]],
                        intf,
                        l3outConfig.interfaceRoutingPolicy,
                    )
                )
            elif intf.type == "subInterfaces":
                payload["subInterfaces"].append(
                    self.__generate_l3out_subintf(
                        tenant_id,
                        self.siteid_name_map[template["l3outTemplate"]["siteId"]],
                        intf,
                        l3outConfig.interfaceRoutingPolicy,
                    )
                )
            elif intf.type == "sviInterfaces":
                payload["sviInterfaces"].append(
                    self.__generate_l3out_sviintf(
                        tenant_id,
                        self.siteid_name_map[template["l3outTemplate"]["siteId"]],
                        intf,
                        l3outConfig.interfaceRoutingPolicy,
                    )
                )
            else:
                raise ValueError(f"interface type {intf.type} is not supported")

    def __generate_l3out_payload(self, template: dict, l3outConfig: L3OutConfig) -> dict:
        vrf = self.find_template_object_by_name(
            l3outConfig.vrf, f"type=vrf&tenant-id={template['l3outTemplate']['tenantId']}"
        )
        if vrf is None:
            raise Exception(f"VRF {l3outConfig.vrf} does not exist.")

        if l3outConfig.exportRouteMap is not None:
            ex_routemap = self.find_template_object_by_name(
                l3outConfig.exportRouteMap, f"type=routeMap&tenant-id={template['l3outTemplate']['tenantId']}"
            )
            if ex_routemap is None:
                raise Exception(f"RouteMap {l3outConfig.exportRouteMap} does not exist.")

        if (l3outConfig.importRouteControl is not None) and (l3outConfig.importRouteMap is not None):
            im_routemap = self.find_template_object_by_name(
                l3outConfig.importRouteMap, f"type=routeMap&tenant-id={template['l3outTemplate']['tenantId']}"
            )
            if im_routemap is None:
                raise Exception(f"RouteMap {l3outConfig.importRouteMap} does not exist.")

        l3domain = self.find_domain_by_name(
            l3outConfig.l3domain, site_id=template["l3outTemplate"]["siteId"], type="l3"
        )
        if l3domain is None:
            raise Exception(f"l3domain {l3outConfig.l3domain} does not exist.")

        payload = {
            "name": l3outConfig.name,
            "vrfRef": vrf["uuid"],
            "l3domain": l3domain["uuid"],
            "routingProtocol": l3outConfig.routingProtocol,
            "exportRouteMapRef": None if l3outConfig.exportRouteMap is None else ex_routemap["uuid"],
            "importRouteMapRef": (
                None if not l3outConfig.importRouteControl or not l3outConfig.importRouteMap else im_routemap["uuid"]
            ),
            "importRouteControl": l3outConfig.importRouteControl,
            "nodes": list(map(lambda obj: asdict(obj), l3outConfig.nodes)),
            "pim": l3outConfig.pimEnabled,
        }
        if l3outConfig.interfaceRoutingPolicy is not None:
            intf_routing_pol = self.find_template_object_by_name(
                l3outConfig.interfaceRoutingPolicy,
                f"type=l3OutIntfPolGroup&tenant-id={template['l3outTemplate']['tenantId']}",
            )
            if intf_routing_pol is None:
                raise ValueError(f"Interface routing policy {l3outConfig.interfaceRoutingPolicy} does not exist.")

            payload["interfaceGroups"] = [
                {
                    "name": "IF_GROUP_POLICY",
                    "interfaceRoutingPolicyRef": intf_routing_pol["uuid"],
                    "qosPriority": "unspecified",
                }
            ]

        self.__generate_l3out_interface_payload(template, payload, l3outConfig)
        # pprint(payload)
        return payload

    def __send_deploy_task_request(self, url: str, payload: dict) -> None:
        task_resp = self.session.post(url, json=payload)
        if task_resp.status_code >= 400:
            raise Exception(task_resp.json())
        task_resp = task_resp.json()
        # check deployment status
        task_status_url = f"{self.base_path}{PATH_DEPLOYMENT}/{task_resp['id']}"
        for i in range(20):
            print(f"--- Checking deployment status ...({i})")
            resp = self.session.get(task_status_url).json()
            if resp["operDetails"]["taskStatus"] in ["Complete", "Error", "Timeout"]:
                print(f"  |--- {resp['operDetails']['taskStatus']}")
                break
            time.sleep(2)

    def __flattern_port_list(self, raw: str) -> list[str]:
        result = []
        matcher = re.compile(r"(\d+)/(\d+)-(\d+)")
        interfaces = raw.split(",")
        for intf in interfaces:
            intf = intf.strip()
            if res := matcher.match(intf):
                result.extend([f"{res.group(1)}/{i}" for i in range(int(res.group(2)), int(res.group(3)) + 1)])
            else:
                result.append(intf)
        return result

    def __get_all_phyintf_resource(self) -> dict[str, list[str]]:
        """
        This is helper function for creating map of physical interface per node
        dict structure:
        {
            [nodename]: ["eth1/1","eth1/2" ....]
        }
        """
        portmap: dict[str, list[str]] = {}
        url = f"{self.base_path}{PATH_FABRIC_RESOURCES_SUM}"
        resp = self.session.get(url).json()
        fr_template_ids = []
        for fabric_template in resp:
            for pol in fabric_template["policies"]:
                if pol["objType"] == "interfaceProfile" and pol["count"] > 0:
                    fr_template_ids.append(fabric_template["templateId"])
                    break
        for id in fr_template_ids:
            url = f"{self.base_path}{PATH_TEMPLATES}/{id}"
            template = self.session.get(url).json()
            for site in template["fabricResourceTemplate"]["sites"]:
                sitename = self.siteid_name_map[site["siteId"]]
                for phyif_profile in template["fabricResourceTemplate"]["template"]["interfaceProfiles"]:
                    for node in phyif_profile["nodes"]:
                        nodeKey = f"{sitename}__{node}"
                        if nodeKey not in portmap:
                            portmap[nodeKey] = self.__flattern_port_list(phyif_profile["interfaces"])
                        else:
                            portmap[nodeKey].extend(self.__flattern_port_list(phyif_profile["interfaces"]))
        return portmap

    # UTILS
    def login(self) -> None:
        print("- TRYING TO LOGIN TO NDO")
        self.session = requests.session()
        self.session.verify = False
        self.session.trust_env = False
        payload = {
            "userName": self.username,
            "userPasswd": self.password,
            "domain": self.domain,
        }
        url = f"{self.base_path}{PATH_LOGIN}"
        self.session.post(url, json=payload).json()
        # create site name to ID map
        print("- INDEXING NODE IDS")
        for site in self.get_all_sites():
            self.sitename_id_map[site["name"]] = site["id"]
            self.siteid_name_map[site["id"]] = site["name"]
        #
        print("- INDEXING PHYSICAL PORTS AND NODES")
        self.fabric_res_phyif_map = self.__get_all_phyintf_resource()
        # pprint(self.fabric_res_phyif_map)

    def get_all_sites(self) -> list[Site]:
        url = f"{self.base_path}{PATH_SITES}"
        resp = self.session.get(url).json()
        return resp["sites"]

    def find_tenant_by_name(self, tenant_name: str) -> Tenant | None:
        url = f"{self.base_path}{PATH_TENANTS}"
        # Get all
        resp: list = self.session.get(url).json()["tenants"]
        # filter by name
        filter_tenants = list(filter(lambda t: t["name"] == tenant_name, resp))
        if len(filter_tenants) == 0:
            return None

        return filter_tenants[0]

    def find_schema_by_name(self, schema_name: str) -> Schema | None:
        url = f"{self.base_path}{PATH_SCHEMAS_LIST}"
        # Get all
        resp: list = self.session.get(url).json()["schemas"]
        # filter by name
        filter_schemas = list(filter(lambda s: s["displayName"] == schema_name, resp))
        if len(filter_schemas) > 0:
            # re-query to get full schema object
            return self.session.get(f"{self.base_path}{PATH_SCHEMAS}/{filter_schemas[0]['id']}").json()

        return None

    def find_l3out_template_by_name(self, l3out_name: str) -> L3OutTemplate | None:
        url = f"{self.base_path}{PATH_L3OUT_TEMPLATE_SUM}"
        # Get all
        resp: list = self.session.get(url).json()
        # filter by name
        filtered = list(filter(lambda t: t["templateName"] == l3out_name, resp))
        if len(filtered) > 0:
            # re-query to get full object
            return self.session.get(f"{self.base_path}{PATH_TEMPLATES}/{filtered[0]['templateId']}").json()

        return None

    def find_tenant_policies_template_by_name(self, name: str) -> Template | None:
        url = f"{self.base_path}{PATH_TENANT_POLICIES_TEMPLATE_SUM}"
        # Get all
        resp: list = self.session.get(url).json()
        # filter by name
        filtered = list(filter(lambda t: t["templateName"] == name, resp))
        if len(filtered) > 0:
            # re-query to get full object
            return self.session.get(f"{self.base_path}{PATH_TEMPLATES}/{filtered[0]['templateId']}").json()

        return None

    def find_template_object_by_name(self, target_name: str, query: str) -> Template | None:
        url = f"{self.base_path}{PATH_TEMPLATES_OBJECT}?{query}"
        resp = self.session.get(url)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        filtered = list(filter(lambda v: v["name"] == target_name, resp.json()))
        if len(filtered) == 0:
            return None

        return filtered[0]

    def isSchemaStateSync(self, schema_name: str | None = None, schema: Schema | None = None) -> bool:
        """
        This method is for checking schema state with NDO, whether it sync or out-of-sync.

        you can provide parameter either `schema_name` or `schema` object return from `find_schema_by_name` method
        """

        if schema_name is None and schema is None:
            raise ValueError("Either schema_name or schema object is required.")

        schemaId = ""
        if schema is not None:
            schemaId = schema["id"]
        elif schema_name is not None:
            sch = self.find_schema_by_name(schema_name)
            if sch is None:
                raise ValueError(f"schema {schema_name} is not exist.")
            schemaId = sch["id"]

        url = f"{self.base_path}{PATH_SCHEMAS}/{schemaId}/policy-states"
        resp: list[dict] = self.session.get(url).json()["policyStates"]
        for state in resp:
            if len(state.keys()) != 3:
                return False
        return True

    # Tenant Template
    # All of the methods in this Tenant Template will return the updated schema object.
    # Note that it won't change the schema object in the NDO until you call the `save_schema` method with the updated schema object.

    def save_schema(self, schema: dict) -> Schema:
        """
        Saves the given schema. This method is used to save the schema after making changes to it.

        Args:
            schema (dict): The schema to be saved.

        Returns:
            Schema: The saved schema.

        Raises:
            Exception: If the request to save the schema fails.
        """
        print(f"--- Saving schema {schema['displayName']}")
        url = f"{self.base_path}{PATH_SCHEMAS}/{schema['id']}?enableVersionCheck=true"
        resp = self.session.put(url, json=schema)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)
        return resp.json()

    def create_tenant(self, tenant_name: str, sites: list[str], tenant_desc: str = "") -> Tenant:
        """
        Creates a new tenant with the given name, sites, and optional description.

        Args:
            tenant_name (str): The name of the tenant.
            sites (list[str]): A list of site names associated with the tenant.
            tenant_desc (str, optional): The description of the tenant. Defaults to "".

        Returns:
            Tenant: The created tenant object.

        Raises:
            Exception: If the site does not exist in the network.

        """
        print(f"--- Creating tenant {tenant_name}")

        tenant = self.find_tenant_by_name(tenant_name)
        if tenant is not None:
            print(f"  |--- Tenant {tenant_name} already exist")
            return tenant

        siteAssociations = []
        for sitename in sites:
            if sitename not in self.sitename_id_map:
                raise Exception(f"Site {sitename} not exist in the network.")
            site_payload = {
                "siteId": self.sitename_id_map[sitename],
                "securityDomains": None,
                "azureAccount": None,
                "awsAccount": None,
                "gcpAccount": None,
                "gatewayRouter": None,
            }
            siteAssociations.append(site_payload)

        payload = {
            "name": tenant_name,
            "displayName": tenant_name,
            "siteAssociations": siteAssociations,
            "userAssociations": [],
            "description": tenant_desc,
        }

        url = f"{self.base_path}{PATH_TENANTS}?enableVersionCheck=true"
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)
        return resp.json()

    def create_schema(self, schema_name: str, schema_desc: str = "") -> Schema:
        """
        Creates a new schema with the given name and description. If the schema already exists, it will return the existing schema.

        Args:
            schema_name (str): The name of the schema.
            schema_desc (str, optional): The description of the schema. Defaults to "".

        Returns:
            Schema: The created schema object.

        Raises:
            Exception: If the schema creation fails.

        """
        print(f"--- Creating schema {schema_name}")

        schema = self.find_schema_by_name(schema_name)
        if schema is not None:
            print(f"  |--- Schema {schema_name} already exist")
            return schema

        url = f"{self.base_path}{PATH_SCHEMAS}"
        payload = {"displayName": schema_name, "description": schema_desc}
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)
        return resp.json()

    def create_template(self, schema: dict, template_name: str, tenant_id: str) -> Template:
        """
        Creates a template in the given schema.

        Args:
            schema (dict): The schema to add the template to.
            template_name (str): The name of the template.
            tenant_id (str): The ID of the tenant.

        Returns:
            Template: The created template object.
        """

        print(f"--- Creating template {template_name}")

        if "templates" not in schema or not schema["templates"]:
            schema["templates"] = []
        filter_template = list(filter(lambda d: d["name"] == template_name, schema["templates"]))

        if len(filter_template) != 0:
            print(f"  |--- template {template_name} is already exists")
            return filter_template[0]

        payload = {
            "name": template_name,
            "tenantId": tenant_id,
            "displayName": template_name,
            "templateType": "stretched-template",
            "vrfs": [],
            "contracts": [],
            "filters": [],
            "anps": [],
            "bds": [],
            "externalEpgs": [],
        }

        schema["templates"].append(payload)
        print(f"  |--- Done")
        return schema["templates"][-1]

    def add_site_to_template(self, schema: dict, template_name: str, sites: list[str]) -> None:
        """
        Adds a site to a template in the given schema.

        Args:
            schema (dict): The schema containing the template and sites.
            template_name (str): The name of the template.
            sites (list[str]): The list of site names to be added.

        Raises:
            Exception: If the site does not exist.

        Returns:
            None: This method does not return anything.
        """

        for site in sites:
            print(f"--- Adding site {site} to template {template_name}")
            try:
                site_id = self.sitename_id_map[site]
                filter_site = list(
                    filter(lambda el: el["siteId"] == site_id and el["templateName"] == template_name, schema["sites"])
                )

                if len(filter_site) != 0:
                    print(f"  |--- Site {site} already exist in the template {template_name}")
                    continue

                payload = {
                    "name": site,
                    "siteId": site_id,
                    "templateName": template_name,
                }
                schema["sites"].append(payload)
                newSchema = self.save_schema(schema)

                # update schema with new schema
                schema["sites"] = newSchema["sites"]
                schema["_updateVersion"] = newSchema["_updateVersion"]
                print(f"  |--- Done")
            except Exception:
                raise Exception(f"Site {site} does not exist")

    def create_filter_under_template(self, schema: dict, template_name: str, filter_name: str) -> Filter:
        """
        Creates a filter under a specified template.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template to create the filter under.
            filter_name (str): The name of the filter to be created.

        Returns:
            Filter: The created filter object.

        Raises:
            Exception: If the specified template does not exist.
        """

        print(f"--- Creating filter {filter_name}")

        filter_template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(filter_template) == 0:
            raise Exception(f"Template {template_name} does not exist.")

        filter_object = list(filter(lambda d: d["name"] == filter_name, filter_template[0]["filters"]))
        if len(filter_object) != 0:
            print(f"  |--- Filter {filter_name} is already exist")
            return filter_object[0]

        payload = {
            "name": filter_name,
            "displayName": filter_name,
            "entries": [
                {
                    "name": "IP",
                    "displayName": "IP",
                    "description": "",
                    "etherType": "ip",
                    "arpFlag": "unspecified",
                    "ipProtocol": "unspecified",
                    "matchOnlyFragments": False,
                    "stateful": False,
                    "sourceFrom": "unspecified",
                    "sourceTo": "unspecified",
                    "destinationFrom": "unspecified",
                    "destinationTo": "unspecified",
                    "tcpSessionRules": ["unspecified"],
                }
            ],
        }

        filter_template[0]["filters"].append(payload)
        print(f"  |--- Done")
        return filter_template[0]["filters"][-1]

    def create_contract_under_template(
        self, schema: dict, template_name: str, contract_name: str, filter_name: str
    ) -> Contract:
        """
        Creates a contract under a template.
        Args:
            schema (dict): The schema containing templates and contracts.
            template_name (str): The name of the template.
            contract_name (str): The name of the contract to be created.
            filter_name (str): The name of the filter.
        Returns:
            Contract: The created contract.
        Raises:
            ValueError: If the specified template does not exist.
        """
        print(f"--- Creating contract {contract_name}")

        filter_template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(filter_template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        contract = list(filter(lambda d: d["name"] == contract_name, filter_template[0]["contracts"]))
        if len(contract) != 0:
            print(f"  |--- Contract {contract_name} is already exist")
            return contract[0]

        payload = {
            "name": contract_name,
            "displayName": contract_name,
            "filterRelationships": [
                {
                    "filterRef": {"templateName": template_name, "filterName": filter_name},
                    "directives": [],
                    "action": "permit",
                    "priorityOverride": "default",
                }
            ],
        }

        filter_template[0]["contracts"].append(payload)
        print(f"  |--- Done")
        return filter_template[0]["contracts"][-1]

    def create_vrf_under_template(
        self,
        schema: dict,
        template_name: str,
        vrf_name: str,
        contract_name: str | None = None,
        vrf_config: VrfConfig | None = None,
    ) -> Vrf:
        """
        Create a VRF under a template.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template.
            vrf_name (str): The name of the VRF to be created.
            contract_name (str, optional): The name of the contract.
            vrf_config (VrfConfig | None, optional): The configuration for the VRF. Defaults to None.

        Returns:
            Vrf: The created VRF.

        Raises:
            ValueError: If the vrf_config is not an instance of VrfConfig.
            ValueError: If the template does not exist.

        """
        print(f"--- Creating VRF {vrf_name}")
        if vrf_config is None:
            vrf_config = VrfConfig()
        elif not isinstance(vrf_config, VrfConfig):
            raise ValueError("vrf_config must be object of VrfConfig")

        template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        filter_vrf = list(filter(lambda d: d["name"] == vrf_name, template[0]["vrfs"]))
        if len(filter_vrf) != 0:
            print(f"  |--- VRF {vrf_name} is already exist")
            return filter_vrf[0]

        payload = {
            "displayName": vrf_name,
            "name": vrf_name,
            "vzAnyConsumerContracts": [{"contractRef": {"contractName": contract_name}}] if contract_name else [],
            "vzAnyProviderContracts": [{"contractRef": {"contractName": contract_name}}] if contract_name else [],
        }
        payload.update(asdict(vrf_config))

        template[0]["vrfs"].append(payload)
        print(f"  |--- Done")
        return template[0]["vrfs"][-1]

    # support replace mode
    def create_bridge_domain_under_template(
        self,
        schema: dict,
        template_name: str,
        linked_vrf_template: str,
        linked_vrf_name: str,
        bd_name: str,
        bd_config: BridgeDomainConfig | None = None,
        linked_vrf_schema: str | None = None,
        replace: bool = False,
    ) -> BD:
        """
        Creates a bridge domain under a template.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template.
            linked_vrf_template (str): The name of the linked VRF template.
            linked_vrf_name (str): The name of the linked VRF.
            linked_vrf_schema (str | None, optional): The name of the linked VRF schema. Defaults to None meaning the same schema as the template.
            bd_name (str): The name of the bridge domain.
            bd_config (BridgeDomainConfig | None, optional): The configuration for the bridge domain. Defaults to None.

        Returns:
            BD: The created bridge domain.

        Raises:
            ValueError: If bd_config is not an instance of BridgeDomainConfig.
            ValueError: If the template does not exist.
        """

        print(f"--- Creating BD {bd_name} under template {template_name}")
        if bd_config is None:
            bd_config = BridgeDomainConfig()
        elif not isinstance(bd_config, BridgeDomainConfig):
            raise ValueError("bd_config must be object of BridgeDomainConfig")

        filter_template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(filter_template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        filter_bd = list(filter(lambda d: d["name"] == bd_name, filter_template[0]["bds"]))
        if len(filter_bd) != 0:
            print(f"  |--- BD {bd_name} is already exist in template {template_name}")
            if replace:
                print(f"  |--- replace TRUE : Replacing {bd_name} config in template {template_name}")
            else:
                return filter_bd[0]

        # "vrfRef": f"/schemas/{schema['id']}/templates/{linked_vrf_template}/vrfs/{linked_vrf_name}",
        target_schema = schema if linked_vrf_schema is None else self.find_schema_by_name(linked_vrf_schema)
        if target_schema is None:
            raise ValueError(f"Linked VRF schema {linked_vrf_schema} does not exist.")
        payload = {
            "name": bd_name,
            "displayName": bd_name,
            "vrfRef": {
                "schemaID": target_schema["id"],
                "templateName": linked_vrf_template,
                "vrfName": linked_vrf_name,
            },
        }
        payload.update(asdict(bd_config))
        if bd_config.l2Stretch == False:
            print(
                "  |--- *** BD is not stretched, so subnets are removed and intersiteBumTrafficAllow is set to False ***"
            )
            payload["subnets"] = []
            payload["intersiteBumTrafficAllow"] = False
            # deploy per site subnet if config is set
            siteSubnetBySite: dict[str, List[dict]] = {}
            for perSiteSubnet in bd_config.perSiteSubnet:
                if perSiteSubnet[0] not in siteSubnetBySite:
                    siteSubnetBySite[perSiteSubnet[0]] = [asdict(perSiteSubnet[1])]
                else:
                    siteSubnetBySite[perSiteSubnet[0]].append(asdict(perSiteSubnet[1]))

            if len(siteSubnetBySite) > 0:
                for site in schema["sites"]:
                    # find subnet config for site
                    if self.siteid_name_map[site["siteId"]] not in siteSubnetBySite:
                        continue

                    bd_site_config = list(filter(lambda bd: bd_name in bd["bdRef"], site["bds"]))
                    if len(bd_site_config) == 0:
                        # create subnet object
                        site["bds"].append(
                            {
                                "bdRef": f"/schemas/{schema['id']}/templates/{template_name}/bds/{bd_name}",
                                "subnets": [asdict(perSiteSubnet[1])],
                            }
                        )
                    else:
                        bd_site_config[0]["subnets"] = siteSubnetBySite[self.siteid_name_map[site["siteId"]]]
        else:
            if len(bd_config.perSiteSubnet) != 0:
                print("  |--- *** BD is stretched, perSiteSubnet is not supported ***")
            del payload["perSiteSubnet"]

        if replace and len(filter_bd) != 0:
            filter_bd[0] = filter_bd[0].update(payload)
        else:
            filter_template[0]["bds"].append(payload)

        print(f"  |--- Done")
        return filter_template[0]["bds"][-1]

    def create_anp_under_template(self, schema: dict, template_name: str, anp_name: str, anp_desc: str = "") -> ANP:
        """
        Creates a new Application Network Profile (ANP) under a specified template.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template to create the ANP under.
            anp_name (str): The name of the ANP to create.
            anp_desc (str, optional): The description of the ANP. Defaults to "".

        Returns:
            ANP: The created ANP.

        Raises:
            ValueError: If the specified template does not exist.

        """
        print(f"--- Creating ANP under template {template_name}")
        filter_template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(filter_template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        filter_anp = list(filter(lambda anp: anp["name"] == anp_name, filter_template[0]["anps"]))
        if len(filter_anp) != 0:
            print(f"  |--- ANP {anp_name} is already exist in template {template_name}")
            return filter_anp[0]

        payload = {
            "name": anp_name,
            "displayName": anp_name,
            "description": anp_desc,
            "epgs": [],
        }
        filter_template[0]["anps"].append(payload)
        print(f"  |--- Done")
        return filter_template[0]["anps"][-1]

    def create_epg_under_template(self, schema: dict, anp_obj: dict, epg_name: str, epg_config: EPGConfig) -> EPG:
        """
        Creates an EPG (Endpoint Group) under a given ANP (Application Network Profile).

        Args:
            schema (dict): The schema containing the templates.
            anp_obj (dict): The ANP (Application Network Profile) object. This object should be obtained from `create_anp_under_template` method.
            epg_name (str): The name of the EPG (Endpoint Group) to be created.
            epg_config (EPGConfig): The configuration object for the EPG.

        Returns:
            EPG: The created EPG (Endpoint Group) object.

        Raises:
            ValueError: If epg_config is not an instance of EPGConfig.

        """
        if not isinstance(epg_config, EPGConfig):
            raise ValueError("epg_config must be instance of EPGConfig")

        print(f"--- Creating EPG {epg_name} under ANP {anp_obj['name']}")
        filter_epg = list(filter(lambda epg: epg["name"] == epg_name, anp_obj["epgs"]))

        if len(filter_epg) != 0:
            print(f"  |--- EPG {epg_name} is already exist in ANP {anp_obj['name']}")
            return filter_epg[0]

        # TODO
        # Parameterized flags
        target_schema = (
            schema if epg_config.linked_schema is None else self.find_schema_by_name(epg_config.linked_schema)
        )
        if target_schema is None:
            raise ValueError(f"Linked schema {epg_config.linked_schema} does not exist.")
        payload = {
            "epgType": "application",
            "name": epg_name,
            "displayName": epg_name,
            "description": epg_config.epg_desc,
            "bdRef": {
                "schemaID": target_schema["id"],
                "templateName": epg_config.linked_template,
                "bdName": epg_config.linked_bd,
            },
            "intraEpg": epg_config.intraEpg,
            "proxyArp": epg_config.proxyArp,
            "mCastSource": epg_config.mCastSource,
            "preferredGroup": epg_config.preferredGroup,
        }
        anp_obj["epgs"].append(payload)
        print(f"  |--- Done")
        return anp_obj["epgs"][-1]

    # support replace mode
    def create_ext_epg_under_template(
        self,
        schema: dict,
        template_name: str,
        epg_name: str,
        linked_vrf_name: str,
        linked_vrf_template: str,
        l3outToSiteInfo: List[ExternalEpgToL3OutBinding],
        linked_vrf_schema: str | None = None,
        epg_desc: str = "",
        eepg_subnets: List[ExternalEpgSubnet] = [],
        replace: bool = False,
    ) -> ExtEPG:
        """
        Creates an External EPG under a given template.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template.
            epg_name (str): The name of the External EPG.
            linked_vrf_name (str): The name of the VRF.
            linked_vrf_template (str): The name of the VRF template.
            linked_vrf_schema (str, optional): The name of the linked VRF schema. Defaults to None meaning the same schema as the template.
            l3outToSiteInfo (List[ExternalEpgToL3OutBinding]): The list of L3Out to site information.
            epg_desc (str, optional): The description of the External EPG. Defaults to "".

        Returns:
            ExtEPG: The created External EPG.

        Raises:
            ValueError: If the template does not exist.
        """
        print(f"--- Creating External EPG under template {template_name}")
        filter_template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(filter_template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        filter_eepg = list(filter(lambda anp: anp["name"] == epg_name, filter_template[0]["externalEpgs"]))
        if len(filter_eepg) != 0:
            print(f"  |--- External EPG {epg_name} is already exist in template {template_name}")
            if replace:
                print(f"  |--- replace TRUE : Replacing {epg_name} config in template {template_name}")
            else:
                return filter_eepg[0]

        target_schema = schema if linked_vrf_schema is None else self.find_schema_by_name(linked_vrf_schema)
        if target_schema is None:
            raise ValueError(f"Linked VRF schema {linked_vrf_schema} does not exist.")

        subnets = [
            {
                "ip": s.ip,
                "name": s.name,
                "scope": ["import-security"] if s.externalSubnet is True else [],
                "aggregate": [],
            }
            for s in eepg_subnets
        ]

        payload = {
            "name": epg_name,
            "displayName": epg_name,
            "extEpgType": "on-premise",
            "vrfRef": {
                "schemaID": target_schema["id"],
                "vrfName": linked_vrf_name,
                "templateName": linked_vrf_template,
            },
            "subnets": subnets,
            "description": epg_desc,
        }
        # Add External EPG to template
        if replace and len(filter_eepg) != 0:
            filter_eepg[0] = filter_eepg[0].update(payload)
        else:
            filter_template[0]["externalEpgs"].append(payload)

        self.__append_l3out_to_external_epg_site(schema, template_name, epg_name, l3outToSiteInfo)
        # Add L3Out to site
        print(f"  |--- Done")
        return filter_template[0]["externalEpgs"][-1]

    def change_ext_epg_l3out_binding(
        self, schema: dict, template_name: str, epg_name: str, l3outToSiteInfo: List[ExternalEpgToL3OutBinding]
    ) -> None:
        """
        Change the L3Out binding of an External EPG.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template.
            epg_name (str): The name of the External EPG.
            l3outToSiteInfo (List[ExternalEpgToL3OutBinding]): The list of L3Out to site information.

        Returns: None

        Raises:
            ValueError: If the template or ExternalEPG does not exist.
        """
        print(f"--- Changing External EPG L3out blinding from template {template_name}")
        filter_template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(filter_template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        filter_eepg = list(filter(lambda anp: anp["name"] == epg_name, filter_template[0]["externalEpgs"]))
        if len(filter_eepg) == 0:
            raise ValueError(f"External ExtermalEPG {epg_name} does not exist in template {template_name}")

        self.__append_l3out_to_external_epg_site(schema, template_name, epg_name, l3outToSiteInfo)

    def add_phy_domain_to_epg(
        self,
        schema: dict,
        template_name: str,
        anp_name: str,
        epg_name: str,
        domain: str,
        site_name: str,
    ) -> None:
        """
        Adds a physical domain to an EPG per site.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template.
            anp_name (str): The name of the ANP (Application Network Profile).
            epg_name (str): The name of the EPG (Endpoint Group).
            domain (str): The name of the physical domain to be added.
            site_name (str): The name of the target site.

        Raises:
            ValueError: If the site does not exist, the template with the site does not exist, the ANP does not exist, or the EPG does not exist.

        Returns:
            None: This method does not return anything.
        """
        print(f"--- Adding domain {domain} to site {site_name}")
        if site_name not in self.sitename_id_map:
            raise ValueError(f"Site {site_name} does not exist.")

        domainObject = self.find_domain_by_name(domain, site_name=site_name, type="physical")
        if domainObject is None:
            raise ValueError(f"Domain {domain} does not exist.")

        # filter target epg from schema object
        target_site_id = self.sitename_id_map[site_name]
        schema_site_template = list(
            filter(lambda s: s["siteId"] == target_site_id and s["templateName"] == template_name, schema["sites"])
        )
        if len(schema_site_template) == 0:
            raise ValueError(f"Template {template_name} with site {site_name} does not exist.")

        target_anp = list(filter(lambda a: f"/anps/{anp_name}" in a["anpRef"], schema_site_template[0]["anps"]))
        if len(target_anp) == 0:
            raise ValueError(f"ANP {anp_name} does not exist.")

        target_epg = list(filter(lambda e: f"/epgs/{epg_name}" in e["epgRef"], target_anp[0]["epgs"]))
        if len(target_epg) == 0:
            raise ValueError(f"EPG {epg_name} does not exist.")

        filtered_domain = list(
            filter(
                lambda d: ("domainRef" in d and domainObject["uuid"] == d["domainRef"]) or domain in d["dn"],
                target_epg[0]["domainAssociations"],
            )
        )
        if len(filtered_domain) != 0:
            print(f"  |--- Domain {domain} is already exist.")
            return

        payload = {
            "dn": "",
            "domainRef": domainObject["uuid"],
            "domainType": "physicalDomain",
            "deployImmediacy": "lazy",
            "resolutionImmediacy": "immediate",
            "allowMicroSegmentation": False,
        }
        target_epg[0]["domainAssociations"].append(payload)
        print(f"  |--- Done")

    def add_static_port_to_epg(
        self,
        schema: dict,
        template_name: str,
        anp_name: str,
        epg_name: str,
        site_name: str,
        port_configs: list[StaticPortPhy | StaticPortPC | StaticPortVPC],
        strict_check: bool = True,
        pod: str = "pod-1",
    ) -> None:
        """
        Adds a static port to the specified EPG.

        Args:
            schema (dict): The schema object containing the network configuration.
            template_name (str): The name of the template.
            anp_name (str): The name of the ANP (Application Network Profile).
            epg_name (str): The name of the EPG (Endpoint Group).
            site_name (str): The name of the site.
            port_configs (list[StaticPortPhy | StaticPortPC | StaticPortVPC]): A list of port configurations.
            strict_check (bool, optional): Whether to perform strict checking. Defaults to True.
            pod (str, optional): The name of the pod. Defaults to "pod-1".

        Raises:
            ValueError: If the specified site or ANP does not exist.

        Returns:
            None
        """
        print(f"--- Adding Static port to site {site_name}")
        if site_name not in self.sitename_id_map:
            raise ValueError(f"Site {site_name} does not exist.")

        # filter target epg from schema object
        target_site_id = self.sitename_id_map[site_name]
        target_template = list(
            filter(lambda s: s["siteId"] == target_site_id and s["templateName"] == template_name, schema["sites"])
        )

        if len(target_template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        target_anp = list(filter(lambda a: f"/anps/{anp_name}" in a["anpRef"], target_template[0]["anps"]))
        if len(target_anp) == 0:
            raise ValueError(f"ANP {anp_name} does not exist.")

        target_epg = list(filter(lambda e: f"/epgs/{epg_name}" in e["epgRef"], target_anp[0]["epgs"]))
        if len(target_epg) == 0:
            raise ValueError(f"EPG {epg_name} does not exist.")

        for port in port_configs:
            print(f"  |--- Adding port {port.port_name} {f'on {port.nodeId}' if port.port_type =='port' else ''}")
            path = self.__get_port_resource_path(port, site_name, pod, strict_check)
            filter_port = list(filter(lambda p: p["path"] == path, target_epg[0]["staticPorts"]))
            if len(filter_port) != 0:
                print(f"     |--- Port {port.port_name} is already exist.")
                continue

            payload = {
                "type": port.port_type,
                "path": path,
                "portEncapVlan": port.vlan,
                "deploymentImmediacy": "immediate",
                "mode": port.port_mode,
            }
            print(f"     |--- Done")
            target_epg[0]["staticPorts"].append(payload)

    def delete_egp_under_template(self, schema: dict, template_name: str, anp_name: str, epg_name: str) -> None:
        """
        Deletes an EPG under a specific template.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template.
            anp_name (str): The name of the ANP (Application Network Profile).
            epg_name (str): The name of the EPG (Endpoint Group).

        Raises:
            ValueError: If the template or ANP does not exist.

        Returns:
            None
        """
        print(f"--- Deleting EPG under template {template_name}")

        filter_template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(filter_template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        filter_anp = list(filter(lambda anp: anp["name"] == anp_name, filter_template[0]["anps"]))
        if len(filter_anp) == 0:
            raise ValueError(f"ANP {anp_name} does not exist.")

        for i in range(len(filter_anp[0]["epgs"])):
            if filter_anp[0]["epgs"][i]["displayName"] == epg_name:
                del filter_anp[0]["epgs"][i]
                break

    def delete_bridge_domain_under_template(self, schema: dict, template_name: str, bd_name: str) -> None:
        """
        Deletes a bridge domain under a given template.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template.
            bd_name (str): The name of the bridge domain to delete.

        Raises:
            ValueError: If the template does not exist.

        Returns:
            None
        """
        print(f"--- Deleting BD under template {template_name}")

        filter_template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(filter_template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        for i in range(len(filter_template[0]["bds"])):
            if filter_template[0]["bds"][i]["displayName"] == bd_name:
                del filter_template[0]["bds"][i]
                break

    def delete_vrf_under_template(self, schema: dict, template_name: str, vrf_name: str) -> None:
        """
        Deletes a VRF under a specific template.

        Args:
            schema (dict): The schema containing the templates.
            template_name (str): The name of the template.
            vrf_name (str): The name of the VRF to be deleted.

        Raises:
            ValueError: If the template does not exist.

        Returns:
            None
        """
        print(f"--- Deleting VRF under template {template_name}")

        filter_template = list(filter(lambda t: t["name"] == template_name, schema["templates"]))
        if len(filter_template) == 0:
            raise ValueError(f"Template {template_name} does not exist.")

        for i in range(len(filter_template[0]["vrfs"])):
            if filter_template[0]["vrfs"][i]["displayName"] == vrf_name:
                del filter_template[0]["vrfs"][i]
                break

    # Tenant policies template
    def create_tenant_policies_template(
        self, template_name: str, sites: list[str], tenant_name: str
    ) -> TenantPolTemplate:
        print(f"--- Creating Tenant policies template {template_name}")
        for site in sites:
            if site not in self.sitename_id_map:
                raise ValueError(f"site {site} does not exist.")

        tenant = self.find_tenant_by_name(tenant_name)
        if not tenant:
            raise ValueError(f"tenant {tenant_name} does not exist.")

        template = self.find_tenant_policies_template_by_name(template_name)
        if template:
            print(f"  |--- Template already exist")
            return template

        url = f"{self.base_path}{PATH_TEMPLATES}"
        payload = {
            "name": template_name,
            "displayName": template_name,
            "templateType": "tenantPolicy",
            "tenantPolicyTemplate": {
                "template": {"tenantId": tenant["id"]},
                "sites": list(map(lambda s: {"siteId": self.sitename_id_map[s]}, sites)),
            },
        }

        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

        return resp.json()

    # support replace mode
    def add_route_map_policy_under_template(
        self, template_name: str, rnConfig: RouteMapConfig, operation: Literal["add", "merge", "replace"] = "add"
    ) -> None:
        print("--- Adding RouteMap policy")
        if not isinstance(rnConfig, RouteMapConfig):
            raise ValueError("rnConfig must be an object of class RouteMapConfig")

        template = self.find_tenant_policies_template_by_name(template_name)
        if template is None:
            raise ValueError(f"template {template_name} does not exist")

        if "routeMapPolicies" not in template["tenantPolicyTemplate"]["template"]:
            template["tenantPolicyTemplate"]["template"]["routeMapPolicies"] = [
                self.__generate_routeMap_payload(rnConfig)
            ]
        else:
            rm_policies: list = template["tenantPolicyTemplate"]["template"]["routeMapPolicies"]
            filtered_rm = list(filter(lambda rm: rm["name"] == rnConfig.name, rm_policies))
            if len(filtered_rm) > 0:
                print(f"  |--- RouteMap {rnConfig.name} already exist.")
                if operation == "replace":
                    print(f"  |--- replace TRUE : Replacing {rnConfig.name} config")
                    filtered_rm[0] = filtered_rm[0].update(self.__generate_routeMap_payload(rnConfig))
                elif operation == "merge":
                    print(f"  |--- merge TRUE : Merging {rnConfig.name} config")
                    self.__merge_routeMap_payload(filtered_rm[0], rnConfig)
                else:
                    return
            else:
                rm_policies.append(self.__generate_routeMap_payload(rnConfig))

        url = f"{self.base_path}{PATH_TEMPLATES}/{template['templateId']}"
        resp = self.session.put(url, json=template)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

    def add_route_map_prefix_to_policy(
        self, template_name: str, rm_name: str, entryOrder: int, prefix: RouteMapPrefix
    ) -> None:
        print(f"--- Adding prefix to route map {rm_name}")
        template = self.find_tenant_policies_template_by_name(template_name)
        if template is None:
            raise ValueError(f"Tenant policy {template_name} does not exist.")
        rm_pol = list(
            filter(lambda p: p["name"] == rm_name, template["tenantPolicyTemplate"]["template"]["routeMapPolicies"])
        )
        found = False
        for entry in rm_pol[0]["rtMapEntryList"]:
            if entry["rtMapContext"]["order"] != entryOrder:
                continue
            entry["matchRule"][0]["matchPrefixList"].append(asdict(prefix))
            found = True
            break
        if not found:
            raise ValueError(f"Route map entry with order {entryOrder} does not exist.")
        # put update to template
        url = f"{self.base_path}{PATH_TEMPLATES}/{template['templateId']}"
        resp = self.session.put(url, json=template)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

    def add_l3out_intf_routing_policy(
        self,
        template_name: str,
        pol_name: str,
        bfdConfig: BFDPolicyConfig | None = None,
        ospfIntfConfig: OSPFIntfConfig | None = None,
    ) -> None:
        print("--- Adding Interface policy")
        if bfdConfig == None and ospfIntfConfig == None:
            raise ValueError("Either bfdConfig or ospfIntfConfig is required.")

        template = self.find_tenant_policies_template_by_name(template_name)
        if template is None:
            raise ValueError(f"template {template_name} does not exist")

        payload: dict[str, Any] = {"name": pol_name}
        if bfdConfig != None:
            payload["bfdPol"] = asdict(bfdConfig)
        if ospfIntfConfig != None:
            payload["ospfIntfPol"] = {
                "networkType": ospfIntfConfig.networkType,
                "prio": ospfIntfConfig.prio,
                "cost": ospfIntfConfig.cost,
                "ifControl": {
                    "advertiseSubnet": ospfIntfConfig.advertiseSubnet,
                    "bfd": ospfIntfConfig.bfd,
                    "ignoreMtu": ospfIntfConfig.ignoreMtu,
                    "passiveParticipation": ospfIntfConfig.passiveParticipation,
                },
                "helloInterval": ospfIntfConfig.helloInterval,
                "deadInterval": ospfIntfConfig.deadInterval,
                "retransmitInterval": ospfIntfConfig.retransmitInterval,
                "transmitDelay": ospfIntfConfig.transmitDelay,
            }

        if "l3OutIntfPolGroups" not in template["tenantPolicyTemplate"]["template"]:
            template["tenantPolicyTemplate"]["template"]["l3OutIntfPolGroups"] = [payload]
        else:
            policies: list = template["tenantPolicyTemplate"]["template"]["l3OutIntfPolGroups"]
            filtered_pol = list(filter(lambda pol: pol["name"] == pol_name, policies))
            if len(filtered_pol) > 0:
                print(f"  |--- Interface policy {pol_name} already exist.")
                return
            policies.append(payload)

        url = f"{self.base_path}{PATH_TEMPLATES}/{template['templateId']}"
        resp = self.session.put(url, json=template)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

    # L3OUT template
    def create_l3out_template(self, template_name: str, site_name: str, tenant_name: str) -> L3OutTemplate:
        """
        Creates an L3OutTemplate with the given parameters.

        Args:
            template_name (str): The name of the L3OutTemplate.
            site_name (str): The name of the site.
            tenant_name (str): The name of the tenant.

        Returns:
            L3OutTemplate: The created L3OutTemplate.

        Raises:
            ValueError: If the site does not exist or the tenant does not exist.
            Exception: If there is an error during the creation of the L3OutTemplate.
        """
        print(f"--- Creating L3outTemplate {template_name}")
        if site_name not in self.sitename_id_map:
            raise ValueError(f"site {site_name} does not exist.")

        tenant = self.find_tenant_by_name(tenant_name)
        if not tenant:
            raise ValueError(f"tenant {tenant_name} does not exist.")

        l3out = self.find_l3out_template_by_name(template_name)
        if l3out:
            print(f"  |--- Template already exist")
            return l3out

        url = f"{self.base_path}/{PATH_TEMPLATES}"
        payload = {
            "name": template_name,
            "displayName": template_name,
            "templateType": "l3out",
            "l3outTemplate": {
                "tenantId": tenant["id"],
                "siteId": self.sitename_id_map[site_name],
                "l3outs": [],
            },
        }
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

        return resp.json()

    def add_static_route_prefixes_to_l3out(
        self, template_name: str, l3out_name: str, nodeID: str, prefixes: list[L3OutStaticRouteConfig]
    ) -> None:
        """
        Adds static route prefixes to an L3Out.
        parameters:
            template_name: The name of the L3Out template.
            l3out_name: The name of the L3Out.
            nodeID: The node ID.
            prefixes: A list of L3OutStaticRouteConfig objects representing the prefixes to add.
        """
        print(f"--- Adding static route prefixes to L3out {l3out_name}")
        template = self.find_l3out_template_by_name(template_name)
        if template is None:
            raise ValueError(f"template {template_name} does not exist.")

        l3out = list(filter(lambda l: l["name"] == l3out_name, template["l3outTemplate"]["l3outs"]))
        if len(l3out) == 0:
            raise ValueError(f"L3out {l3out_name} does not exist.")

        target_node = list(filter(lambda n: n["nodeID"] == nodeID, l3out[0]["nodes"]))
        if len(target_node) == 0:
            raise ValueError(f"Node {nodeID} does not exist.")

        for prefix in prefixes:
            print(f"  |--- Adding prefix {prefix.prefix}")
            payload = asdict(prefix)
            if "staticRoutes" not in target_node[0]:
                target_node[0]["staticRoutes"] = []
            target_node[0]["staticRoutes"].append(payload)

        url = f"{self.base_path}{PATH_TEMPLATES}/{template['templateId']}"
        resp = self.session.put(url, json=template)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

    # support replace mode
    def add_l3out_under_template(
        self, template_name: str, l3outConfig: L3OutConfig, operation: Literal["replace", "merge"] | None
    ) -> None:
        """
        Adds an L3out to the specified template.

        Args:
            template_name (str): The name of the template.
            l3outConfig (L3OutConfig): An object of class L3OutConfig representing the L3out configuration.
            operation (str | None): The operation mode for adding the L3out. Can be "replace", "merge", or None.
            If None, If the L3out already exists, it will not be added again.

        Raises:
            ValueError: If l3outConfig is not an object of class L3OutConfig or if the template does not exist.

        Returns:
            None: This method does not return anything.
        """
        print(f"--- Adding L3out {l3outConfig.name} to template {template_name}")
        if not isinstance(l3outConfig, L3OutConfig):
            raise ValueError("l3outConfig must be an object of class L3OutConfig")

        template = self.find_l3out_template_by_name(template_name)
        if template is None:
            raise ValueError(f"template {template_name} does not exist.")

        if "l3outs" not in template["l3outTemplate"]:
            template["l3outTemplate"]["l3outs"] = []

        l3outs: list = template["l3outTemplate"]["l3outs"]
        filtered = list(filter(lambda l: l["name"] == l3outConfig.name, l3outs))
        if len(filtered) != 0:
            print(f"  |--- L3out {l3outConfig.name} already exist.")
            if operation == "replace":
                print(f"  |--- replace TRUE : Replacing {l3outConfig.name} config")
                filtered[0] = filtered[0].update(self.__generate_l3out_payload(template, l3outConfig))
            elif operation == "merge":
                print(f"  |--- merge TRUE : Merging {l3outConfig.name} config")
                new_payload = self.__generate_l3out_payload(template, l3outConfig)
                if "interfaces" in filtered[0]:
                    filtered[0]["interfaces"].extend(new_payload["interfaces"])
                if "subInterfaces" in filtered[0]:
                    filtered[0]["subInterfaces"].extend(new_payload["subInterfaces"])
                if "sviInterfaces" in filtered[0]:
                    filtered[0]["sviInterfaces"].extend(new_payload["sviInterfaces"])
            else:
                return
        else:
            payload = self.__generate_l3out_payload(template, l3outConfig)
            l3outs.append(payload)

        url = f"{self.base_path}{PATH_TEMPLATES}/{template['templateId']}"
        resp = self.session.put(url, json=template)
        if resp.status_code >= 400:
            print(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

    # Fabric Template
    def find_vpc_by_name(self, vpc_name: str, site_name: str) -> VPCResourcePolicy | None:
        """
        Finds a VPC by its name within a specific site.

        Args:
            vpc_name (str): The name of the VPC to find.
            site_name (str): The name of the site where the VPC is located.

        Returns:
            VPCResourcePolicy | None: The VPC resource policy if found, None otherwise.

        Raises:
            ValueError: If the specified site does not exist.
        """
        if site_name not in self.sitename_id_map:
            raise ValueError(f"Site {site_name} does not exist.")

        url = f"{self.base_path}{PATH_VPC_SUMMARY_SITE}/{self.sitename_id_map[site_name]}"
        resp = self.session.get(url).json()
        if "vpcs" not in resp["spec"]:
            return None

        filtered = list(filter(lambda v: v["name"] == vpc_name, resp["spec"]["vpcs"]))
        if len(filtered) == 0:
            return None

        return filtered[0]

    def find_pc_by_name(self, pc_name: str, site_name: str) -> PCResourcePolicy | None:
        """
        Finds a PC (Port Channel) by its name within a specific site.

        Args:
            pc_name (str): The name of the PC to search for.
            site_name (str): The name of the site to search within.

        Returns:
            PCResourcePolicy | None: The PC resource policy if found, otherwise None.

        Raises:
            ValueError: If the specified site does not exist.
        """
        if site_name not in self.sitename_id_map:
            raise ValueError(f"Site {site_name} does not exist.")

        url = f"{self.base_path}{PATH_PC_SUMMARY_SITE}/{self.sitename_id_map[site_name]}"
        resp = self.session.get(url).json()
        if "pcs" not in resp["spec"]:
            return None

        filtered = list(filter(lambda v: v["name"] == pc_name, resp["spec"]["pcs"]))
        if len(filtered) == 0:
            return None

        return filtered[0]

    def find_fabric_policy_by_name(self, name: str) -> FabricPolicy | None:
        """
        Finds a fabric policy by its name.

        Args:
            name (str): The name of the fabric policy.

        Returns:
            FabricPolicy | None: The fabric policy object if found, None otherwise.
        """
        url = f"{self.base_path}{PATH_FABRIC_POLICIES_SUM}"
        resp = self.session.get(url).json()
        filtered_resp = list(filter(lambda p: p["templateName"] == name, resp))
        if len(filtered_resp) == 0:
            return None
        else:
            url = f"{self.base_path}{PATH_TEMPLATES}/{filtered_resp[0]['templateId']}"
            return self.session.get(url).json()

    def find_fabric_resource_by_name(self, name: str) -> FabricResourcePolicy | None:
        """
        Finds a fabric resource by its name.

        Args:
            name (str): The name of the fabric resource.

        Returns:
            FabricResourcePolicy | None: The fabric resource policy if found, None otherwise.
        """
        url = f"{self.base_path}{PATH_FABRIC_RESOURCES_SUM}"
        resp = self.session.get(url).json()
        filtered_resp = list(filter(lambda p: p["templateName"] == name, resp))
        if len(filtered_resp) == 0:
            return None
        else:
            url = f"{self.base_path}{PATH_TEMPLATES}/{filtered_resp[0]['templateId']}"
            return self.session.get(url).json()

    def find_phyintf_setting_by_name(self, name: str) -> IntSettingPolicy | None:
        """
        Finds the physical interface setting by name.

        Args:
            name (str): The name of the physical interface setting.

        Returns:
            IntSettingPolicy | None: The physical interface setting if found, None otherwise.
        """
        url = f"{self.base_path}{PATH_PHYINTF_POLICY_GROUP}"
        resp = self.session.get(url)
        if resp.status_code != 200:
            raise Exception(resp.json())

        resp = resp.json()
        for item in resp["items"]:
            if item["spec"]["name"] == name:
                return item["spec"]
        return None

    def find_pc_intf_setting_by_name(self, name: str) -> IntSettingPolicy | None:
        """
        Find the port channel interface setting by name.

        Args:
            name (str): The name of the port channel interface setting.

        Returns:
            IntSettingPolicy | None: The port channel interface setting if found, None otherwise.
        """
        url = f"{self.base_path}{PATH_PORTCHANNEL_POLICY_GROUP}"
        resp = self.session.get(url)
        if resp.status_code != 200:
            raise Exception(resp.json())

        resp = resp.json()
        for item in resp["items"]:
            if item["spec"]["name"] == name:
                return item["spec"]
        return None

    def find_domain_by_name(
        self, domain_name: str, site_name: str | None = None, site_id: str | None = None, type: str = ""
    ) -> dict | None:
        """
        Find a domain object by its name.

        Args:
            domain_name (str): The name of the domain to find.
            site_name (str | None, optional): The name of the site. Defaults to None.
            site_id (str | None, optional): The ID of the site. Defaults to None.
            type (str, optional): The type of the domain, support value ["l3", ""]. Defaults to "".

        Returns:
            dict | None: The domain dictionary if found, None otherwise.

        Raises:
            ValueError: If neither site_name nor site_id is provided.
        """
        if not site_name and not site_id:
            raise ValueError("Either Sitename or SiteID is required.")

        url = f"{self.base_path}{PATH_DOMAINSUM_SITE}/{site_id if site_id is not None else self.sitename_id_map[site_name]}?types={type}"
        resp = self.session.get(url).json()
        domains = resp["spec"]["domains"]
        for domain in domains:
            if domain["name"] == domain_name:
                return domain
        return None

    def create_fabric_policy(self, name: str, site: str) -> FabricPolicy:
        """
        Creates a fabric policy with the given name and site.

        Args:
            name (str): The name of the fabric policy.
            site (str): The name of the site.

        Returns:
            FabricPolicy: The created fabric policy.

        Raises:
            ValueError: If the site does not exist.
            Exception: If there is an error in the API response.

        """
        print(f"--- Creating policy {name} on site {site}")

        if site not in self.sitename_id_map:
            raise ValueError(f"Site {site} does not exist.")

        policy = self.find_fabric_policy_by_name(name)
        if policy:
            print(f"  |--- Policy {name} already exist")
            return policy

        payload = {
            "displayName": name,
            "name": name,
            "templateType": "fabricPolicy",
            "fabricPolicyTemplate": {"sites": [{"siteId": self.sitename_id_map[site]}]},
        }
        url = f"{self.base_path}{PATH_TEMPLATES}"
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

        return resp.json()

    def create_fabric_resource(self, name: str, site: str) -> FabricResourcePolicy:
        """
        Creates a fabric resource policy with the given name and site.

        Args:
            name (str): The name of the fabric resource policy.
            site (str): The name of the site where the fabric resource policy will be created.

        Returns:
            FabricResourcePolicy: The created fabric resource policy.

        Raises:
            ValueError: If the specified site does not exist.
            Exception: If there is an error during the creation of the fabric resource policy.
        """
        print(f"--- Creating resource policy {name} on site {site}")

        if site not in self.sitename_id_map:
            raise ValueError(f"Site {site} does not exist.")

        policy = self.find_fabric_resource_by_name(name)
        if policy:
            print(f"  |--- Policy {name} already exist")
            return policy

        payload = {
            "displayName": name,
            "name": name,
            "templateType": "fabricResource",
            "fabricResourceTemplate": {
                "sites": [{"siteId": self.sitename_id_map[site]}],
                "template": {"interfaceProfiles": []},
            },
        }
        url = f"{self.base_path}{PATH_TEMPLATES}"
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

        return resp.json()

    def add_vlans_to_pool(self, policy_name: str, pool_name: str, vlans: list[int | Tuple[int, int]] = []) -> None:
        """
        Adds a list of VLANs to a VLAN pool in a fabric policy.

        Args:
            policy_name (str): The name of the fabric policy.
            pool_name (str): The name of the VLAN pool.
            vlans (list[int], optional): A list of VLAN IDs to be added to the pool. Defaults to an empty list. If a tuple is provided, it will be treated as a range of VLANs.
            example: [1, 2, 3, (10, 20)] will add VLANs 1, 2, 3, and VLANs 10 to 20 to the pool.

        Raises:
            ValueError: If the fabric policy does not exist.
            Exception: If there is an error in the API response.

        Returns:
            None: This method does not return anything.
        """
        print(f"--- Adding vlans {','.join([str(v) for v in vlans])} to pool {pool_name}")
        policy = self.find_fabric_policy_by_name(policy_name)
        if not policy:
            raise ValueError(f"Policy {policy_name} not exist, Please create it first.")

        payload = {
            "name": pool_name,
            "allocMode": "static",
            "encapBlocks": [
                {
                    "range": {
                        "from": vlan if isinstance(vlan, int) else vlan[0],
                        "to": vlan if isinstance(vlan, int) else vlan[1],
                        "allocMode": "static",
                    }
                }
                for vlan in vlans
            ],
        }
        # vlan pool never initialized before in this template
        if "vlanPools" not in policy["fabricPolicyTemplate"]["template"]:
            policy["fabricPolicyTemplate"]["template"]["vlanPools"] = [payload]
        else:
            target_pool = list(
                filter(lambda pool: pool["name"] == pool_name, policy["fabricPolicyTemplate"]["template"]["vlanPools"])
            )
            if len(target_pool) == 0:
                # create new pool
                policy["fabricPolicyTemplate"]["template"]["vlanPools"].append(payload)
            else:
                # extent the target pool with new vlans
                for vlan in vlans:
                    if isinstance(vlan, tuple):
                        target_pool[0]["encapBlocks"].append(
                            {"range": {"from": vlan[0], "to": vlan[1], "allocMode": "static"}}
                        )
                    elif isinstance(vlan, int):
                        target_pool[0]["encapBlocks"].append(
                            {"range": {"from": vlan, "to": vlan, "allocMode": "static"}}
                        )

        url = f"{self.base_path}{PATH_TEMPLATES}/{policy['templateId']}"
        resp = self.session.put(url, json=policy)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

    def add_port_to_fabric_resource(
        self,
        resource_name: str,
        port_config: PhysicalIntfResource | PortChannelResource | VPCResource,
        intf_policy_name: str,
    ) -> None:
        """
        Adds a port to a fabric resource policy.

        Args:
            resource_name (str): The name of the fabric resource policy.
            port_config (PhysicalIntfResource | PortChannelResource | VPCResource): The port configuration object.
            intf_policy_name (str): The name of the interface policy.

        Raises:
            ValueError: If the fabric resource does not exist or the policy does not exist.
            Exception: If the port_config is not a valid object.

        Returns:
            None: This method does not return anything.
        """
        print(f"--- Adding fabric resource {port_config.name}")
        # find resource template
        resource = self.find_fabric_resource_by_name(resource_name)
        if not resource:
            raise ValueError(f"Fabric resource {resource_name} does not exist.")

        template = resource["fabricResourceTemplate"]["template"]
        if isinstance(port_config, PhysicalIntfResource):
            # find policy ID
            interface_setting = self.find_phyintf_setting_by_name(intf_policy_name)
            if interface_setting is None:
                raise ValueError(f"policy {intf_policy_name} does not exist. Please create it before using.")
            port_config.policy = interface_setting["uuid"]
            # clear nodeID for physical interface
            for desc in port_config.interfaceDescriptions:
                desc.nodeID = ""
            self.__append_fabricRes_intf_object("interfaceProfiles", template, port_config)
        elif isinstance(port_config, PortChannelResource):
            # find policy ID
            interface_setting = self.find_pc_intf_setting_by_name(intf_policy_name)
            if interface_setting is None:
                raise ValueError(f"policy {intf_policy_name} does not exist. Please create it before using.")
            port_config.policy = interface_setting["uuid"]
            self.__append_fabricRes_intf_object("portChannels", template, port_config)
        elif isinstance(port_config, VPCResource):
            # find policy ID
            interface_setting = self.find_pc_intf_setting_by_name(intf_policy_name)
            if interface_setting is None:
                raise Exception(f"policy {intf_policy_name} does not exist. Please create it before using.")
            port_config.policy = interface_setting["uuid"]
            self.__append_fabricRes_intf_object("virtualPortChannels", template, port_config)
        else:
            raise ValueError(
                "port_config is not valid, you must pass an object of types PhysicalIntfResource | PortChannelResource | VPCResource"
            )

        url = f'{self.base_path}{PATH_TEMPLATES}/{resource["templateId"]}'
        resp = self.session.put(url, json=resource)
        if resp.status_code >= 400:
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

    def add_domain_to_fabric_policy(
        self,
        policy_name: str,
        domain_type: Literal["l3Domains", "domains"],
        domain_name: str,
        pool_name: str | None = None,
    ) -> None:
        """
        Adds a domain to a fabric policy.

        Args:
            policy_name (str): The name of the fabric policy.
            domain_type (Literal["l3Domains", "domains"]): The type of the domain. Must be either "l3Domains" or "domains".
            domain_name (str): The name of the domain to be added.
            pool_name (str | None, optional): The name of the VLAN pool. Defaults to None.

        Raises:
            ValueError: If the domain_type is not supported or if the policy does not exist.
            ValueError: If the VLAN pool does not exist in the policy.

        Returns:
            None: This method does not return anything.
        """
        print(f"--- Adding {domain_type} to fabric policy {policy_name}")
        if domain_type not in ["l3Domains", "domains"]:
            raise ValueError("only domain_type of l3Domain or domains is supported")
        policy = self.find_fabric_policy_by_name(policy_name)
        if policy is None:
            raise ValueError(f"Policy {policy_name} not exist, Please create it first.")

        template = policy["fabricPolicyTemplate"]["template"]
        poolname_map = {}  # use for mapping pool_name to uuid
        for pool in [] if "vlanPools" not in template else template["vlanPools"]:
            poolname_map[pool["name"]] = pool["uuid"]

        if pool_name is not None and pool_name not in poolname_map:
            raise ValueError(f"Vlan pool {pool_name} does not exist in the policy {policy_name}.")

        payload = {"name": domain_name}

        if domain_type not in template:
            template[domain_type] = []

        target = list(filter(lambda pol: pol["name"] == domain_name, template[domain_type]))

        if pool_name is not None:
            payload["pool"] = poolname_map[pool_name]
            if len(target) != 0:
                if "pool" not in target[0] or target[0]["pool"] != poolname_map[pool_name]:
                    print(f"  |--- {domain_type} name {domain_name} already exist.")
                    print(f"     |--- changing pool to {pool_name}")
                    target[0]["pool"] = poolname_map[pool_name]
                else:
                    print(f"  |--- {domain_type} name {domain_name} already exist.")
                    return
            else:
                template[domain_type].append(payload)
        else:
            if len(target) != 0:
                print(f"  |--- {domain_type} name {domain_name} already exist.")
                return
            template[domain_type].append(payload)

        url = f"{self.base_path}{PATH_TEMPLATES}/{policy['templateId']}"
        resp = self.session.put(url, json=policy)
        if resp.status_code >= 400:
            print(f"  |--- {resp.json()}")
            raise Exception(resp.json())

        print(f"  |--- Done{f' delay {self.delay} sec' if self.delay is not None else ''}")
        if self.delay is not None:  # delay for a while
            time.sleep(self.delay)

    # task deployment
    def deploy_policies_template(self, template_name: str) -> None:
        print(f"--- Deploying policies template {template_name}")
        url = f"{self.base_path}{PATH_TEMPLATES_SUMMARY}"
        templates = self.session.get(url).json()
        filtered = list(filter(lambda t: t["templateName"] == template_name, templates))
        if len(filtered) == 0:
            raise ValueError(f"template {template_name} does not exist.")

        target_template = filtered[0]
        url = f"{self.base_path}{PATH_TASK}"
        payload = {
            "schemaId": target_template["schemaId"],
            "templateId": target_template["templateId"],
            "timeoutSec": 600,
            "isRedeploy": False,
        }
        self.__send_deploy_task_request(url, payload)

    def deploy_schema_template(self, schema_name: str, template_name: str) -> None:
        print(f"--- Deploying schema {schema_name} template {template_name}")

        schema = self.find_schema_by_name(schema_name)
        if schema is None:
            raise ValueError(f"schema {schema_name} does not exist.")

        url = f"{self.base_path}{PATH_TASK}"
        payload = {"schemaId": schema["id"], "templateName": template_name, "isRedeploy": False}
        self.__send_deploy_task_request(url, payload)

    def undeploy_template_from_sites(self, schema_name: str, template_name: str, site_list: list[str]) -> None:
        print(f"--- Undeploying template {template_name} from site {','.join(site_list)}")

        siteId_list = []
        schema = self.find_schema_by_name(schema_name)
        if schema is None:
            raise ValueError(f"schema {schema_name} does not exist.")

        for site_name in site_list:
            if site_name not in self.sitename_id_map:
                raise ValueError(f"site {site_name} does not exist.")
            siteId_list.append(self.sitename_id_map[site_name])

        url = f"{self.base_path}{PATH_TASK}"
        payload = {
            "schemaId": schema["id"],
            "templateName": template_name,
            "siteGroupId": "default",
            "undeploy": siteId_list,
        }
        self.__send_deploy_task_request(url, payload)
