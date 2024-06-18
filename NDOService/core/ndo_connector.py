from .path_const import *
from .types import *
from .configurations import *

from pprint import pprint
from dataclasses import asdict
from typing import Literal
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
        self.session = None
        self.sitename_id_map = {}
        self.schema = None
        # LOGIN
        self.login()

    # INTERNAL UTIL METHODs
    def __get_port_resource_path(self, **kwargs):
        path = ""
        if kwargs["port_type"] == "vpc":
            vpc_resource = self.find_vpc_by_site(kwargs["port_name"], kwargs["site_name"])
            if not vpc_resource:
                raise Exception(
                    f"VPC resource name {kwargs['port_name']} does not exist in the Fabric Resource Policy, Please create it first."
                )
            path = vpc_resource["path"]
        elif kwargs["port_type"] == "port":
            path = f"topology/{kwargs['pod']}/paths-{kwargs['node']}/pathep-[{kwargs['port_name']}]"

        return path

    def __append_fabric_intf_object(
        self,
        key: str,
        template: dict,
        port_config: PhysicalIntfResource | PortChannelResource | VPCResource,
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
            entryList.append(
                {
                    "rtMapContext": {"order": entry.order, "name": entry.name, "action": entry.action},
                    "matchRule": [{"matchPrefixList": prefixes}],
                }
            )
        completed_payload = {"name": rnConfig.name, "description": rnConfig.description, "rtMapEntryList": entryList}
        return completed_payload

    # UTILS
    def login(self) -> None:
        if not self.session:
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
        if len(filter_tenants) > 0:
            return filter_tenants[0]

        return None

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
            resp = self.session.get(f"{self.base_path}{PATH_SCHEMAS}/{filter_schemas[0]['id']}").json()
            return resp

        return None

    def find_vpc_by_site(self, vpc_name: str, site_name: str) -> VPCResourcePolicy | None:
        if site_name not in self.sitename_id_map:
            raise Exception(f"Site {site_name} does not exist.")

        url = f"{self.base_path}{PATH_VPC_SUMMARY_SITE}/{self.sitename_id_map[site_name]}"
        resp = self.session.get(url).json()
        if "vpcs" not in resp["spec"]:
            return None

        filtered_vpc = list(filter(lambda v: v["name"] == vpc_name, resp["spec"]["vpcs"]))
        if len(filtered_vpc) == 0:
            return None

        return filtered_vpc[0]

    def find_l3out_template_by_name(self, l3out_name: str) -> L3OutTemplate | None:
        url = f"{self.base_path}{PATH_L3OUT_TEMPLATE_SUM}"
        # Get all
        resp: list = self.session.get(url).json()
        # filter by name
        filtered = list(filter(lambda t: t["templateName"].upper() == l3out_name.upper(), resp))
        if len(filtered) > 0:
            # re-query to get full object
            resp = self.session.get(f"{self.base_path}{PATH_TEMPLATES}/{filtered[0]['templateId']}").json()
            return resp

        return None

    def find_tenant_policies_template_by_name(self, name: str) -> TenantPoliciesTemplate | None:
        url = f"{self.base_path}{PATH_TENANT_POLICIES_TEMPLATE_SUM}"
        # Get all
        resp: list = self.session.get(url).json()
        # filter by name
        filtered = list(filter(lambda t: t["templateName"].upper() == name.upper(), resp))
        if len(filtered) > 0:
            # re-query to get full object
            resp = self.session.get(f"{self.base_path}{PATH_TEMPLATES}/{filtered[0]['templateId']}").json()
            return resp

        return None

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
        if tenant:
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
        if schema:
            print(f"  |--- Schema {schema_name} already exist")
            return schema

        url = f"{self.base_path}{PATH_SCHEMAS}"
        payload = {"displayName": schema_name, "description": schema_desc}
        return self.session.post(url, json=payload).json()

    def create_template(self, schema: dict, template_name: str, tenant_id: str) -> Template:
        print(f"--- Creating template {template_name}")

        if not schema["templates"]:
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
        self, schema: dict, template_name: str, vrf_name: str, contract_name: str, vrf_config: VrfParams = None
    ) -> Vrf:
        print(f"--- Creating VRF {vrf_name}")
        if vrf_config == None:
            vrf_config = VrfParams()
        elif not isinstance(vrf_config, VrfParams):
            raise Exception("vrf_config must be object of VrfParams")

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
        bd_config: BridgeDomainParams = None,
    ) -> BD:
        print(f"--- Creating BD under template {template_name_bd}")
        if bd_config == None:
            bd_config = BridgeDomainParams()
        elif not isinstance(bd_config, BridgeDomainParams):
            raise Exception("bd_config must be object of BridgeDomainParams")

        filter_template = list(
            filter(
                lambda t: t["name"].upper() == template_name_bd.upper(),
                schema["templates"],
            )
        )
        if len(filter_template) == 0:
            raise Exception(f"Template {template_name_bd} does not exist.")

        template_index = schema["templates"].index(filter_template[0])
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
    ) -> dict:
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
    ) -> TenantPoliciesTemplate:
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

    def add_route_map_policy(self, template_name: str, rnConfig: RouteMapConfig) -> None:
        print("--- Adding RouteMap policy")
        template = self.find_tenant_policies_template_by_name(template_name)
        if not template_name:
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
        bfdConfig: BFDPolicyConfig = None,
        ospfIntfConfig: OSPFIntfConfig = None,
    ) -> None:
        print("--- Adding Interface policy")
        if bfdConfig == None and ospfIntfConfig == None:
            raise Exception("Either bfdConfig or ospfIntfConfig is required.")

        template = self.find_tenant_policies_template_by_name(template_name)
        if not template_name:
            raise Exception(f"template {template_name} does not exist")

        payload = {"name": pol_name}
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

    def add_l3out_under_template(self, l3out_name: str):
        # TODO
        pass

    # Fabric Template
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

    def find_phyintf_setting_id_by_name(self, name: str) -> str | None:
        url = f"{self.base_path}{PATH_PHYINTF_POLICY_GROUP}"
        resp = self.session.get(url)
        if resp.status_code != 200:
            raise Exception(resp.json())

        resp = resp.json()
        for item in resp["items"]:
            if item["spec"]["name"] == name:
                return item["spec"]["uuid"]
        return None

    def find_pc_intf_setting_id_by_name(self, name: str) -> str | None:
        url = f"{self.base_path}{PATH_PORTCHANNEL_POLICY_GROUP}"
        resp = self.session.get(url)
        if resp.status_code != 200:
            raise Exception(resp.json())

        resp = resp.json()
        for item in resp["items"]:
            if item["spec"]["name"] == name:
                return item["spec"]["uuid"]
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
        return self.session.post(url, json=payload)

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
        return self.session.post(url, json=payload)

    def add_vlans_to_pool(self, policy_name: str, pool_name: str, vlans: list[int] = []) -> None:
        print(f"--- Adding vlans {','.join([str(v) for v in vlans])} to pool {pool_name}")
        policy = self.find_fabric_policy_by_name(policy_name)
        if not policy:
            raise Exception(f"Policy {pool_name} not exist, Please create it first.")

        payload = {
            "name": pool_name,
            "allocMode": "static",
            "encapBlocks": [{"range": {"from": vlan, "to": vlan, "allocMode": "static"}} for vlan in vlans],
        }
        # vlan pool never initialized before in this template
        if "vlanPools" not in policy["fabricPolicyTemplate"]["template"]:
            policy["fabricPolicyTemplate"]["template"] = {"vlanPools": [payload]}
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
            print(f"   |--- {resp.json()['info']}")
            raise Exception(resp.json())

    def add_port_to_fabric_resource(
        self,
        resource_name: str,
        port_config: PhysicalIntfResource | PortChannelResource | VPCResource,
        intf_policy_name: str,
    ):
        print(f"--- Adding fabric resource {port_config.name}")
        # find resource template
        resource = self.find_fabric_resource_by_name(resource_name)
        if not resource:
            raise Exception(f"Fabric resource {resource_name} does not exist.")

        template = resource["fabricResourceTemplate"]["template"]
        if isinstance(port_config, PhysicalIntfResource):
            # find policy ID
            policy_id = self.find_phyintf_setting_id_by_name(intf_policy_name)
            port_config.policy = policy_id
            if not policy_id:
                raise Exception(f"policy {intf_policy_name} does not exist. Please create it before using.")
            self.__append_fabric_intf_object("interfaceProfiles", template, port_config)
        elif isinstance(port_config, PortChannelResource):
            # find policy ID
            policy_id = self.find_pc_intf_setting_id_by_name(intf_policy_name)
            port_config.policy = policy_id
            if not policy_id:
                raise Exception(f"policy {intf_policy_name} does not exist. Please create it before using.")
            self.__append_fabric_intf_object("portChannels", template, port_config)
        elif isinstance(port_config, VPCResource):
            # find policy ID
            policy_id = self.find_pc_intf_setting_id_by_name(intf_policy_name)
            port_config.policy = policy_id
            if not policy_id:
                raise Exception(f"policy {intf_policy_name} does not exist. Please create it before using.")
            self.__append_fabric_intf_object("virtualPortChannels", template, port_config)
        else:
            raise Exception(
                "port_config is not valid, you must pass an object of types PhysicalIntfResource | PortChannelResource | VPCResource"
            )

        url = f'{self.base_path}{PATH_TEMPLATES}/{resource["templateId"]}'
        resp = self.session.put(url, json=resource)
        if resp.status_code >= 400:
            raise Exception(resp.json())
