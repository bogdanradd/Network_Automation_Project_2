"""This module displays a menu and interacts with the user"""

import sys
import subprocess
import pathlib
import unittest
import asyncio
from pings_and_attacks import run_ping_1, run_ping_2, run_nmap, run_dos, ping_and_dos, test_all_ssh_acl, run_all_pings
from check_pylint import run
from self_diagnose import SelfDiagnose, DEVICES


def configure_devices():
    """This method runs the pyats script that configures the devices"""
    script = pathlib.Path("/tmp/pycharm_project_844/project/pyats_configure_devices.py")
    subprocess.run([sys.executable, str(script)], check=False)


def configure_ftd_defence():
    """This method runs the pyats script that configures FTD defence policies"""
    script = pathlib.Path("/tmp/pycharm_project_844/project/pyats_add_defense_ftd.py")
    subprocess.run([sys.executable, str(script)], check=False)


def run_connector_unittests():
    """This method runs all unittest files for connectors"""
    print("\n" + "="*70)
    print("Running Connector Unit Tests")
    print("="*70 + "\n")

    loader = unittest.TestLoader()
    suite = loader.discover('/tmp/pycharm_project_844/project', pattern='magic_mock_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


def run_self_diagnose():
    """This method runs self-diagnose on a selected router"""
    print("\nAvailable routers:")
    for device_name in DEVICES:
        print(f"  - {device_name}")

    router = input("\nEnter router name (IOU1 or IOSv): ").strip()

    if router not in DEVICES:
        print(f"Error: '{router}' is not a valid router. Please choose IOU1 or IOSv.")
        return

    device_info = DEVICES[router]
    print(f"\n=== Starting self-diagnose for {router} ===")
    diagnose = SelfDiagnose(device_info['host'], device_info['port'], router)
    asyncio.run(diagnose.run_self_diagnose(router))


def display_menu():
    """This method displays the menu and calls the desired function"""
    while True:
        print("""
        ############### MENU ###############\n
        1) Configure devices
        2) Run PINGS from Automation to every IP in the topology
        3) Run PING from Automation to Guest
        4) Run PING from Attacker to Guest
        5) Run NMAP from Attacker to Guest
        6) Run DOS from Attacker to Guest
        7) Run 3) and 6) at the same time
        8) Add defence policies on FTD
        9) Test SSH ACLS made on IOU1, IOSv and CSR
        10) Self-diagnose router
        11) Run Pylint
        12) Run unittests for connectors
        0) Exit
        ############### MENU ###############
        """)

        choice = input("Enter your choice: ").strip()

        if choice == '1':
            try:
                configure_devices()
            except Exception as e:
                print('Configuration script failed', e)
        elif choice == '2':
            try:
                run_all_pings()
            except Exception as e:
                print('Failed to send PINGS', e)
        elif choice == '3':
            try:
                run_ping_1()
            except Exception as e:
                print('Failed to send PING', e)
        elif choice == '4':
            try:
                run_ping_2()
            except Exception as e:
                print('Failed to send PING', e)
        elif choice == '5':
            try:
                run_nmap()
            except Exception as e:
                print('Failed to send NMAP', e)
        elif choice == '6':
            try:
                run_dos()
            except Exception as e:
                print('Failed to send DOS', e)
        elif choice == '7':
            try:
                ping_and_dos()
            except Exception as e:
                print('Failed to run PING and DOS', e)
        elif choice == '8':
            try:
                configure_ftd_defence()
            except Exception as e:
                print('Failed to configure FTD defence', e)
        elif choice == '9':
            try:
                test_all_ssh_acl()
            except Exception as e:
                print('Failed to test SSH ACLs', e)
        elif choice == '10':
            try:
                run_self_diagnose()
            except Exception as e:
                print('Failed to run self-diagnose', e)
        elif choice == '11':
            try:
                run('project', '../project')
                run('lib/connectors', '../lib/connectors')
            except Exception as e:
                print('Failed to run Pylint', e)
        elif choice == '12':
            try:
                run_connector_unittests()
            except Exception as e:
                print('Failed to run unittests', e)
        elif choice == '0':
            break


if __name__ == '__main__':
    display_menu()
