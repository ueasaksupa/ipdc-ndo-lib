from .path_const import *
from .types import *
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NDOTenantTemplate:
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

    def find_tenant_by_name(self, tenant_name) -> Tenant | None:
        url = f"{self.base_path}{PATH_TENANTS}"
        # Get all
        resp: list = self.session.get(url).json()["tenants"]
        # filter by name
        filter_tenants = list(filter(lambda t: t["name"].upper() == tenant_name.upper(), resp))
        if len(filter_tenants) > 0:
            return filter_tenants[0]

        return None

    def find_schema_by_name(self, schema_name) -> Schema | None:
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

    def find_vpc_by_site(self, vpc_name, site_name) -> VPCResourcePolicy | None:
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

    # Tenant Template
    def save_schema(self, schema: dict) -> Schema:
        print(f"--- Saving schema {schema['displayName']}")
        url = f"{self.base_path}{PATH_SCHEMAS}/{schema['id']}"
        return self.session.put(url, json=schema).json()

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

    def create_vrf_under_template(self, schema: dict, template_name: str, vrf_name: str, vrf_desc: str = "") -> Vrf:
        print(f"--- Creating VRF {vrf_name}")
        template = list(
            filter(
                lambda t: t["name"].upper() == template_name.upper(),
                schema["templates"],
            )
        )
        if len(template) == 0:
            raise Exception(f"Template {template_name} does not exist.")

        target_template_index = schema["templates"].index(template[0])
        filter_vrf = list(filter(lambda d: d["name"].upper() == vrf_name.upper(), template[0]["vrfs"]))
        if len(filter_vrf) != 0:
            print(f"  |--- VRF {vrf_name} is already exist")
            return filter_vrf[0]

        # TODO
        # Parameterized flags
        payload = {
            "displayName": vrf_name,
            "name": vrf_name,
            "description": vrf_desc,
            "l3MCast": False,
            "preferredGroup": False,
            "vzAnyEnabled": False,
            "ipDataPlaneLearning": "enabled",
        }
        schema["templates"][target_template_index]["vrfs"].append(payload)
        return schema["templates"][target_template_index]["vrfs"][-1]

    def create_bridge_domain_under_template(
        self,
        schema: dict,
        template_name_vrf: str,
        template_name_bd: str,
        linked_vrf_name: str,
        bd_name: str,
        bd_desc: str = "",
    ) -> BD:
        print(f"--- Creating BD under template {template_name_bd}")
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

        # TODO
        # Parameterized flags
        # "vrfRef": f"/schemas/{schema['id']}/templates/{template_name_vrf}/vrfs/{linked_vrf_name}",
        payload = {
            "name": bd_name,
            "displayName": bd_name,
            "vrfRef": {
                "schemaID": schema["id"],
                "templateName": template_name_vrf,
                "vrfName": linked_vrf_name,
            },
            "description": bd_desc,
            "l2UnknownUnicast": "proxy",
            "intersiteBumTrafficAllow": True,
            "optimizeWanBandwidth": True,
            "l2Stretch": True,
            "l3MCast": False,
            "unkMcastAct": "flood",
            "v6unkMcastAct": "flood",
            "arpFlood": True,
            "multiDstPktAct": "bd-flood",
            "unicastRouting": True,
        }
        schema["templates"][template_index]["bds"].append(payload)
        return schema["templates"][template_index]["bds"][-1]

    def create_anp_under_template(self, schema: dict, template_name: str, anp_name: str, anp_desc: str = "") -> ANP:
        print(f"--- Creating ANP under template {template_name}")
        filter_template = list(filter(lambda t: t["name"].upper() == template_name.upper(), schema["templates"]))
        if len(filter_template) == 0:
            raise Exception(f"Template {template_name} does not exist.")

        template_index = schema["templates"].index(filter_template[0])

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
        schema["templates"][template_index]["anps"].append(payload)
        return schema["templates"][template_index]["anps"][-1]

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
            "contractRelationships": [],
            "subnets": [],
            "uSegEpg": False,
            "uSegAttrs": [],
            "intraEpg": "unenforced",
            "prio": "unspecified",
            "proxyArp": False,
            "mCastSource": False,
            "preferredGroup": False,
            "bdRef": {"schemaID": schema["id"], "templateName": linked_template, "bdName": linked_bd},
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
            if conf["port_type"] == "vpc":
                vpc_resource = self.find_vpc_by_site(conf["port_name"], site_name)
                if not vpc_resource:
                    raise Exception(
                        f"VPC resource name {conf['port_name']} does not exist in the Fabric Resource Policy, Please create it first."
                    )
                path = vpc_resource["path"]
            elif conf["port_type"] == "port":
                path = f"topology/{pod}/paths-{conf['node']}/pathep-[{conf['port_name']}]"
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

    # Fabric Template
    def find_fabric_policy_by_name(self, name) -> FabricPolicy | None:
        url = f"{self.base_path}{PATH_FABRIC_POLICIES_SUM}"
        resp = self.session.get(url).json()
        filtered_resp = list(filter(lambda p: p["templateName"] == name, resp))
        if len(filtered_resp) == 0:
            return None
        else:
            url = f"{self.base_path}{PATH_TEMPLATES}/{filtered_resp[0]['templateId']}"
            return self.session.get(url).json()

    def find_fabric_resource_by_name(self, name) -> FabricPolicy | None:
        url = f"{self.base_path}{PATH_FABRIC_RESOURCES_SUM}"
        resp = self.session.get(url).json()
        filtered_resp = list(filter(lambda p: p["templateName"] == name, resp))
        if len(filtered_resp) == 0:
            return None
        else:
            url = f"{self.base_path}{PATH_TEMPLATES}/{filtered_resp[0]['templateId']}"
            return self.session.get(url).json()

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
        print(f"--- Adding vlans {",".join([str(v) for v in vlans])} to pool {pool_name}")
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
