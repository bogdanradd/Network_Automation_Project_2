"""This module represents a connector for telnet connections"""

import asyncio
import re
import time
import telnetlib3


def render_commands(templates, **kwargs):
    """This method is used to render commands and format them"""
    return [str(t).format(**kwargs) for t in templates]


class TelnetConnection:
    """This class is used to take care of the telnet connection"""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    def __enter__(self):
        return self

    async def connect(self):
        """This method is used to connect through telnet and return the reader and writer"""
        self.reader, self.writer = await telnetlib3.open_connection(self.host, self.port)

    async def readuntil(self, separator: str):
        """This method is used to read until command is received"""
        response = await self.reader.readuntil(separator.encode())
        return response.decode()

    async def read(self, n: int):
        """This method is used to read n bytes"""
        return await self.reader.read(n)

    def write(self, data: str):
        """This method is used to send commands in CLI"""
        self.writer.write(data + '\n')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write('\n')

    async def execute_commands(self, command: list, prompt):
        """This method is used to execute certain sets of commands in CLI"""
        output = []
        time.sleep(3)
        self.write('\r')
        time.sleep(3)
        self.write('\r')
        time.sleep(3)
        init_prompt = await self.read(n=10000)
        if '>' in init_prompt:
            self.write('en')
            out = await self.readuntil('#')
            output.append(out)
        for cmd in command:
            self.write(cmd)
            out = await self.readuntil(prompt)
            output.append(out)
        return output

    async def configure_ssh(self, templates, prmt, **kwargs):
        """This method is used to configure SSH on devices"""
        commands = render_commands(templates, **kwargs)
        return await self.execute_commands(commands, prmt)

    async def initialize(self):
        """This method is used to initialize CSR"""
        self.write('\r')
        time.sleep(2)
        self.write('\r')
        time.sleep(2)
        out = await self.read(n=10000)
        if 'dialog? [yes/no]' in out:
            self.write('no')
            time.sleep(2)
            out = await self.read(n=1000)
        if 'autoinstall? [yes]' in out:
            self.write('')
        time.sleep(30)

    async def get_running_config(self, output_file: str):
        """Extract running configuration from device"""
        time.sleep(2)
        self.write('\r')
        time.sleep(3)
        prompt = await self.read(n=20000)
        if '>' in prompt:
            self.write('en')
            time.sleep(2)
            await self.read(n=5000)
        self.write('terminal length 0')
        time.sleep(2)
        await self.read(n=5000)
        self.write('show running-config')
        time.sleep(5)
        out = await self.read(n=50000)
        lines = out.split('\n')
        config_lines = []
        in_config = False
        for line in lines:
            if 'Current configuration' in line or 'Building configuration' in line:
                in_config = True
                continue
            if in_config:
                stripped = line.strip()
                if stripped and stripped.endswith('#') and not stripped.startswith('!'):
                    if len(stripped.split()) == 1:
                        break
                config_lines.append(line)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(config_lines))
        return output_file

    async def erase_and_reload(self):
        """Erase startup configuration and reload the device"""
        self.write('\r')
        time.sleep(1)
        await self.read(n=500)
        self.write('erase startup-config')
        time.sleep(1)
        await self.readuntil('[confirm]')
        self.write('\r')
        time.sleep(1)
        await self.read(n=1000)
        self.write('reload')
        time.sleep(4)
        out = await self.read(n=15000)
        if '[yes/no]:' in out:
            self.write('no')
            time.sleep(1)
            out = await self.read(n=10000)
        if '[confirm]' in out:
            self.write('')
        time.sleep(20)

    def _get_indent_level(self, line: str):
        """Get the indentation level of a line"""
        return len(line) - len(line.lstrip())

    async def apply_config_block(self, block: str):
        """Apply a configuration block based on indentation"""
        lines = [l for l in block.splitlines() if l.strip() and not l.strip().startswith('!')]
        if not lines:
            return
        is_interface_block = lines[0].strip().startswith('interface ')
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped == 'shutdown':
                continue
            filtered_lines.append(line)
        lines = filtered_lines
        current_indent = 0
        for line in lines:
            line_indent = self._get_indent_level(line)
            stripped_line = line.strip()
            if line_indent < current_indent:
                exits_needed = (current_indent - line_indent) // 1
                for _ in range(exits_needed):
                    self.write('exit')
                    time.sleep(0.3)
                    await self.read(n=1000)
            self.write(stripped_line)
            time.sleep(0.3)
            await self.read(n=1000)
            current_indent = line_indent
        if is_interface_block and current_indent > 0:
            self.write('no shutdown')
            time.sleep(0.3)
            await self.read(n=1000)
        while current_indent > 0:
            self.write('exit')
            time.sleep(0.3)
            await self.read(n=1000)
            current_indent -= 1

    async def apply_missing_config(self, missing_blocks: dict):
        """Apply missing configuration blocks to restore the device"""
        if not any(missing_blocks.values()):
            return

        self.write('conf t')
        time.sleep(1)
        await self.readuntil('(config)#')

        for hostname_line in missing_blocks['hostname']:
            self.write(hostname_line)
            time.sleep(0.3)
            await self.readuntil('(config)#')

        for username_line in missing_blocks['username']:
            self.write(username_line)
            time.sleep(0.3)
            await self.readuntil('(config)#')

        for domain_line in missing_blocks['ip_domain']:
            self.write(domain_line)
            time.sleep(0.3)
            await self.readuntil('(config)#')

        for dhcp_block in missing_blocks['dhcp']:
            await self.apply_config_block(dhcp_block)

        for dhcp_excluded_line in missing_blocks['dhcp excluded']:
            self.write(dhcp_excluded_line)
            time.sleep(0.3)
            await self.readuntil('(config)#')

        for interface_block in missing_blocks['interfaces']:
            await self.apply_config_block(interface_block)

        for ospf_block in missing_blocks['router_ospf']:
            await self.apply_config_block(ospf_block)

        for acl_block in missing_blocks['access_list']:
            await self.apply_config_block(acl_block)

        for line_block in missing_blocks['line']:
            await self.apply_config_block(line_block)

        self.write('end')
        time.sleep(1)
        await self.readuntil('#')

    async def configure_ftd(self, hostname, ip, netmask, gateway, password):
        """This method is used to configure FTD initial setup"""
        self.write('')
        time.sleep(1)
        out = await self.read(n=1000)
        time.sleep(1)
        result = re.search(r'^\s*(?P<login>firepower login:)', out)
        if result.group('login'):
            self.write('admin')
            time.sleep(1)
            self.write('Admin123')
            time.sleep(5)

        out = await self.read(n=1000)
        time.sleep(1)
        if 'Press <ENTER> to display the EULA: ' in out:
            self.write('')
            while True:
                time.sleep(1)
                out = await self.read(n=1000)
                if '--More--' in out:
                    self.write(' ')
                elif "Please enter 'YES' or press <ENTER> to AGREE to the EULA: " in out:
                    self.write('')
                    time.sleep(3)
                    out = await self.read(n=1000)
                    break
                else:
                    print('No string found in output')

        if 'password:' in out:
            self.write(password)
            time.sleep(3)
            out = await self.read(n=1000)
            if 'password:' in out:
                self.write(password)
                time.sleep(5)
                out = await self.read(n=1000)

        if 'IPv4? (y/n) [y]:' in out:
            self.write('')
            time.sleep(1)
            out = await self.read(n=1000)
        if 'IPv6? (y/n) [n]:' in out:
            self.write('')
            time.sleep(1)
            out = await self.read(n=1000)
        if '[manual]:' in out:
            self.write('')
            time.sleep(1)
            out = await self.read(n=1000)
        if '[192.168.45.45]:' in out:
            self.write(ip)
            time.sleep(1)
            out = await self.read(n=1000)
        if '[255.255.255.0]:' in out:
            self.write(netmask)
            time.sleep(1)
            out = await self.read(n=1000)
        if '[192.168.45.1]:' in out:
            self.write(gateway)
            time.sleep(1)
            out = await self.read(n=1000)
        if '[firepower]:' in out:
            self.write(hostname)
            time.sleep(1)
            out = await self.read(n=1000)
        if '::35]:' in out:
            self.write(gateway)
            time.sleep(1)
            out = await self.read(n=1000)
        if "'none' []:" in out:
            self.write('')
            time.sleep(15)
            out = await self.read(n=1000)
        if 'Manage the device locally? (yes/no) [yes]:' in out:
            self.write('')
            time.sleep(15)
