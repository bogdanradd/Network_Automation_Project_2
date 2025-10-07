"""Add dhcp pool commands"""
dhcp_commands = [
    'ip dhcp pool GUEST',
    'network {guest_nw} {guest_sm}',
    'default-router {guest_gw}',
    'exit',
    'ip dhcp excluded-address 192.168.201.1 192.168.201.99',
    'end'
]
