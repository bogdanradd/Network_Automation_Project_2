"""
This test will configure all devices.
"""
import time
import subprocess
import asyncio

from bravado.exception import HTTPError
from pyats import aetest, topology
from pyats.topology import Device
from genie.libs.conf.interface.iosxe import Interface
from genie.libs.conf.ospf import Ospf
from lib.connectors.ssh_conn import SSHConnection
from lib.connectors.swagger_conn import SwaggerConnector
from lib.connectors.async_telnet_conn import TelnetConnection
from ssh_config import commands
from int_config import add_ips
from dhcp_config import dhcp_commands
from ospf_config import ospf_commands
from ssh_acl import acl_commands


async def telnet_configure_ssh(conn: TelnetConnection, templates, prompt, **kwargs):
    """This is a helper function that is being called inside pyats in order to configure the SSH connection on the devices."""
    await conn.connect()
    time.sleep(1)
    return await conn.configure_ssh(templates=templates, prmt=prompt, **kwargs)


async def telnet_configure_ftd(conn: TelnetConnection, hostname, ip, netmask, gateway, password):
    """This is a helper function that is being called inside pyats in order to configure FTD's initial setup."""
    await conn.connect()
    time.sleep(1)
    return await conn.configure_ftd(
        hostname=hostname,
        ip=ip,
        netmask=netmask,
        gateway=gateway,
        password=password,
    )

async def initial_setup_csr(conn: TelnetConnection):
    """This is a helper function that is being called inside pyats in order to initialize CSR."""
    await conn.connect()
    time.sleep(1)
    return await conn.initialize()



