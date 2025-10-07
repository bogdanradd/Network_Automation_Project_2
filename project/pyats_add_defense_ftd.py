"""
This test will configure defence against Attacker.
"""
from bravado.exception import HTTPError
from pyats import aetest, topology
from lib.connectors.swagger_conn import SwaggerConnector




class CommonSetup(aetest.CommonSetup):
    """This class is used as a general class. It contains every method used to configure FTD defence policies."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tb = None
        self.dev = None
        self._swagger_conn = None

    def ensure_swagger_connection(self):
        """Ensure a SwaggerConnector is available for the firewall device and return it."""
        if self._swagger_conn is not None:
            return self._swagger_conn

        for device in self.tb.devices:
            dev = self.tb.devices[device]
            if dev.custom.role != 'firewall':
                continue
            if "swagger" not in dev.connections:
                continue

            connection: SwaggerConnector = dev.connect(via='swagger')
            swagger = connection.get_swagger_client()
            if not swagger:
                self.failed('No swagger connection')
            self._swagger_conn = connection
            return self._swagger_conn

    @aetest.subsection
    def load_testbed(self, steps):
        """This method loads the testbed that provides details about whole topology."""
        with steps.start("Load testbed"):
            self.tb = topology.loader.load('main_testbed.yaml')
        self.parent.parameters.update(tb=self.tb)

    @aetest.subsection
    def add_attacker_rule(self, steps):
        """This method is used to add a rule against Attacker, so it denies every attack targeting 192.168.205.0/24"""
        with steps.start("Add rule against attacker on FTD"):
            connection = self.ensure_swagger_connection()
            try:
                deny_rule = connection.add_attacker_rule(cidrs=['192.168.201.0/24', '192.168.205.0/24'])
                print(deny_rule)
                connection.add_allow_rule(inside_interface='inside', outside_interface='outside')
            except HTTPError as e:
                print('Could not add rule against attacker on FTD', e)

    @aetest.subsection
    def swagger_deploy(self, steps):
        """This method is being used to deploy actual configuration on FTD"""
        with steps.start("Deploy FTD configuration"):
            connection = self.ensure_swagger_connection()
            try:
                connection.deploy()
            except HTTPError:
                print('Deployment failed')


if __name__ == '__main__':
    aetest.main()
