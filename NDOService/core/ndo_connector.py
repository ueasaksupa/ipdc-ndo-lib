from .path_const import *
from .types import *
from .configurations import *

from pprint import pprint
from dataclasses import asdict
from typing import Literal, Any
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NDOTemplate:
    def __init__(self, host, username, password, port=443) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.domain = "local"
        self.base_path = f"https://{self.host}:{port}"
        self.sitename_id_map = {}
        self.siteid_name_map = {}
        self.session = requests.Session()
        # LOGIN
        self.login()

    # ** INTERNAL ONLY ** UTIL METHODs
    def __get_port_resource_path(self, **kwargs):
        path = ""
        if kwargs["port_type"] == "vpc":
            vpc_resource = self.find_vpc_by_name(kwargs["port_name"], kwargs["site_name"])
            if not vpc_resource:
                raise Exception(
                    f"VPC resource name {kwargs['port_name']} does not exist in the Fabric Resource Policy, Please create it first."
                )
            path = vpc_resource["path"]
        elif kwargs["port_type"] == "port":
            path = f"topology/{kwargs['pod']}/paths-{kwargs['node']}/pathep-[{kwargs['port_name']}]"

        return path

    def __append_fabric_intf_object(
        self, key: str, template: dict, port_config: PhysicalIntfResource | PortChannelResource | VPCResource
    ):
        if not template[key]:
            template[key] = [asdict(port_config)]
            return
        # check whether the object name already exist.
        filter_object = list(filter(lambda i: i["name"] == port_config.name, template[key]))
        if len(filter_object) > 0:
            print(f"   |--- {key} name {port_config.name} already exist.")
            return
        template[key].append(asdict(port_config))

    def __append_l3out_to_external_epg_site(
        self, schema: dict, template_name: str, epg_name: str, l3outList: List[dict]
    ) -> None:
        for l3out in l3outList:
            for site in schema["sites"]:
                if site["siteId"] != self.sitename_id_map[l3out["site"]] or site["templateName"] != template_name:
                    continue

                l3outTemplate = self.find_l3out_template_by_name(l3out["l3OutTemplateName"])
                if l3outTemplate is None:
                    raise ValueError(f"L3out template {l3out['l3OutTemplateName']} does not exist.")
                l3outObject = list(
                    filter(lambda l: l["name"] == l3out["l3outName"], l3outTemplate["l3outTemplate"]["l3outs"])
                )
                if len(l3outObject) == 0:
                    raise Exception(
                        f"L3out {l3out['l3outName']} does not exist in template {l3out['l3OutTemplateName']}"
                    )

                sitePayload = {
                    "externalEpgRef": {"templateName": template_name, "externalEpgName": epg_name},
                    "l3outRef": l3outObject[0]["uuid"],
                }
                site["externalEpgs"].append(sitePayload)

    def __generate_rm_payload(self, rnConfig: RouteMapConfig):
        entryList = []
        for entry in rnConfig.entryList:
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
                entryPayload["setAction"] = [
                    {
                        "setPreference": entry.attributes.setPreference,
                        "setWeight": entry.attributes.setWeight,
                        "setMultiPath": entry.attributes.setMultiPath,
                        "setNextHopPropagate": (
                            True if entry.attributes.setMultiPath else entry.attributes.setNextHopPropagate
                        ),
                        "setAsPath": (
                            [
                                {
                                    "criteria": entry.attributes.setAsPath.criteria,
                                    "pathASNs": [
                                        {"asn": asn, "order": i}
                                        for i, asn in enumerate(entry.attributes.setAsPath.pathASNs, start=1)
                                    ],
                                    "asnCount": entry.attributes.setAsPath.asnCount,
                                }
                            ]
                            if entry.attributes.setAsPath
                            else None
                        ),
                    }
                ]
            entryList.append(entryPayload)
        completed_payload = {"name": rnConfig.name, "description": rnConfig.description, "rtMapEntryList": entryList}
        return completed_payload

    def __generate_l3out_phyintf(self, site_name: str, intfConfig: L3OutInterfaceConfig) -> dict:
        INTF_PAYLOAD = {
            "pathType": intfConfig.portType,
            "addresses": {"primaryV4": intfConfig.primaryV4, "primaryV6": intfConfig.primaryV6},
            "mac": "00:22:BD:F8:19:FF",
            "mtu": "inherit",
            "bgpPeers": list(map(lambda obj: asdict(obj), intfConfig.bgpPeers)),
        }
        if isinstance(intfConfig, L3OutIntPortChannel):
            pcintf = self.find_pc_by_name(intfConfig.portChannelName, site_name)
            if pcintf is None:
                raise Exception(f"PortChannel {intfConfig.portChannelName} does not exist in the fabric resource.")
            INTF_PAYLOAD["pathRef"] = pcintf["uuid"]
        elif isinstance(intfConfig, L3OutIntPhysicalPort):
            INTF_PAYLOAD["podID"] = intfConfig.podID
            INTF_PAYLOAD["nodeID"] = intfConfig.nodeID
            INTF_PAYLOAD["path"] = f"eth{intfConfig.portID}"

        return INTF_PAYLOAD

    def __generate_l3out_subintf(self, site_name: str, intfConfig: L3OutSubInterfaceConfig) -> dict:
        INTF_PAYLOAD = self.__generate_l3out_phyintf(site_name, intfConfig)
        INTF_PAYLOAD["encap"] = {"encapType": intfConfig.encapType, "value": intfConfig.encapVal}
        return INTF_PAYLOAD

    def __generate_l3out_sviintf(self, site_name: str, intfConfig: L3OutSviInterfaceConfig) -> dict:
        INTF_PAYLOAD = self.__generate_l3out_subintf(site_name, intfConfig)
        INTF_PAYLOAD["svi"] = {"encapScope": "local", "autostate": "disabled", "mode": intfConfig.sviMode}
        return INTF_PAYLOAD

    def __generate_l3out_interface_payload(self, template: dict, payload: dict, l3outConfig: L3OutConfig) -> None:
        payload["interfaces"] = []
        payload["subInterfaces"] = []
        payload["sviInterfaces"] = []
        for intf in l3outConfig.interfaces:
            if intf.portType not in ["port", "pc"]:
                raise ValueError(f"portType {intf.portType} is not supported")
            if intf.type == "interfaces":
                payload["interfaces"].append(
                    self.__generate_l3out_phyintf(self.siteid_name_map[template["l3outTemplate"]["siteId"]], intf)
                )
            elif intf.type == "subInterfaces":
                payload["subInterfaces"].append(
                    self.__generate_l3out_subintf(self.siteid_name_map[template["l3outTemplate"]["siteId"]], intf)
                )
            elif intf.type == "sviInterfaces":
                payload["sviInterfaces"].append(
                    self.__generate_l3out_sviintf(self.siteid_name_map[template["l3outTemplate"]["siteId"]], intf)
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
        }
        self.__generate_l3out_interface_payload(template, payload, l3outConfig)
        # pprint(payload)
        return payload

    # UTILS
    def login(self) -> None:
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
        for site in self.get_all_sites():
            self.sitename_id_map[site["name"]] = site["id"]
            self.siteid_name_map[site["id"]] = site["name"]

    def get_all_sites(self) -> Site:
        url = f"{self.base_path}{PATH_SITES}"
        resp = self.session.get(url).json()
        return resp["sites"]

    def find_tenant_by_name(self, tenant_name: str) -> Tenant | None:
        url = f"{self.base_path}{PATH_TENANTS}"
        # Get all
        resp: list = self.session.get(url).json()["tenants"]
        # filter by name
        filter_tenants = list(filter(lambda t: t["name"].upper() == tenant_name.upper(), resp))
        if len(filter_tenants) == 0:
            return None

        return filter_tenants[0]

    def find_schema_by_name(self, schema_name: str) -> Schema | None:
        url = f"{self.base_path}{PATH_SCHEMAS_LIST}"
        # Get all
        resp: list = self.session.get(url).json()["schemas"]
        # filter by name
        filter_schemas = list(
            filter(
                lambda s: s["displayName"].upper() == schema_name.upper(),
                resp,
            )
        )
        if len(filter_schemas) > 0:
            # re-query to get full schema object
            return self.session.get(f"{self.base_path}{PATH_SCHEMAS}/{filter_schemas[0]['id']}").json()

        return None

    def find_l3out_template_by_name(self, l3out_name: str) -> L3OutTemplate | None:
        url = f"{self.base_path}{PATH_L3OUT_TEMPLATE_SUM}"
        # Get all
        resp: list = self.session.get(url).json()
        # filter by name
        filtered = list(filter(lambda t: t["templateName"].upper() == l3out_name.upper(), resp))
        if len(filtered) > 0:
            # re-query to get full object
            return self.session.get(f"{self.base_path}{PATH_TEMPLATES}/{filtered[0]['templateId']}").json()

        return None

    def find_tenant_policies_template_by_name(self, name: str) -> TenantPolTemplate | None:
        url = f"{self.base_path}{PATH_TENANT_POLICIES_TEMPLATE_SUM}"
        # Get all
        resp: list = self.session.get(url).json()
        # filter by name
        filtered = list(filter(lambda t: t["templateName"].upper() == name.upper(), resp))
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

    # Tenant Template
    def save_schema(self, schema: dict) -> Schema:
        print(f"--- Saving schema {schema['displayName']}")
        url = f"{self.base_path}{PATH_SCHEMAS}/{schema['id']}?enableVersionCheck=true"
        resp = self.session.put(url, json=schema)
        if resp.status_code >= 400:
            raise Exception(resp.json())
        return resp.json()

    def create_tenant(self, tenant_name: str, sites: list, tenant_desc: str = "") -> Tenant:
        print(f"--- Creating tenant {tenant_name}")

        tenant = self.find_tenant_by_name(tenant_name)
        if tenant is not None:
            print(f"  |--- Tenant {tenant_name} already exist")
            return tenant

        siteAssociations = []
        for target_site in sites:
            if target_site["name"] not in self.sitename_id_map:
                raise Exception(f"Site {target_site['name']} not exist in the network.")
            site_payload = {
                "siteId": self.sitename_id_map[target_site["name"]],
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
        return self.session.post(url, json=payload).json()

    def create_schema(self, schema_name: str, schema_desc: str = "") -> Schema:
        print(f"--- Creating schema {schema_name}")

        schema = self.find_schema_by_name(schema_name)
        if schema is not None:
            print(f"  |--- Schema {schema_name} already exist")
            return schema

        url = f"{self.base_path}{PATH_SCHEMAS}"
        payload = {"displayName": schema_name, "description": schema_desc}
        return self.session.post(url, json=payload).json()

    def create_template(self, schema: dict, template_name: str, tenant_id: str) -> Template:
        print(f"--- Creating template {template_name}")

        if "templates" not in schema:
            schema["templates"] = []
        filter_template = list(
            filter(
                lambda d: d["name"].upper() == template_name.upper(),
                schema["templates"],
            )
        )

        if len(filter_template) != 0:
            print(f"  |--- template {template_name} is already exists")
            return filter_template[0]

        payload = {
            "name": template_name,
            "tenantId": tenant_id,
            "displayName": template_name,
            "templateType": "stretched-template",
        }

        schema["templates"].append(payload)
        return schema["templates"][-1]

    def add_site_to_template(self, schema: dict, template_name: str, target_sites: list) -> None:
        for target_site in target_sites:
            print(f"--- Adding site {target_site['name']} to template {template_name}")
            try:
                target_site_id = self.sitename_id_map[target_site["name"]]
                filter_site = list(
                    filter(
                        lambda el: el["siteId"] == target_site_id
                        and el["templateName"].upper() == template_name.upper(),
                        schema["sites"],
                    )
                )

                if len(filter_site) != 0:
                    print(f"  |--- Site {target_site['name']} already exist in the template {template_name}")
                    continue

                payload = {
                    "name": target_site["name"],
                    "siteId": target_site_id,
                    "templateName": template_name,
                }
                schema["sites"].append(payload)
            except Exception:
                raise Exception(f"Site {target_site['name']} does not exist")

    def create_filter_under_template(self, schema: dict, template_name: str, filter_name: str) -> Filter:
        print(f"--- Creating filter {filter_name}")

        filter_template = list(
            filter(
                lambda t: t["name"].upper() == template_name.upper(),
                schema["templates"],
            )
        )
        if len(filter_template) == 0:
            raise Exception(f"Template {template_name} does not exist.")

        filter_object = list(filter(lambda d: d["name"].upper() == filter_name.upper(), filter_template[0]["filters"]))
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
        return filter_template[0]["filters"][-1]

    def create_contract_under_template(
        self, schema: dict, template_name: str, contract_name: str, filter_name: str
    ) -> Contract:
        print(f"--- Creating contract {contract_name}")

        filter_template = list(
            filter(
                lambda t: t["name"].upper() == template_name.upper(),
                schema["templates"],
            )
        )
        if len(filter_template) == 0:
            raise Exception(f"Template {template_name} does not exist.")

        contract = list(filter(lambda d: d["name"].upper() == contract_name.upper(), filter_template[0]["contracts"]))
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
        return filter_template[0]["contracts"][-1]

    def create_vrf_under_template(
        self, schema: dict, template_name: str, vrf_name: str, contract_name: str, vrf_config: VrfConfig | None = None
    ) -> Vrf:
        print(f"--- Creating VRF {vrf_name}")
        if vrf_config is None:
            vrf_config = VrfConfig()
        elif not isinstance(vrf_config, VrfConfig):
            raise Exception("vrf_config must be object of VrfConfig")

        template = list(
            filter(
                lambda t: t["name"].upper() == template_name.upper(),
                schema["templates"],
            )
        )
        if len(template) == 0:
            raise Exception(f"Template {template_name} does not exist.")

        filter_vrf = list(filter(lambda d: d["name"].upper() == vrf_name.upper(), template[0]["vrfs"]))
        if len(filter_vrf) != 0:
            print(f"  |--- VRF {vrf_name} is already exist")
            return filter_vrf[0]

        payload = {
            "displayName": vrf_name,
            "name": vrf_name,
            "vzAnyConsumerContracts": [{"contractRef": {"contractName": contract_name}}],
            "vzAnyProviderContracts": [{"contractRef": {"contractName": contract_name}}],
        }
        payload.update(asdict(vrf_config))

        template[0]["vrfs"].append(payload)
        return template[0]["vrfs"][-1]

    def create_bridge_domain_under_template(
        self,
        schema: dict,
        template_name_vrf: str,
        template_name_bd: str,
        linked_vrf_name: str,
        bd_name: str,
        bd_config: BridgeDomainConfig | None = None,
    ) -> BD:
        print(f"--- Creating BD under template {template_name_bd}")
        if bd_config is None:
            bd_config = BridgeDomainConfig()
        elif not isinstance(bd_config, BridgeDomainConfig):
            raise Exception("bd_config must be object of BridgeDomainConfig")

        filter_template = list(
            filter(
                lambda t: t["name"].upper() == template_name_bd.upper(),
                schema["templates"],
            )
        )
        if len(filter_template) == 0:
            raise Exception(f"Template {template_name_bd} does not exist.")

        filter_bd = list(
            filter(
                lambda d: d["name"].upper() == bd_name.upper(),
                filter_template[0]["bds"],
            )
        )
        if len(filter_bd) != 0:
            print(f"   |--- BD {bd_name} is already exist in template {template_name_bd}")
            return filter_bd[0]

        # "vrfRef": f"/schemas/{schema['id']}/templates/{template_name_vrf}/vrfs/{linked_vrf_name}",
        payload = {
            "name": bd_name,
            "displayName": bd_name,
            "vrfRef": {"schemaID": schema["id"], "templateName": template_name_vrf, "vrfName": linked_vrf_name},
        }
        payload.update(asdict(bd_config))

        filter_template[0]["bds"].append(payload)
        return filter_template[0]["bds"][-1]

    def create_anp_under_template(self, schema: dict, template_name: str, anp_name: str, anp_desc: str = "") -> ANP:
        print(f"--- Creating ANP under template {template_name}")
        filter_template = list(filter(lambda t: t["name"].upper() == template_name.upper(), schema["templates"]))
        if len(filter_template) == 0:
            raise Exception(f"Template {template_name} does not exist.")

        filter_anp = list(filter(lambda anp: anp["name"].upper() == anp_name.upper(), filter_template[0]["anps"]))
        if len(filter_anp) != 0:
            print(f"   |--- ANP {anp_name} is already exist in template {template_name}")
            return filter_anp[0]

        payload = {
            "name": anp_name,
            "displayName": anp_name,
            "description": anp_desc,
            "epgs": [],
        }
        filter_template[0]["anps"].append(payload)
        return filter_template[0]["anps"][-1]

    def create_epg_under_template(
        self,
        schema: dict,
        anp: dict,
        linked_template: str,
        linked_bd: str,
        epg_name: str,
        epg_desc: str = "",
    ) -> EPG:
        print(f"--- Creating EPG under ANP {anp['name']}")
        filter_epg = list(filter(lambda epg: epg["name"].upper() == epg_name.upper(), anp["epgs"]))

        if len(filter_epg) != 0:
            print(f"   |--- EPG {epg_name} is already exist in ANP {anp['name']}")
            return filter_epg[0]

        # TODO
        # Parameterized flags
        payload = {
            "name": epg_name,
            "displayName": epg_name,
            "description": epg_desc,
            "bdRef": {"schemaID": schema["id"], "templateName": linked_template, "bdName": linked_bd},
            "contractRelationships": [],
            "subnets": [],
            "uSegEpg": False,
            "uSegAttrs": [],
            "intraEpg": "unenforced",
            "prio": "unspecified",
            "proxyArp": False,
            "mCastSource": False,
            "preferredGroup": False,
            "selectors": [],
            "epgType": "application",
        }
        anp["epgs"].append(payload)
        return anp["epgs"][-1]

    def create_ext_epg_under_template(
        self,
        schema: dict,
        template_name: str,
        epg_name: str,
        vrf_name: str,
        vrf_template: str,
        l3outList: List[dict],
        epg_desc: str = "",
    ) -> ExtEPG:
        print(f"--- Creating External EPG under template {template_name}")
        filter_template = list(filter(lambda t: t["name"].upper() == template_name.upper(), schema["templates"]))
        if len(filter_template) == 0:
            raise Exception(f"Template {template_name} does not exist.")

        filter_eepg = list(
            filter(lambda anp: anp["name"].upper() == epg_name.upper(), filter_template[0]["externalEpgs"])
        )
        if len(filter_eepg) != 0:
            print(f"   |--- External EPG {epg_name} is already exist in template {template_name}")
            return filter_eepg[0]

        payload = {
            "name": epg_name,
            "displayName": epg_name,
            "extEpgType": "on-premise",
            "vrfRef": {"vrfName": vrf_name, "templateName": vrf_template},
            "description": epg_desc,
        }
        # Add External EPG to template
        filter_template[0]["externalEpgs"].append(payload)
        # Add L3Out to site
        self.__append_l3out_to_external_epg_site(schema, template_name, epg_name, l3outList)

        return filter_template[0]["externalEpgs"][-1]

    def add_phy_domain_to_epg(
        self,
        schema: dict,
        template_name: str,
        anp_name: str,
        epg_name: str,
        domain: str,
        site_name: str,
    ) -> None:
        print(f"--- Adding domain {domain} to site {site_name}")
        if site_name not in self.sitename_id_map:
            raise Exception(f"Site {site_name} does not exist.")

        # filter target epg from schema object
        target_site_id = self.sitename_id_map[site_name]
        target_template = list(
            filter(lambda s: s["siteId"] == target_site_id and s["templateName"] == template_name, schema["sites"])
        )

        target_anp = list(filter(lambda a: f"/anps/{anp_name}" in a["anpRef"], target_template[0]["anps"]))
        if len(target_anp) == 0:
            raise Exception(f"ANP {anp_name} does not exist.")

        target_epg = list(filter(lambda e: f"/epgs/{epg_name}" in e["epgRef"], target_anp[0]["epgs"]))
        if len(target_epg) == 0:
            raise Exception(f"EPG {epg_name} does not exist.")

        payload = {
            "dn": f"uni/phys-{domain}",
            "domainType": "physicalDomain",
            "deployImmediacy": "lazy",
            "resolutionImmediacy": "immediate",
            "allowMicroSegmentation": False,
        }
        filtered_domain = list(filter(lambda d: domain in d["dn"], target_epg[0]["domainAssociations"]))
        if len(filtered_domain) != 0:
            print(f"   |--- Domain {domain} is already exist.")
            return

        target_epg[0]["domainAssociations"].append(payload)

    def add_static_port_to_epg(
        self,
        schema: dict,
        template_name: str,
        anp_name: str,
        epg_name: str,
        site_name: str,
        port_configurations: list[dict],
        pod: str = "pod-1",
    ) -> None:
        print(f"--- Adding Static port to site {site_name}")
        if site_name not in self.sitename_id_map:
            raise Exception(f"Site {site_name} does not exist.")

        # filter target epg from schema object
        target_site_id = self.sitename_id_map[site_name]
        target_template = list(
            filter(lambda s: s["siteId"] == target_site_id and s["templateName"] == template_name, schema["sites"])
        )

        target_anp = list(filter(lambda a: f"/anps/{anp_name}" in a["anpRef"], target_template[0]["anps"]))
        if len(target_anp) == 0:
            raise Exception(f"ANP {anp_name} does not exist.")

        target_epg = list(filter(lambda e: f"/epgs/{epg_name}" in e["epgRef"], target_anp[0]["epgs"]))
        if len(target_epg) == 0:
            raise Exception(f"EPG {epg_name} does not exist.")

        for conf in port_configurations:
            print(f"   |--- Adding port {conf['node']}/{conf['port_name']}/")

            path = self.__get_port_resource_path(**conf, site_name=site_name, pod=pod)
            filter_port = list(filter(lambda p: p["path"].upper() == path.upper(), target_epg[0]["staticPorts"]))
            if len(filter_port) != 0:
                print(f"   |--- Port {conf['port_name']} on {conf['node']} is already exist.")
                continue

            payload = {
                "type": conf["port_type"],
                "path": path,
                "portEncapVlan": conf["vlan"],
                "deploymentImmediacy": "immediate",
                "mode": conf["port_mode"],
            }
            target_epg[0]["staticPorts"].append(payload)

    # Tenant policies template
    def create_tenant_policies_template(
        self, template_name: str, sites: list[str], tenant_name: str
    ) -> TenantPolTemplate:
        print(f"--- Creating Tenant policies template {template_name}")
        for site in sites:
            if site not in self.sitename_id_map:
                raise Exception(f"site {site} does not exist.")

        tenant = self.find_tenant_by_name(tenant_name)
        if not tenant:
            raise Exception(f"tenant {tenant_name} does not exist.")

        template = self.find_tenant_policies_template_by_name(template_name)
        if template:
            print(f"   |--- Template already exist")
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
        return resp.json()

    def add_route_map_policy_under_template(self, template_name: str, rnConfig: RouteMapConfig) -> None:
        print("--- Adding RouteMap policy")
        if not isinstance(rnConfig, RouteMapConfig):
            raise ValueError("rnConfig must be an object of class RouteMapConfig")

        template = self.find_tenant_policies_template_by_name(template_name)
        if template is None:
            raise Exception(f"template {template_name} does not exist")

        if "routeMapPolicies" not in template["tenantPolicyTemplate"]["template"]:
            template["tenantPolicyTemplate"]["template"]["routeMapPolicies"] = [self.__generate_rm_payload(rnConfig)]
        else:
            rm_policies: list = template["tenantPolicyTemplate"]["template"]["routeMapPolicies"]
            filtered_rm = list(filter(lambda rm: rm["name"] == rnConfig.name, rm_policies))
            if len(filtered_rm) > 0:
                print(f"   |--- RouteMap {rnConfig.name} already exist.")
                return
            rm_policies.append(self.__generate_rm_payload(rnConfig))

        url = f"{self.base_path}{PATH_TEMPLATES}/{template['templateId']}"
        resp = self.session.put(url, json=template)
        if resp.status_code >= 400:
            raise Exception(resp.json())

    def add_l3out_intf_routing_policy(
        self,
        template_name: str,
        pol_name: str,
        bfdConfig: BFDPolicyConfig | None = None,
        ospfIntfConfig: OSPFIntfConfig | None = None,
    ) -> None:
        print("--- Adding Interface policy")
        if bfdConfig == None and ospfIntfConfig == None:
            raise Exception("Either bfdConfig or ospfIntfConfig is required.")

        template = self.find_tenant_policies_template_by_name(template_name)
        if template is None:
            raise Exception(f"template {template_name} does not exist")

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
                print(f"   |--- Interface policy {pol_name} already exist.")
                return
            policies.append(payload)

        url = f"{self.base_path}{PATH_TEMPLATES}/{template['templateId']}"
        resp = self.session.put(url, json=template)
        if resp.status_code >= 400:
            raise Exception(resp.json())

    # L3OUT template
    def create_l3out_template(self, template_name: str, site_name: str, tenant_name: str) -> L3OutTemplate:
        print(f"--- Creating L3outTemplate {template_name}")
        if site_name not in self.sitename_id_map:
            raise Exception(f"site {site_name} does not exist.")

        tenant = self.find_tenant_by_name(tenant_name)
        if not tenant:
            raise Exception(f"tenant {tenant_name} does not exist.")

        l3out = self.find_l3out_template_by_name(template_name)
        if l3out:
            print(f"   |--- Template already exist")
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
        return resp.json()

    def add_l3out_under_template(self, template_name: str, l3outConfig: L3OutConfig) -> None:
        print(f"--- Adding L3out {l3outConfig.name} to template {template_name}")
        if not isinstance(l3outConfig, L3OutConfig):
            raise ValueError("l3outConfig must be an object of class L3OutConfig")

        template = self.find_l3out_template_by_name(template_name)

        if not template:
            raise Exception(f"template {template_name} does not exist.")
        if "l3outs" not in template["l3outTemplate"]:
            template["l3outTemplate"]["l3outs"] = []

        l3outs: list = template["l3outTemplate"]["l3outs"]
        filtered = list(filter(lambda l: l["name"] == l3outConfig.name, l3outs))
        if len(filtered) != 0:
            print(f"   |--- L3out {l3outConfig.name} already exist.")
            return

        payload = self.__generate_l3out_payload(template, l3outConfig)
        l3outs.append(payload)
        url = f"{self.base_path}{PATH_TEMPLATES}/{template['templateId']}"
        resp = self.session.put(url, json=template)
        if resp.status_code >= 400:
            print(resp.json())

    # Fabric Template
    def find_vpc_by_name(self, vpc_name: str, site_name: str) -> VPCResourcePolicy | None:
        if site_name not in self.sitename_id_map:
            raise Exception(f"Site {site_name} does not exist.")

        url = f"{self.base_path}{PATH_VPC_SUMMARY_SITE}/{self.sitename_id_map[site_name]}"
        resp = self.session.get(url).json()
        if "vpcs" not in resp["spec"]:
            return None

        filtered = list(filter(lambda v: v["name"] == vpc_name, resp["spec"]["vpcs"]))
        if len(filtered) == 0:
            return None

        return filtered[0]

    def find_pc_by_name(self, pc_name: str, site_name: str) -> VPCResourcePolicy | None:
        if site_name not in self.sitename_id_map:
            raise Exception(f"Site {site_name} does not exist.")

        url = f"{self.base_path}{PATH_PC_SUMMARY_SITE}/{self.sitename_id_map[site_name]}"
        resp = self.session.get(url).json()
        if "pcs" not in resp["spec"]:
            return None

        filtered = list(filter(lambda v: v["name"] == pc_name, resp["spec"]["pcs"]))
        if len(filtered) == 0:
            return None

        return filtered[0]

    def find_fabric_policy_by_name(self, name: str) -> FabricPolicy | None:
        url = f"{self.base_path}{PATH_FABRIC_POLICIES_SUM}"
        resp = self.session.get(url).json()
        filtered_resp = list(filter(lambda p: p["templateName"] == name, resp))
        if len(filtered_resp) == 0:
            return None
        else:
            url = f"{self.base_path}{PATH_TEMPLATES}/{filtered_resp[0]['templateId']}"
            return self.session.get(url).json()

    def find_fabric_resource_by_name(self, name: str) -> FabricPolicy | None:
        url = f"{self.base_path}{PATH_FABRIC_RESOURCES_SUM}"
        resp = self.session.get(url).json()
        filtered_resp = list(filter(lambda p: p["templateName"] == name, resp))
        if len(filtered_resp) == 0:
            return None
        else:
            url = f"{self.base_path}{PATH_TEMPLATES}/{filtered_resp[0]['templateId']}"
            return self.session.get(url).json()

    def find_phyintf_setting_id_by_name(self, name: str) -> IntSettingPolicy | None:
        url = f"{self.base_path}{PATH_PHYINTF_POLICY_GROUP}"
        resp = self.session.get(url)
        if resp.status_code != 200:
            raise Exception(resp.json())

        resp = resp.json()
        for item in resp["items"]:
            if item["spec"]["name"] == name:
                return item["spec"]
        return None

    def find_pc_intf_setting_id_by_name(self, name: str) -> IntSettingPolicy | None:
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
        if not site_name and not site_id:
            raise Exception("Either Sitename or SiteID is required.")

        url = f"{self.base_path}{PATH_DOMAINSUM_SITE}/{site_id if site_id is not None else self.sitename_id_map[site_name]}?types={type}"
        resp = self.session.get(url).json()
        domains = resp["spec"]["domains"]
        for domain in domains:
            if domain["name"] == domain_name:
                return domain
        return None

    def create_fabric_policy(self, name: str, site: str) -> FabricPolicy:
        print(f"--- Creating policy {name} on site {site}")

        if site not in self.sitename_id_map:
            raise Exception(f"Site {site} does not exist.")

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
        return resp.json()

    def create_fabric_resource(self, name: str, site: str) -> FabricPolicy:
        print(f"--- Creating resource policy {name} on site {site}")

        if site not in self.sitename_id_map:
            raise Exception(f"Site {site} does not exist.")

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
        return resp.json()

    def add_vlans_to_pool(self, policy_name: str, pool_name: str, vlans: list[int] = []) -> None:
        print(f"--- Adding vlans {','.join([str(v) for v in vlans])} to pool {pool_name}")
        policy = self.find_fabric_policy_by_name(policy_name)
        if not policy:
            raise Exception(f"Policy {policy_name} not exist, Please create it first.")

        payload = {
            "name": pool_name,
            "allocMode": "static",
            "encapBlocks": [{"range": {"from": vlan, "to": vlan, "allocMode": "static"}} for vlan in vlans],
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
                    target_pool[0]["encapBlocks"].append({"range": {"from": vlan, "to": vlan, "allocMode": "static"}})

        url = f"{self.base_path}{PATH_TEMPLATES}/{policy['templateId']}"
        resp = self.session.put(url, json=policy)
        if resp.status_code >= 400:
            print(f"   |--- {resp.json()}")
            raise Exception(resp.json())

    def add_port_to_fabric_resource(
        self,
        resource_name: str,
        port_config: PhysicalIntfResource | PortChannelResource | VPCResource,
        intf_policy_name: str,
    ) -> None:
        print(f"--- Adding fabric resource {port_config.name}")
        # find resource template
        resource = self.find_fabric_resource_by_name(resource_name)
        if not resource:
            raise Exception(f"Fabric resource {resource_name} does not exist.")

        template = resource["fabricResourceTemplate"]["template"]
        if isinstance(port_config, PhysicalIntfResource):
            # find policy ID
            policy_id = self.find_phyintf_setting_id_by_name(intf_policy_name)
            if policy_id is None:
                raise Exception(f"policy {intf_policy_name} does not exist. Please create it before using.")
            port_config.policy = policy_id["uuid"]
            self.__append_fabric_intf_object("interfaceProfiles", template, port_config)
        elif isinstance(port_config, PortChannelResource):
            # find policy ID
            policy_id = self.find_pc_intf_setting_id_by_name(intf_policy_name)
            if policy_id is None:
                raise Exception(f"policy {intf_policy_name} does not exist. Please create it before using.")
            port_config.policy = policy_id["uuid"]
            self.__append_fabric_intf_object("portChannels", template, port_config)
        elif isinstance(port_config, VPCResource):
            # find policy ID
            policy_id = self.find_pc_intf_setting_id_by_name(intf_policy_name)
            if policy_id is None:
                raise Exception(f"policy {intf_policy_name} does not exist. Please create it before using.")
            port_config.policy = policy_id["uuid"]
            self.__append_fabric_intf_object("virtualPortChannels", template, port_config)
        else:
            raise Exception(
                "port_config is not valid, you must pass an object of types PhysicalIntfResource | PortChannelResource | VPCResource"
            )

        url = f'{self.base_path}{PATH_TEMPLATES}/{resource["templateId"]}'
        resp = self.session.put(url, json=resource)
        if resp.status_code >= 400:
            raise Exception(resp.json())

    def add_domain_to_fabric_policy(
        self,
        policy_name: str,
        domain_type: Literal["l3Domains", "domains"],
        domain_name: str,
        pool_name: str | None = None,
    ) -> None:
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
        if pool_name is not None:
            payload["pool"] = poolname_map[pool_name]

        if domain_type not in template:
            template[domain_type] = [payload]
        else:
            target = list(filter(lambda pol: pol["name"] == domain_name, template[domain_type]))
            if len(target) != 0:
                print(f"   |--- {domain_type} name {domain_name} already exist.")
                return
            template[domain_type].append(payload)

        url = f"{self.base_path}{PATH_TEMPLATES}/{policy['templateId']}"
        resp = self.session.put(url, json=policy)
        if resp.status_code >= 400:
            print(f"   |--- {resp.json()}")
            raise Exception(resp.json())