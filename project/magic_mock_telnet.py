"""Unit tests for async telnet connector"""
import unittest
import warnings
from unittest.mock import MagicMock, patch, AsyncMock

warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)


class TestCase(unittest.TestCase):
    """Test cases for async telnet connection"""

    @patch('lib.connectors.async_telnet_conn.telnetlib3.open_connection')
    def test_connect(self, telnet_mock):
        """Test telnet connect method"""
        import asyncio
        from lib.connectors.async_telnet_conn import TelnetConnection
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        telnet_mock.return_value = (mock_reader, mock_writer)
        conn = TelnetConnection('10.10.10.10', 23)
        asyncio.run(conn.connect())
        telnet_mock.assert_called_once_with('10.10.10.10', 23)
        self.assertEqual(mock_reader, conn.reader)
        self.assertEqual(mock_writer, conn.writer)

    @patch('lib.connectors.async_telnet_conn.telnetlib3.open_connection')
    def test_readuntil(self, telnet_mock):
        """Test telnet readuntil method"""
        import asyncio
        from lib.connectors.async_telnet_conn import TelnetConnection
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_reader.readuntil = AsyncMock(return_value=b'Router#')
        telnet_mock.return_value = (mock_reader, mock_writer)
        conn = TelnetConnection('10.10.10.10', 23)
        conn.reader = mock_reader
        conn.writer = mock_writer
        result = asyncio.run(conn.readuntil('#'))
        mock_reader.readuntil.assert_called_once_with(b'#')
        self.assertEqual('Router#', result)

    @patch('lib.connectors.async_telnet_conn.telnetlib3.open_connection')
    def test_write(self, telnet_mock):
        """Test telnet write method"""
        from lib.connectors.async_telnet_conn import TelnetConnection
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        telnet_mock.return_value = (mock_reader, mock_writer)
        conn = TelnetConnection('10.10.10.10', 23)
        conn.reader = mock_reader
        conn.writer = mock_writer
        conn.write('show ip interface brief')
        mock_writer.write.assert_called_once_with('show ip interface brief\n')

    def test_render_commands(self):
        """Test render_commands helper function"""
        from lib.connectors.async_telnet_conn import render_commands
        templates = ['interface {iface}', 'ip address {ip} {mask}', 'no shutdown']
        result = render_commands(templates, iface='GigabitEthernet0/0', ip='10.0.0.1', mask='255.255.255.0')
        self.assertEqual([
            'interface GigabitEthernet0/0',
            'ip address 10.0.0.1 255.255.255.0',
            'no shutdown'
        ], result)

    @patch('lib.connectors.async_telnet_conn.telnetlib3.open_connection')
    def test_read(self, telnet_mock):
        """Test telnet read method"""
        import asyncio
        from lib.connectors.async_telnet_conn import TelnetConnection
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_reader.read = AsyncMock(return_value=b'Sample output')
        telnet_mock.return_value = (mock_reader, mock_writer)
        conn = TelnetConnection('10.10.10.10', 23)
        conn.reader = mock_reader
        conn.writer = mock_writer
        result = asyncio.run(conn.read(1024))
        mock_reader.read.assert_called_once_with(1024)
        self.assertEqual(b'Sample output', result)
