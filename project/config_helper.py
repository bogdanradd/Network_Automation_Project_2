"""Configuration parser helper module"""
import re

class ParseConfig:
    """Parse and manipulate network device configurations"""

    def __init__(self, path: str):
        self.path = path
        self.lines = []

    def __enter__(self):
        with open(self.path, 'r', encoding='utf-8') as file:
            for line in file.readlines():
                self.lines.append(line)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lines.clear()

    def get_config_block(self, start: str):
        """Extract a configuration block starting from a given line"""
        out = []
        block_start = False

        for line in self.lines:
            if line.startswith(start):
                block_start = True
                out.append(line)
                continue
            if block_start:
                if line and not line.startswith(' '):
                    break
                out.append(line)

        if block_start and out:
            return ''.join(out)
        return None

    def reduce_config(self):
        """Remove unnecessary configuration lines"""
        self.lines = list(filter(lambda line: not line.startswith('!'), self.lines))

    def rename_interfaces(self, old_int_pattern: str, new_int: str, new_index: int):
        """Rename interfaces in configuration using regex pattern"""
        def generator(new_interface, start_index):
            i = start_index
            while i < 10:
                yield f'{new_interface}{i}'
                i += 1
        interface_generator = generator(new_int, new_index)
        self.lines = list(map(lambda x: re.sub(old_int_pattern, lambda _: next(interface_generator), x), self.lines))

    def rewrite_file(self):
        """Rewrite the configuration file with current lines"""
        with open(self.path, 'w', encoding='utf-8') as file:
            for line in self.lines:
                file.write(line)

if __name__ == '__main__':
    with ParseConfig('../hw/iou1_running_config.txt') as config_file1:
        print(config_file1.get_config_block('interface Ethernet0/3'))
        print(''.join(config_file1.lines) + '\n')
        config_file1.reduce_config()
        print('Config without "!": \n' + ''.join(config_file1.lines))
        config_file1.rename_interfaces(r'Ethernet1\/.', 'GigabitEthernet0/', 0)
        print('Config with renamed interfaces: \n' + ''.join(config_file1.lines))
