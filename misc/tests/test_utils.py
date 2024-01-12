import os
import sys
import imp
import json
from click.testing import CliRunner

misc_folder = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(misc_folder, "pypkg"))
utils_cli = imp.load_source(
    "utils_cli",
    os.path.join(misc_folder, "dash_api_utils"))


def test_dash_api_utils():
    runner = CliRunner()
    result = runner.invoke(utils_cli.utils_cli, ['--help'])
    assert result.exit_code == 0

    runner = CliRunner()
    appliance_json_str = '''
{
 "sip": {
  "ipv4": 16777482
 },
 "vm_vni": 4321
}
    '''
    result = runner.invoke(utils_cli.utils_cli,
                           ['--to_proto', '-t', 'DASH_APPLIANCE_TABLE'],
                           input=appliance_json_str)
    assert result.exit_code == 0

    runner = CliRunner()
    appliance_binary = result.stdout_bytes
    result = runner.invoke(utils_cli.utils_cli,
                           ['--to_json', '-t', 'DASH_APPLIANCE_TABLE'],
                           input=appliance_binary)
    assert result.exit_code == 0
    assert json.loads(result.stdout) == json.loads(appliance_json_str)
