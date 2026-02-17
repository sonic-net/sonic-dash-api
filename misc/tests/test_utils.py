import os
import sys
try:
    import importlib.util
    import importlib.machinery
    use_importlib = True
except ImportError:
    import imp
    use_importlib = False
import json
from click.testing import CliRunner


def load_source(modname, filename):
    loader = importlib.machinery.SourceFileLoader(modname, filename)
    spec = importlib.util.spec_from_file_location(modname, filename, loader=loader)
    module = importlib.util.module_from_spec(spec)
    # The module is always executed and not cached in sys.modules.
    # Uncomment the following line to cache the module.
    # sys.modules[module.__name__] = module
    loader.exec_module(module)
    return module


misc_folder = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(misc_folder, "pypkg"))
if use_importlib:
    utils_cli = load_source(
        "utils_cli",
        os.path.join(misc_folder, "dash_api_utils"))
else:
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
 "vm_vni": 4321,
 "local_region_id": 100,
 "outbound_direction_lookup": "dst_mac",
 "trusted_vnis_list": [
  {
   "value": 100
  }
 ]
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
