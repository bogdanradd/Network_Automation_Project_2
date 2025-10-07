"""This module represents a connector for SWAGGER connections"""

import ipaddress
import json
import requests
import urllib3
import time
from bravado.client import SwaggerClient
from bravado.requests_client import RequestsClient
from pyats.topology import Device
from urllib3.exceptions import InsecureRequestWarning


def _ensure_netobj(client, cidr: str):
    """This method is used to create network objects on FTD"""
    net = ipaddress.ip_network(cidr, strict=False)
    name = f"NET_{net.network_address}_{net.prefixlen}"
    existing = client.NetworkObject.getNetworkObjectList(
        filter=f"name:{name}"
    ).result()
    if existing["items"]:
        return existing["items"][0]
    body = {"type": "networkobject", "name": name, "subType": "NETWORK",
            "value": f"{net.network_address}/{net.prefixlen}"}
    return client.NetworkObject.addNetworkObject(body=body).result()


class SwaggerConnector:
    """This class takes care of SWAGGER connections"""

    def __init__(self, device: Device, **kwargs):
        self.device: Device = device
        self.client = None
        self.connected = False
        self._session = None
        self._headers = None
        self._auth = None
        self._url = None
        self.__access_token = None
        self.__refresh_token = None
        self.__token_type = None
        urllib3.disable_warnings(InsecureRequestWarning)

    def connect(self):
        """This method connects via SWAGGER"""
        host = self.device.connections.swagger.ip
        port = self.device.connections.swagger.port
        protocol = self.device.connections.swagger.protocol
        self._url = f'{protocol}://{host}:{port}'
        self._headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        self.__login()
        self.connected = True
        return self

    def __login(self):
        """This method is used to login via SWAGGER with credentials from testbed"""
        endpoint = '/api/fdm/latest/fdm/token'
        response = requests.post(
            url=self._url + endpoint,
            headers=self._headers,
            verify=False,
            data=json.dumps(
                {
                    'username': self.device.connections.telnet.credentials.login.username,
                    'password': self.device.connections.telnet.credentials.login.password.plaintext,
                    'grant_type': 'password',
                }
            )
        )
        self.__access_token = response.json()['access_token']
        self.__refresh_token = response.json()['refresh_token']
        self.__token_type = response.json()['token_type']
        self._headers.update({'Authorization': f'{self.__token_type} {self.__access_token}'})

    def get_swagger_client(self):
        """This method is used to return the SWAGGER client"""
        endpoint = '/apispec/ngfw.json'
        http_client = RequestsClient()
        http_client.session.verify = False
        http_client.ssl_verify = False
        http_client.session.headers = self._headers
        self.client = SwaggerClient.from_url(
            spec_url=self._url + endpoint,
            http_client=http_client,
            request_headers=self._headers,
            config={'validate_certificate': False, 'validate_responses': False, },
        )
        return self.client

    def finish_initial_setup(self):
        """This method is used to finish the initial GUI setup"""

        body = {
            "type": "initialprovision",
            "id": "default",
            "acceptEULA": True,
            "startTrialEvaluation": True,
            "selectedPerformanceTierId": "FTDv5",
        }

        return self.client.InitialProvision.addInitialProvision(body=body).result()

    def delete_existing_dhcp_sv(self):
        """This method is used to delete the existing DHCP pool"""
        dhcp_servers = self.client.DHCPServerContainer.getDHCPServerContainerList().result()
        for dhcp_server in dhcp_servers['items']:
            dhcp_serv_list = dhcp_server['servers']
            print(dhcp_serv_list)
            dhcp_server.servers = []
            response = self.client.DHCPServerContainer.editDHCPServerContainer(
                objId=dhcp_server.id,
                body=dhcp_server,
            ).result()
            return response

    def configure_ftd_interfaces(self, interface1, interface2):
        """This method is used to configure the other FTD interfaces"""
        existing_interfaces = self.client.Interface.getPhysicalInterfaceList().result()
        responses = []
        for interface in existing_interfaces['items']:
            if interface.hardwareName == interface1.name:
                interface.ipv4.ipAddress.ipAddress = interface1.ipv4.ip.compressed
                interface.ipv4.ipAddress.netmask = interface1.ipv4.netmask.exploded
                interface.ipv4.dhcp = False
                interface.ipv4.ipType = 'STATIC'
                interface.enable = True
                interface.name = interface1.alias
                response1 = self.client.Interface.editPhysicalInterface(
                    objId=interface.id,
                    body=interface,
                ).result()
                responses.append(response1)

            if interface.hardwareName == interface2.name:
                interface.ipv4.ipAddress.ipAddress = interface2.ipv4.ip.compressed
                interface.ipv4.ipAddress.netmask = interface2.ipv4.netmask.exploded
                interface.ipv4.dhcp = False
                interface.ipv4.ipType = 'STATIC'
                interface.enable = True
                interface.name = interface2.alias
                response2 = self.client.Interface.editPhysicalInterface(
                    objId=interface.id,
                    body=interface,
                ).result()
                responses.append(response2)
        return responses

    def configure_new_dhcp_sv(self, iface):
        """This method is used to configure the new DHCP pool for DockerGuest-1"""
        interface_for_dhcp = None
        existing_interfaces = self.client.Interface.getPhysicalInterfaceList().result()
        for interface in existing_interfaces['items']:
            if interface.hardwareName == iface.name:
                interface_for_dhcp = interface
        dhcp_servers = self.client.DHCPServerContainer.getDHCPServerContainerList().result()
        for dhcp_server in dhcp_servers['items']:
            dhcp_serv_list = dhcp_server['servers']
            print(dhcp_serv_list)
            dhcp_server_model = self.client.get_model('DHCPServer')
            interface_ref_model = self.client.get_model('ReferenceModel')
            dhcp_server.servers = [
                dhcp_server_model(
                    addressPool='192.168.205.100-192.168.205.200',
                    enableDHCP=True,
                    interface=interface_ref_model(
                        id=interface_for_dhcp.id,
                        name=interface_for_dhcp.name,
                        type='physicalinterface',
                    ),
                    type='dhcpserver'
                )
            ]
            response = self.client.DHCPServerContainer.editDHCPServerContainer(
                objId=dhcp_server.id,
                body=dhcp_server,
            ).result()
            return response

    def configure_ospf(self, vrf_id, name, process_id,
                       area_id, if_to_cidr):
        """This method is used to create new network objects and assign them in the OSPF process"""
        ref = self.client.get_model("ReferenceModel")

        if_list = self.client.Interface.getPhysicalInterfaceList().result()["items"]
        name_to_if = {i.name: i for i in if_list}

        area_networks = []
        for if_name, cidr in if_to_cidr:
            itf = name_to_if[if_name]
            netobj = _ensure_netobj(self.client, cidr)
            area_networks.append({
                "type": "areanetwork",
                "ipv4Network": ref(id=netobj.id, name=netobj.name, type="networkobject"),
                "tagInterface": ref(
                    id=itf.id, name=itf.name, type="physicalinterface",
                    hardwareName=itf.hardwareName,
                ),
            })

        body = {
            "type": "ospf",
            "name": name,
            "processId": str(process_id),
            "areas": [{
                "type": "area",
                "areaId": str(area_id),
                "areaNetworks": area_networks,
                "virtualLinks": [],
                "areaRanges": [],
                "filterList": [],
            }],
            "neighbors": [],
            "summaryAddresses": [],
            "redistributeProtocols": [],
            "filterRules": [],
            "logAdjacencyChanges": {"type": "logadjacencychanges", "logType": "DETAILED"},
            "processConfiguration": {
                "type": "processconfiguration",
                "administrativeDistance": {
                    "type": "administrativedistance",
                    "intraArea": 110, "interArea": 110, "external": 110
                },
                "timers": {
                    "type": "timers",
                    "floodPacing": 33,
                    "lsaArrival": 1000,
                    "lsaGroup": 240,
                    "retransmission": 66,
                    "lsaThrottleTimer": {
                        "type": "lsathrottletimer",
                        "initialDelay": 0, "minimumDelay": 5000, "maximumDelay": 5000
                    },
                    "spfThrottleTimer": {
                        "type": "spfthrottletimer",
                        "initialDelay": 5000, "minimumHoldTime": 10000, "maximumWaitTime": 10000
                    }
                }
            }
        }

        return self.client.OSPF.addOSPF(vrfId=vrf_id, body=body).result()

    def deploy(self):
        """This method is used to deploy current configuration on FTD"""
        res = self.client.Deployment.addDeployment(body={"forceDeploy": True}).result()
        dep_id = res.id

        terminal = {"DEPLOYED", "FAILED", "ERROR", "CANCELLED", "CANCELED"}
        while True:
            cur = self.client.Deployment.getDeployment(objId=dep_id).result()
            state = (cur.state or "").upper()
            if state in terminal:
                print(cur.statusMessage)
                break
            time.sleep(2)

    def add_allow_rule(self, inside_interface, outside_interface, policy_name="NGFW-Access-Policy"):
        """This method is used to create security zones and add bidirectional access rules"""
        ref_model = self.client.get_model("ReferenceModel")
        security_zone_model = self.client.get_model("SecurityZone")
        access_rule_model = self.client.get_model("AccessRule")

        existing_interfaces = self.client.Interface.getPhysicalInterfaceList().result()

        inside_if = None
        outside_if = None
        for interface in existing_interfaces['items']:
            if interface.name == inside_interface:
                inside_if = interface
            if interface.name == outside_interface:
                outside_if = interface

        existing_zones = self.client.SecurityZone.getSecurityZoneList().result()
        inside_zone = next((z for z in existing_zones['items'] if z.name == "InsideSecZone"), None)
        outside_zone = next((z for z in existing_zones['items'] if z.name == "OutsideSecZone"), None)

        if not inside_zone:
            inside_zone_body = security_zone_model(
                name="InsideSecZone",
                mode="ROUTED",
                type="securityzone",
                interfaces=[ref_model(type="physicalinterface", id=inside_if.id, name=inside_if.name)]
            )
            inside_zone = self.client.SecurityZone.addSecurityZone(body=inside_zone_body).result()

        if not outside_zone:
            outside_zone_body = security_zone_model(
                name="OutsideSecZone",
                mode="ROUTED",
                type="securityzone",
                interfaces=[ref_model(type="physicalinterface", id=outside_if.id, name=outside_if.name)]
            )
            outside_zone = self.client.SecurityZone.addSecurityZone(body=outside_zone_body).result()

        policies = self.client.AccessPolicy.getAccessPolicyList().result()
        policy = next(p for p in policies.items if p.name == policy_name)
        policy_id = policy.id

        inside_zone_ref = ref_model(id=inside_zone.id, type="securityzone")
        outside_zone_ref = ref_model(id=outside_zone.id, type="securityzone")

        result = []
        rule1_body = access_rule_model(
            name="Inside_Outside",
            action="PERMIT",
            enabled=True,
            type="accessrule",
            sourceZones=[inside_zone_ref],
            destinationZones=[outside_zone_ref]
        )
        result.append(self.client.AccessPolicy.addAccessRule(parentId=policy_id, body=rule1_body).result())

        rule2_body = access_rule_model(
            name="Outside_Inside",
            action="PERMIT",
            enabled=True,
            type="accessrule",
            sourceZones=[outside_zone_ref],
            destinationZones=[inside_zone_ref]
        )
        result.append(self.client.AccessPolicy.addAccessRule(parentId=policy_id, body=rule2_body).result())

        return result

    def add_attacker_rule(self, cidrs, policy_name='NGFW-Access-Policy', rule_name='DENY_ATTACKER'):
        """This method is used to add a rule against Attacker"""
        ref_model = self.client.get_model("ReferenceModel")
        access_rule_model = self.client.get_model("AccessRule")

        policies = self.client.AccessPolicy.getAccessPolicyList().result()
        items = policies.items
        policy = next(p for p in items if p.name == policy_name)
        policy_id = policy.id

        rules = self.client.AccessPolicy.getAccessRuleList(parentId=policy_id).result()
        r_items = rules.items
        allow_1 = next((r for r in r_items if r.name == "Inside_Outside"), None)
        if allow_1:
            self.client.AccessPolicy.deleteAccessRule(
                parentId=policy_id,
                objId=allow_1.id,
            ).result()
        allow_2 = next((r for r in r_items if r.name == "Outside_Inside"), None)
        if allow_2:
            self.client.AccessPolicy.deleteAccessRule(
                parentId=policy_id,
                objId=allow_2.id,
            ).result()

        src_obj = _ensure_netobj(self.client, cidrs[0])
        dst_obj = _ensure_netobj(self.client, cidrs[1])
        src_ref = ref_model(id=src_obj.id, name=src_obj.name, type="networkobject")
        dst_ref = ref_model(id=dst_obj.id, name=dst_obj.name, type="networkobject")

        body = access_rule_model(
            type="accessrule",
            name=rule_name,
            enabled=True,
            ruleAction="DENY",
            sourceNetworks=[src_ref],
            destinationNetworks=[dst_ref],
            order=1
        )
        return self.client.AccessPolicy.addAccessRule(
            parentId=policy_id,
            body=body,
        ).result()
