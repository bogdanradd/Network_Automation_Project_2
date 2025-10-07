"""ACL commands"""
acl_commands = [
    'ip access-list standard SSH',
    'permit host {ssh_container}',
    'deny any',
    'exit',
    'line vty 0 4',
    'access-class SSH in',
    'exit'
]
