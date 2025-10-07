"""Unit tests for SSH connector"""
import unittest
import warnings
from unittest.mock import MagicMock, patch

warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)


class TestCase(unittest.TestCase):
    """Test cases for SSH connection"""

    @patch('lib.connectors.ssh_conn.ConnectHandler')
    def test_connect(self, connect_handler_mock):
        """Test SSH connect method"""
        from lib.connectors.ssh_conn import SSHConnection
        mock_conn = MagicMock()
        connect_handler_mock.return_value = mock_conn
        conn = SSHConnection('10.10.10.10', 22, 'admin', 'password123')
        conn.connect()
        connect_handler_mock.assert_called_once_with(
            device_type='cisco_ios',
            host='10.10.10.10',
            port=22,
            username='admin',
            password='password123'
        )
        self.assertEqual(mock_conn, conn.conn)

    @patch('lib.connectors.ssh_conn.ConnectHandler')
    def test_configure(self, connect_handler_mock):
        """Test SSH configure method"""
        from lib.connectors.ssh_conn import SSHConnection
        mock_conn = MagicMock()
        mock_conn.send_config_set.return_value = 'Config applied successfully'
        connect_handler_mock.return_value = mock_conn
        conn = SSHConnection('10.10.10.10', 22, 'admin', 'password123')
        conn.connect()
        templates = ['interface {interface}', 'ip address {ip} {mask}']
        result = conn.configure(templates, interface='GigabitEthernet0/1', ip='192.168.1.1', mask='255.255.255.0')
        mock_conn.send_config_set.assert_called_once_with([
            'interface GigabitEthernet0/1',
            'ip address 192.168.1.1 255.255.255.0'
        ])
        self.assertEqual('Config applied successfully', result)

    @patch('lib.connectors.ssh_conn.ConnectHandler')
    def test_close(self, connect_handler_mock):
        """Test SSH close method"""
        from lib.connectors.ssh_conn import SSHConnection
        mock_conn = MagicMock()
        connect_handler_mock.return_value = mock_conn
        conn = SSHConnection('10.10.10.10', 22, 'admin', 'password123')
        conn.connect()
        conn.close()
        mock_conn.disconnect.assert_called_once()
        self.assertIsNone(conn.conn)

    def test_render_commands(self):
        """Test render_commands helper function"""
        from lib.connectors.ssh_conn import render_commands
        templates = ['hostname {name}', 'interface {iface}', 'no shutdown']
        result = render_commands(templates, name='Router1', iface='Ethernet0')
        self.assertEqual(['hostname Router1', 'interface Ethernet0', 'no shutdown'], result)
