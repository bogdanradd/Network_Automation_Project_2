"""Enable ospf commands"""
ospf_commands = [
    'router ospf 1',
    'exit',
    'interface {interface}',
    'ip ospf 1 area 0',
    'exit'
]