class CommonSetup(aetest.CommonSetup):
    """This class is used as a general class. It contains every method used to configure all devices."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tb = None
        self.dev = None
        self._swagger_conn = None

    def ensure_csr_connection(self):
        """Ensure CSR is connected via unicon and return the device handle."""
        if not self.dev:
            self.dev: Device = self.tb.devices.CSR
        if not getattr(self.dev, "connected", False):
            self.dev.connect(log_stdout=True, via='unicon')
        return self.dev

    def ensure_ssh_connection(self, device_name):
        """Establish SSH connection for a given device and return the connector."""
        dev = self.tb.devices[device_name]
        conn_class = dev.connections.get("ssh", {}).get("class", None)
        assert conn_class, f"No SSH connection for {device_name}"

        conn: SSHConnection = conn_class(
            host=str(dev.connections.ssh['ip']),
            port=str(dev.connections.ssh['port']),
            username=dev.connections.ssh.credentials.login['username'],
            password=dev.connections.ssh.credentials.login['password'].plaintext,
        )
        conn.connect()
        return conn

    def ensure_swagger_connection(self):
        """Ensure a SwaggerConnector is available for the firewall device and return it."""
        if self._swagger_conn is not None:
            return self._swagger_conn

        for device in self.tb.devices:
            dev = self.tb.devices[device]
            if dev.custom.role != 'firewall':
                continue
            if "swagger" not in dev.connections:
                continue

            connection: SwaggerConnector = dev.connect(via='swagger')
            swagger = connection.get_swagger_client()
            if not swagger:
                self.failed('No swagger connection')
            self._swagger_conn = connection
            return self._swagger_conn

    @aetest.subsection
    def load_testbed(self, steps):
        """This method loads the testbed that provides details about whole topology."""
        with steps.start("Load testbed"):
            self.tb = topology.loader.load('main_testbed.yaml')
        self.parent.parameters.update(tb=self.tb)

    @aetest.subsection
    def bring_up_server_interface(self, steps):
        """This method adds an IP address and some routes to the container"""
        server = self.tb.devices['UbuntuServer']
        with steps.start("Bring up container interface"):
            for intf_name, intf in server.interfaces.items():
                subprocess.run(['sudo', 'ip', 'addr', 'replace',
                                f'{intf.ipv4}',
                                'dev', f'{intf_name}'],
                               check=True)
                subprocess.run(['sudo', 'ip', 'link', 'set', 'dev',
                                f'{intf_name}', 'up'],
                               check=True)
        with steps.start("Add routes on container"):
            for device in self.tb.devices:
                if self.tb.devices[device].type != 'router':
                    continue
                gateway = self.tb.devices[device].interfaces['initial'].ipv4.ip.compressed
                csr_gw = self.tb.devices['CSR'].interfaces['initial'].ipv4.ip.compressed
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name == 'management':
                        continue
                    subnet = self.tb.devices[device].interfaces[interface].ipv4.network.compressed
                    subprocess.run(['sudo', 'ip', 'route', 'replace',
                                    f'{subnet}',
                                    'via', f'{gateway}'],
                                   check=True)
                    if subnet in ['192.168.204.0/24', '192.168.205.0/24']:
                        subprocess.run(['sudo', 'ip', 'route', 'replace', f'{subnet}', 'via', f'{csr_gw}'],
                                       check=True)

    @aetest.subsection
    def initial_setup_csr(self, steps):
        """This method initializes CSR"""
        with steps.start("Initial CSR setup"):
            device = self.tb.devices['CSR']
            conn_class = device.connections.get("telnet", {}).get("class", None)
            assert conn_class, f"No connection for {device}"
            ip = device.connections.telnet.ip.compressed
            port = device.connections.telnet.port
            try:
                conn = conn_class(ip, port)
                asyncio.run(initial_setup_csr(conn))
            except Exception as e:
                print(f'Failed to connect to device {device}', e)

    @aetest.subsection
    def configure_ssh(self, steps):
        """This method configures the SSH connection."""
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'router':
                continue
            with steps.start(f"Configure SSH connection on {device}"):
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name != 'management':
                        continue
                    intf_obj = self.tb.devices[device].interfaces[interface]
                    conn_class = self.tb.devices[device].connections.get(
                        'telnet', {}
                    ).get('class', None)
                    assert conn_class, f'No connection for device {device}'
                    ip = self.tb.devices[device].connections.telnet.ip.compressed
                    port = self.tb.devices[device].connections.telnet.port
                    username = self.tb.devices[device].connections.ssh.credentials.login.username
                    password = self.tb.devices[device].connections.ssh.credentials.login.password.plaintext
                    domain = self.tb.devices[device].custom.get('domain', None)
                    try:
                        conn: TelnetConnection = conn_class(ip, port)
                        asyncio.run(
                            telnet_configure_ssh(
                                conn,
                                templates=commands,
                                prompt='#',
                                interface=interface,
                                ip=intf_obj.ipv4.ip.compressed,
                                sm=intf_obj.ipv4.netmask.exploded,
                                hostname=device,
                                username=username,
                                password=password,
                                domain=domain,
                            )
                        )
                    except Exception as e:
                        print(f'Failed to connect to device {device}', e)
                        continue

    @aetest.subsection
    def bring_up_ftd_interface(self, steps):
        """This method adds an ip address to FTD's management interface."""
        with steps.start("Bring up FTD management interface"):
            for device in self.tb.devices:
                if self.tb.devices[device].custom.role != 'firewall':
                    continue
                for interface in self.tb.devices[device].interfaces:
                    if self.tb.devices[device].interfaces[interface].link.name != 'management':
                        continue

                    intf_obj = self.tb.devices[device].interfaces[interface]
                    hostname = self.tb.devices[device].custom.hostname
                    gateway = self.tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
                    conn_class = self.tb.devices[device].connections.get('telnet', {}).get('class', None)
                    assert conn_class, f'No connection for device {device}'
                    ip = self.tb.devices[device].connections.telnet.ip.compressed
                    port = self.tb.devices[device].connections.telnet.port
                    password = self.tb.devices[device].connections.telnet.credentials.login.password.plaintext
                    conn: TelnetConnection = conn_class(ip, port)

                    asyncio.run(
                        telnet_configure_ftd(
                            conn,
                            hostname=hostname,
                            ip=intf_obj.ipv4.ip.compressed,
                            netmask=intf_obj.ipv4.netmask.exploded,
                            gateway=gateway,
                            password=password,
                        )
                    )

    @aetest.subsection
    def ssh_configure_interfaces(self, steps):
        """This method is used to configure all other active interfaces on IOU1 and IOSv via SSH"""
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'router':
                continue
            if 'unicon' in self.tb.devices[device].connections:
                continue
            with steps.start(f"Configure interfaces on {device}"):
                conn = self.ensure_ssh_connection(device)
                try:
                    for interface in self.tb.devices[device].interfaces:
                        if self.tb.devices[device].interfaces[interface].link.name == 'management':
                            continue
                        intf_obj = self.tb.devices[device].interfaces[interface]
                        print(
                            conn.configure(
                                add_ips,
                                interface=interface,
                                ip=intf_obj.ipv4.ip.compressed,
                                sm=intf_obj.ipv4.netmask.exploded,
                            )
                        )
                finally:
                    conn.close()

    @aetest.subsection
    def ssh_configure_dhcp_iou1(self, steps):
        """This method is used to configure a new DHCP pool on IOU1 via SSH"""
        device = self.tb.devices['IOU1']
        intf_obj = device.interfaces['Ethernet0/1']
        guest_network = intf_obj.ipv4.network.network_address.exploded
        guest_subnetmask = intf_obj.ipv4.netmask.exploded
        guest_gateway = intf_obj.ipv4.ip.compressed
        with steps.start("Configure DHCP on IOU1"):
            conn = self.ensure_ssh_connection('IOU1')
            try:
                print(
                    conn.configure(
                        dhcp_commands,
                        guest_nw=guest_network,
                        guest_gw=guest_gateway,
                        guest_sm=guest_subnetmask,
                    )
                )
            finally:
                conn.close()

    @aetest.subsection
    def ssh_configure_ospf(self, steps):
        """This method is used to configure OSPF on IOU1 and IOSv via SSH"""
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'router':
                continue
            if 'unicon' in self.tb.devices[device].connections:
                continue
            with steps.start(f"Configure OSPF on {device}"):
                conn = self.ensure_ssh_connection(device)
                try:
                    for interface in self.tb.devices[device].interfaces:
                        print(conn.configure(ospf_commands, interface=interface))
                finally:
                    conn.close()

    @aetest.subsection
    def ssh_configure_acl(self, steps):
        """This method is used to configure an ACL SSH on IOU1 and IOSv via SSH"""
        for device in self.tb.devices:
            if self.tb.devices[device].custom.role != 'router':
                continue
            if 'unicon' in self.tb.devices[device].connections:
                continue
            with steps.start(f"Configure ACL on {device}"):
                conn = self.ensure_ssh_connection(device)
                try:
                    container_ip = self.tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
                    print(conn.configure(acl_commands, ssh_container=container_ip))
                finally:
                    conn.close()

    @aetest.subsection
    def genie_configure_other_interfaces(self, steps):
        """This method is used to configure all other interfaces on CSR via GENIE"""
        with steps.start("Configure other CSR interfaces via GENIE"):
            try:
                dev = self.ensure_csr_connection()
            except Exception as e:
                print('Failed to connect with genie to CSR', e)
            for ifname in ("GigabitEthernet2", "GigabitEthernet3"):
                intf = Interface(name=ifname)
                intf.device = dev
                intf.ipv4 = dev.interfaces[ifname].ipv4
                intf.enabled = True
                cfg = intf.build_config(apply=False)
                dev.configure(cfg.cli_config.data)

    @aetest.subsection
    def genie_configure_ospf(self, steps):
        """This method is used to configure OSPF on CSR via GENIE"""
        with steps.start("Configure OSPF on CSR via GENIE"):
            try:
                dev = self.ensure_csr_connection()
            except Exception as e:
                print('Failed to connect with genie to CSR', e)
            ospf = Ospf()
            da = ospf.device_attr[dev]
            va = da.vrf_attr['default']
            va.instance = '1'
            for ifname in ("GigabitEthernet1", "GigabitEthernet2", "GigabitEthernet3"):
                ia = va.area_attr['0'].interface_attr[ifname]
                ia.if_admin_control = True
            cfg = da.build_config(apply=False)
            dev.configure(cfg.cli_config.data)

    @aetest.subsection
    def genie_configure_ssh_acl(self, steps):
        """This method is used to configure an SSH ACL on CSR via GENIE"""
        with steps.start("Configure SSH ACL on CSR via GENIE"):
            try:
                dev = self.ensure_csr_connection()
            except Exception as e:
                print('Failed to connect with genie to CSR', e)
            container_ip = self.tb.devices['UbuntuServer'].interfaces['ens4'].ipv4.ip.compressed
            cfg = f"""
            ip access-list standard SSH
             permit host {container_ip}
             deny any
            line vty 0 4
             access-class SSH in
             transport input ssh
            """
            dev.configure(cfg)

    @aetest.subsection
    def swagger_connect_and_initial_setup(self, steps):
        """This method is being used to finish initial FTD setup and continue configuring it."""
        with steps.start("Connect to FTD and finish initial setup"):
            connection = self.ensure_swagger_connection()
            swagger = connection.get_swagger_client()
            print(swagger)
            try:
                connection.finish_initial_setup()
            except HTTPError as e:
                print('Initial setup is complete:', e)

    @aetest.subsection
    def swagger_delete_existing_dhcp(self, steps):
        """This method deletes existing DHCP configuration on FTD"""
        with steps.start("Delete existing DHCP on FTD"):
            connection = self.ensure_swagger_connection()
            try:
                print(connection.delete_existing_dhcp_sv())
            except HTTPError as e:
                print('No existing DHCP server', e)

    @aetest.subsection
    def swagger_configure_ftd_interfaces(self, steps):
        """This method configures all other active interfaces on FTD via SWAGGER"""
        with steps.start("Configure other interfaces on FTD"):
            connection = self.ensure_swagger_connection()
            ftd_ep2 = connection.device.interfaces['inside']
            csr_ftd = connection.device.interfaces['outside']
            try:
                print(connection.configure_ftd_interfaces(csr_ftd, ftd_ep2))
            except HTTPError as e:
                print('FTD interfaces already configured:', e)

    @aetest.subsection
    def swagger_configure_new_dhcp(self, steps):
        """This method configures a new DHCP pool on FTD via SWAGGER"""
        with steps.start("Configure new DHCP on FTD"):
            connection = self.ensure_swagger_connection()
            ftd_ep2 = connection.device.interfaces['inside']
            try:
                print(connection.configure_new_dhcp_sv(ftd_ep2))
            except HTTPError as e:
                print('Could not configure new DHCP server', e)

    @aetest.subsection
    def swagger_configure_ospf(self, steps):
        """This method configures OSPF on FTD via SWAGGER"""
        with steps.start("Configure OSPF on FTD"):
            connection = self.ensure_swagger_connection()
            try:
                ospf = connection.configure_ospf(
                    vrf_id='default',
                    name='ospf_1',
                    process_id='1',
                    area_id='0',
                    if_to_cidr=[
                        ('outside', '192.168.204.0/24'),
                        ('inside', '192.168.205.0/24'),
                    ],
                )
                print(ospf)
            except HTTPError as e:
                print('Could not configure OSPF on FTD:', e)

    @aetest.subsection
    def swagger_add_allow_rule(self, steps):
        """This method is used to add an allow rule on FTD in order to allow traffic to flow through it."""
        with steps.start("Add allow rule on FTD"):
            connection = self.ensure_swagger_connection()
            try:
                allow_rule = connection.add_allow_rule(inside_interface='inside', outside_interface='outside')
                print(allow_rule)
            except HTTPError as e:
                print('Could not add allow rule on FTD:', e)

    @aetest.subsection
    def swagger_deploy(self, steps):
        """This method is being used to deploy actual configuration on FTD"""
        with steps.start("Deploy FTD configuration"):
            connection = self.ensure_swagger_connection()
            try:
                connection.deploy()
            except HTTPError as e:
                print('Deployment failed:', e)


if __name__ == '__main__':
    aetest.main()
