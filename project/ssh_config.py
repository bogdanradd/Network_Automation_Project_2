"""SSH commands"""
commands = [
    "\n",
    "conf t",
    "int {interface}",
    'ip address {ip} {sm}',
    "no shutdown",
    "exit",
    'hostname {hostname}',
    'ip domain name {domain}',
    'username {username} password {password}',
    'username {username} privilege 15',
    'crypto key generate rsa modulus 2048',
    'line vty 0 4',
    'login local',
    'transport input ssh',
    'exit',
    'ip ssh version 2',
    'end',

]
