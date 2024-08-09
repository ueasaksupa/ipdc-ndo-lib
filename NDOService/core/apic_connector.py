from .path_const import *
from .types import *
from .configurations import *

from pprint import pprint
from dataclasses import asdict
from typing import Literal, Any
import requests
import urllib3
import time
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APICTemplate:
    def __init__(self, host, username, password, port=443):
        self.host = host
        self.username = username
        self.password = password
        self.base_path = f"https://{self.host}:{port}"
        self.session = requests.Session()
        # LOGIN
        self.login()

    def login(self) -> None:
        print("- TRYING TO LOGIN TO APIC")
        self.session = requests.session()
        self.session.verify = False
        self.session.trust_env = False
        payload = {"aaaUser": {"attributes": {"name": self.username, "pwd": self.password}}}
        url = f"{self.base_path}{PATH_APIC_LOGIN}"
        self.session.post(url, json=payload).json()
        print("- LOGIN SUCCESS")

    def create_stormcontrol_policy(self, name: str, config: StormCtlConfig | None = None) -> None:
        print(f"- CREATING STORM CONTROL POLICY {name}")
        if config is None:
            config = StormCtlConfig()
        payload = {
            "stormctrlIfPol": {
                "attributes": {
                    "dn": f"uni/infra/stormctrlifp-{name}",
                    "isUcMcBcStormPktCfgValid": "Valid",
                    "bcRatePps": f"{config.broadcastPPS}",
                    "bcBurstPps": f"{config.broadcastMaxBurstPPS}",
                    "mcRatePps": f"{config.multicastPPS}",
                    "mcBurstPps": f"{config.multicastMaxBurstPPS}",
                    "uucRatePps": f"{config.unicastPPS}",
                    "uucBurstPps": f"{config.unicastMaxBurstPPS}",
                    "name": f"{name}",
                    "rn": f"stormctrlifp-{name}",
                    "stormCtrlAction": config.action,
                    "stormCtrlSoakInstCount": f"{config.soakInstCount}",
                    "status": "created",
                },
                "children": [],
            }
        }

        url = f"{self.base_path}{PATH_APIC_STORM_CONTROL}".format(name=name)
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())
        print(f"- CREATE SUCCESS")

    def apply_stormcontrol_to_interface_policy(self, storm_pol_name: str, intf_pol_name: str) -> None:
        """
        Applies a storm control policy to an interface policy.
        Args:
            storm_pol_name (str): The name of the storm control policy. use empty string("") to remove storm control policy
            intf_pol_name (str): The name of the interface policy.
        Raises:
            Exception: If the HTTP response status code is 400 or above.
        Returns:
            None
        """

        print(f"- APPLYING STORM CONTROL POLICY {storm_pol_name} TO INTERFACE POLICY {intf_pol_name}")
        payload = {
            "infraRsStormctrlIfPol": {
                "attributes": {"tnStormctrlIfPolName": storm_pol_name},
                "children": [],
            }
        }

        url = f"{self.base_path}{PATH_APIC_INTF_POL}".format(name=intf_pol_name)
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())
        print(f"- APPLY SUCCESS")

    def apply_stormcontrol_to_bundle_policy(self, storm_pol_name: str, bundle_name: str) -> None:
        """
        Applies a storm control policy to the bundle interface.
        Args:
            storm_pol_name (str): The name of the storm control policy. use empty string("") to remove storm control policy
            bundle_name (str): The name of the bundle interface.
        Raises:
            Exception: If the HTTP response status code is 400 or above.
        Returns:
            None
        """
        print(f"- APPLYING STORM CONTROL POLICY {storm_pol_name} TO INTERFACE BUNDLE {bundle_name}")
        payload = {
            "infraRsStormctrlIfPol": {
                "attributes": {"tnStormctrlIfPolName": storm_pol_name},
                "children": [],
            }
        }

        url = f"{self.base_path}{PATH_APIC_BUNDLE_POL}".format(name=bundle_name)
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())
        print(f"- APPLY SUCCESS")

    def enable_port(self, port_id: str, node_id: str) -> None:
        print(f"- ENABLING PORT {port_id} ON {node_id}")
        payload = {
            "fabricRsOosPath": {
                "attributes": {
                    "tDn": f"topology/pod-1/paths-{node_id}/pathep-[eth{port_id.strip('eth')}]",
                    "lc": "blacklist",
                    "status": "deleted",
                },
                "children": [],
            }
        }

        url = f"{self.base_path}{PATH_APIC_PORT_STATUS}"
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())
        print(f"- SUCCESS")

    def disable_port(self, port_id: str, node_id: str) -> None:
        print(f"- ENABLING PORT {port_id} ON {node_id}")
        payload = {
            "fabricRsOosPath": {
                "attributes": {
                    "tDn": f"topology/pod-1/paths-{node_id}/pathep-[eth{port_id.strip('eth')}]",
                    "lc": "blacklist",
                },
                "children": [],
            }
        }

        url = f"{self.base_path}{PATH_APIC_PORT_STATUS}"
        resp = self.session.post(url, json=payload)
        if resp.status_code >= 400:
            raise Exception(resp.json())
        print(f"- SUCCESS")
