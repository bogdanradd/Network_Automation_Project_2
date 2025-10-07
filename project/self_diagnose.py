"""Self-diagnose module for network devices using telnet"""
import asyncio
import time

from project.config_helper import ParseConfig
from lib.connectors.async_telnet_conn import TelnetConnection

DEVICES = {
    'IOU1': {'host': '92.81.55.146', 'port': 5021},
    'IOSv': {'host': '92.81.55.146', 'port': 5012},
}


class SelfDiagnose:
    """Class to handle self-diagnosis of network devices"""

    def __init__(self, host: str, port: int, device_name: str = None):
        """Initialize SelfDiagnose with device connection parameters"""
        self.host = host
        self.port = port
        self.device_name = device_name
        self.golden_config_path = f'golden_running_config_{self.device_name}.txt'
        self.current_config_path = f'current_running_config_{self.device_name}.txt'

    def compare_configs(self, golden_config: str, current_config: str) -> dict:
        """Compare two configuration files and return missing configuration blocks"""
        missing_blocks = {
            'hostname': [],
            'dhcp': [],
            'dhcp excluded': [],
            'interfaces': [],
            'router_ospf': [],
            'access_list': [],
            'username': [],
            'ip_domain': [],
            'line': []
        }

        with ParseConfig(golden_config) as old_config, ParseConfig(current_config) as new_config:
            old_config.reduce_config()
            new_config.reduce_config()

            for line in old_config.lines:
                if line.startswith("hostname "):
                    if line not in new_config.lines:
                        missing_blocks['hostname'].append(line.strip())

                elif line.startswith("username "):
                    if line not in new_config.lines:
                        missing_blocks['username'].append(line.strip())

                elif line.startswith("ip domain"):
                    if line not in new_config.lines:
                        missing_blocks['ip_domain'].append(line.strip())

                elif line.startswith("ip dhcp excluded"):
                    if line not in new_config.lines:
                        missing_blocks['dhcp excluded'].append(line.strip())

                elif line.startswith("ip dhcp pool "):
                    block = old_config.get_config_block(line.strip())
                    block_in_new = new_config.get_config_block(line.strip())
                    if not block_in_new or block != block_in_new:
                        missing_blocks['dhcp'].append(block)

                elif line.startswith("interface "):
                    block = old_config.get_config_block(line.strip())
                    if self._is_configured_interface(block):
                        block_in_new = new_config.get_config_block(line.strip())
                        if not block_in_new or block != block_in_new:
                            missing_blocks['interfaces'].append(block)

                elif line.startswith("router ospf"):
                    block = old_config.get_config_block(line.strip())
                    block_in_new = new_config.get_config_block(line.strip())
                    if not block_in_new or block != block_in_new:
                        missing_blocks['router_ospf'].append(block)

                elif line.startswith("ip access-list"):
                    block = old_config.get_config_block(line.strip())
                    block_in_new = new_config.get_config_block(line.strip())
                    if not block_in_new or block != block_in_new:
                        missing_blocks['access_list'].append(block)

                elif line.startswith(("line vty", "line con")):
                    block = old_config.get_config_block(line.strip())
                    block_in_new = new_config.get_config_block(line.strip())
                    if not block_in_new or block != block_in_new:
                        missing_blocks['line'].append(block)

        return missing_blocks

    def _is_configured_interface(self, block: str) -> bool:
        """Check if interface has meaningful configuration (not just shutdown)"""
        lines = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith('!')]
        for line in lines:
            if line.startswith(('ip address', 'ip ospf', 'description', 'switchport')):
                return True
        return False

    async def run_self_diagnose(self, dev_name):
        """Run the complete self-diagnose process"""
        print("Restoring to default settings...")
        conn = TelnetConnection(self.host, self.port)
        await conn.connect()
        await conn.get_running_config(self.golden_config_path)
        with ParseConfig(self.golden_config_path) as config:
            config.reduce_config()
            config.rewrite_file()
        await conn.erase_and_reload()
        if dev_name == "IOSv":
            time.sleep(50)
        print("Diagnosing...")
        time.sleep(5)
        conn = TelnetConnection(self.host, self.port)
        await conn.connect()
        await conn.initialize()
        await conn.get_running_config(self.current_config_path)
        missing_blocks = self.compare_configs(self.golden_config_path, self.current_config_path)
        if missing_blocks:
            print("Restoring to original settings...")
            await conn.apply_missing_config(missing_blocks)
            print("Configuration restored successfully!")
        else:
            print("Device configuration is already correct!")


async def run_device_diagnose(device_name, device_info):
    """Run self-diagnose for a single device"""
    print(f"\n=== Self-diagnose for {device_name} ===")
    diagnose = SelfDiagnose(device_info['host'], device_info['port'], device_name)
    await diagnose.run_self_diagnose(device_name)

async def main():
    """Main function to run self-diagnose"""
    for device_name, device_info in DEVICES.items():
        await run_device_diagnose(device_name, device_info)


if __name__ == '__main__':
    asyncio.run(main())
