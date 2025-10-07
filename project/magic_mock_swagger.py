"""Unit tests for swagger connector"""
import unittest
import warnings
from unittest.mock import MagicMock, patch

warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)


class TestCase(unittest.TestCase):
    """Test cases for swagger connection"""

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_connect(self, post_mock):
        """Test swagger connect method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        result = conn.connect()

        self.assertTrue(conn.connected)
        self.assertEqual(conn, result)
        self.assertEqual('https://10.10.10.10:443', conn._url)
        self.assertIsNotNone(conn._headers)
        self.assertEqual('application/json', conn._headers['Content-Type'])
        self.assertEqual('application/json', conn._headers['Accept'])
        self.assertEqual('Bearer test_access_token', conn._headers['Authorization'])
        post_mock.assert_called_once()
        call_args = post_mock.call_args
        self.assertEqual('https://10.10.10.10:443/api/fdm/latest/fdm/token', call_args.kwargs['url'])

    @patch('lib.connectors.swagger_conn.requests.post')
    @patch('lib.connectors.swagger_conn.SwaggerClient.from_url')
    def test_get_swagger_client(self, swagger_client_mock, post_mock):
        """Test get_swagger_client method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_client = MagicMock()
        swagger_client_mock.return_value = mock_client
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()
        result = conn.get_swagger_client()
        self.assertEqual(mock_client, result)
        self.assertEqual(mock_client, conn.client)
        swagger_client_mock.assert_called_once()
        call_args = swagger_client_mock.call_args
        self.assertEqual('https://10.10.10.10:443/apispec/ngfw.json', call_args.kwargs['spec_url'])

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_finish_initial_setup(self, post_mock):
        """Test finish_initial_setup method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()
        mock_client = MagicMock()
        mock_client.InitialProvision.addInitialProvision.return_value.result.return_value = {'status': 'success'}
        conn.client = mock_client
        result = conn.finish_initial_setup()
        mock_client.InitialProvision.addInitialProvision.assert_called_once()
        call_args = mock_client.InitialProvision.addInitialProvision.call_args
        expected_body = {
            "type": "initialprovision",
            "id": "default",
            "acceptEULA": True,
            "startTrialEvaluation": True,
            "selectedPerformanceTierId": "FTDv5",
        }
        self.assertEqual(expected_body, call_args.kwargs['body'])
        self.assertEqual({'status': 'success'}, result)

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_deploy(self, post_mock):
        """Test deploy method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()
        mock_client = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.id = 'deploy_123'
        mock_deployment.state = 'DEPLOYED'
        mock_deployment.statusMessage = 'Deployment successful'
        mock_client.Deployment.addDeployment.return_value.result.return_value = mock_deployment
        mock_client.Deployment.getDeployment.return_value.result.return_value = mock_deployment
        conn.client = mock_client
        conn.deploy()
        mock_client.Deployment.addDeployment.assert_called_once_with(body={"forceDeploy": True})
        mock_client.Deployment.getDeployment.assert_called_once_with(objId='deploy_123')

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_delete_existing_dhcp_sv(self, post_mock):
        """Test delete_existing_dhcp_sv method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()
        mock_client = MagicMock()

        mock_dhcp_server = MagicMock()
        mock_dhcp_server.id = 'dhcp_123'
        mock_dhcp_server.servers = [MagicMock()]

        mock_list_response = MagicMock()
        mock_list_response.result.return_value = {'items': [mock_dhcp_server]}
        mock_client.DHCPServerContainer.getDHCPServerContainerList.return_value = mock_list_response
        mock_client.DHCPServerContainer.editDHCPServerContainer.return_value.result.return_value = {'status': 'success'}
        conn.client = mock_client

        result = conn.delete_existing_dhcp_sv()
        mock_client.DHCPServerContainer.getDHCPServerContainerList.assert_called_once()
        mock_client.DHCPServerContainer.editDHCPServerContainer.assert_called_once()
        call_args = mock_client.DHCPServerContainer.editDHCPServerContainer.call_args
        self.assertEqual('dhcp_123', call_args.kwargs['objId'])
        self.assertEqual([], call_args.kwargs['body'].servers)
        self.assertEqual({'status': 'success'}, result)

    @patch('lib.connectors.swagger_conn.requests.post')
    def test_configure_ftd_interfaces(self, post_mock):
        """Test configure_ftd_interfaces method"""
        from lib.connectors.swagger_conn import SwaggerConnector
        post_mock.return_value = MagicMock(json=MagicMock(return_value={
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'token_type': 'Bearer'
        }))
        mock_device = MagicMock()
        mock_device.connections.swagger.ip = '10.10.10.10'
        mock_device.connections.swagger.port = 443
        mock_device.connections.swagger.protocol = 'https'
        mock_device.connections.telnet.credentials.login.username = 'admin'
        mock_device.connections.telnet.credentials.login.password.plaintext = 'password123'
        conn = SwaggerConnector(mock_device)
        conn.connect()

        mock_client = MagicMock()
        mock_interface1 = MagicMock()
        mock_interface1.hardwareName = 'GigabitEthernet0/0'
        mock_interface1.id = 'if1_id'
        mock_interface2 = MagicMock()
        mock_interface2.hardwareName = 'GigabitEthernet0/1'
        mock_interface2.id = 'if2_id'

        mock_list_response = MagicMock()
        mock_list_response.result.return_value = {'items': [mock_interface1, mock_interface2]}
        mock_client.Interface.getPhysicalInterfaceList.return_value = mock_list_response
        mock_client.Interface.editPhysicalInterface.return_value.result.return_value = {'status': 'success'}
        conn.client = mock_client

        interface1 = MagicMock()
        interface1.name = 'GigabitEthernet0/0'
        interface1.alias = 'outside'
        interface1.ipv4.ip.compressed = '192.168.1.1'
        interface1.ipv4.netmask.exploded = '255.255.255.0'

        interface2 = MagicMock()
        interface2.name = 'GigabitEthernet0/1'
        interface2.alias = 'inside'
        interface2.ipv4.ip.compressed = '192.168.2.1'
        interface2.ipv4.netmask.exploded = '255.255.255.0'

        result = conn.configure_ftd_interfaces(interface1, interface2)
        mock_client.Interface.getPhysicalInterfaceList.assert_called_once()
        self.assertEqual(2, mock_client.Interface.editPhysicalInterface.call_count)
        self.assertEqual(2, len(result))

        all_calls = mock_client.Interface.editPhysicalInterface.call_args_list
        first_call = all_calls[0]
        second_call = all_calls[1]

        self.assertIn(first_call.kwargs['objId'], ['if1_id', 'if2_id'])
        self.assertEqual('192.168.1.1', first_call.kwargs['body'].ipv4.ipAddress.ipAddress)
        self.assertEqual('255.255.255.0', first_call.kwargs['body'].ipv4.ipAddress.netmask)
        self.assertEqual('outside', first_call.kwargs['body'].name)
        self.assertTrue(first_call.kwargs['body'].enable)

        self.assertIn(second_call.kwargs['objId'], ['if1_id', 'if2_id'])
        self.assertEqual('192.168.2.1', second_call.kwargs['body'].ipv4.ipAddress.ipAddress)
        self.assertEqual('255.255.255.0', second_call.kwargs['body'].ipv4.ipAddress.netmask)
        self.assertEqual('inside', second_call.kwargs['body'].name)
        self.assertTrue(second_call.kwargs['body'].enable)
