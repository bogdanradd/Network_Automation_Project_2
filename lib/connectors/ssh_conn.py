"""This module represents the connector for SSH connections"""

from netmiko import ConnectHandler


def render_commands(templates, **kwargs):
    """This method is used to render commands and format them"""
    return [str(t).format(**kwargs) for t in templates]


class SSHConnection:
    """This class is used to take care of the SSH connections"""

    def __init__(self, host, port, username, password, device_type='cisco_ios'):
        self.device_type = device_type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.conn = None

    def connect(self):
        """This method is used to connect to the device via SSH"""
        self.conn = ConnectHandler(
            device_type=self.device_type,
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )

    def configure(self, templates, **kwargs):
        """This method is used to send sets of commands to the device"""
        commands = render_commands(templates, **kwargs)
        return self.conn.send_config_set(commands)

    def close(self):
        """This method is used to close the SSH connection"""
        if self.conn:
            try:
                self.conn.disconnect()
            finally:
                self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
