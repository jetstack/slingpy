import unittest
import mock
import generic
import yaml
import logging
import os
from slingpy import TerraformInfraProvider


def example_output(self):
    return {
        "bastion_instance_eip": {
            "sensitive": False,
            "type": "string",
            "value": "4.3.2.1"
        },
        "bastion_instance_id": {
            "sensitive": False,
            "type": "string",
            "value": "i-deadbeefcafebeef"
        },
        "bastion_instance_ip": {
            "sensitive": False,
            "type": "string",
            "value": "1.2.3.4"
        },
        "master_asg": {
            "sensitive": False,
            "type": "string",
            "value": "master-asg1"
        },
        "master_elb_dns_name": {
            "sensitive": False,
            "type": "string",
            "value": "master-elb1"
        },
        "worker_asg": {
            "sensitive": False,
            "type": "string",
            "value": "worker-asg1"
        }
    }


def example_output_flocker(self):
    output = example_output(self)
    output.update({
        "flocker_access_key": {
            "sensitive": False,
            "type": "string",
            "value": "flocker-access-key1"
        },
        "flocker_secret_key": {
            "sensitive": False,
            "type": "string",
            "value": "flocker-secret-key1"
        },
    })
    return output


def mock_params(custom):
    params = generic.generic_yaml()
    params['custom'] = custom
    return mock.mock_open(
        read_data=yaml.dump(params)
    )


def aws_zones(self):
    return ['eu-west-1a', 'eu-west-1b', 'eu-west-1c']


class TestAwsTerraform(unittest.TestCase):

    def setUp(self):
        if os.environ.get('DEBUG') is None:
            logging.disable(logging.CRITICAL)

    @mock.patch("__builtin__.open", mock_params({}))
    def test_terraform_configure_no_custom(self):
        ip = TerraformInfraProvider()
        with self.assertRaises(SystemExit):
            ip.variables()

    @mock.patch("__builtin__.open", mock_params({
        'aws_access_key': 'access_key1',
        'aws_secret_key': 'secret_key1',
    }))
    @mock.patch("slingpy.cloud.AWSPlugin.zones_available", aws_zones)
    def test_terraform_configure_minmal(self):
        ip = TerraformInfraProvider()
        vars = ip.variables()
        self.assertEqual(vars['access_key'], 'access_key1')
        self.assertEqual(vars['secret_key'], 'secret_key1')
        self.assertEqual(vars['region'], 'eu-west-1')
        self.assertEqual(vars['zones'], aws_zones(None))
        self.assertEqual(vars['master_type'], 'm3.medium')
        self.assertEqual(vars['master_count'], 1)
        self.assertEqual(vars['worker_type'], 't2.large')
        self.assertEqual(vars['worker_count'], 2)
        self.assertEqual(vars['cluster_name'], 'slingshot-aws')

    @mock.patch("__builtin__.open", mock_params({
        'aws_access_key': 'access_key1',
        'aws_secret_key': 'secret_key1',
        'aws_zones': 'eu-west-1a,eu-west-1b'
    }))
    @mock.patch("slingpy.cloud.AWSPlugin.zones_available", aws_zones)
    def test_terraform_configure_select_zones(self):
        ip = TerraformInfraProvider()
        vars = ip.variables()
        self.assertEqual(vars['zones'], ['eu-west-1a', 'eu-west-1b'])

    @mock.patch("__builtin__.open", mock_params({
        'aws_access_key': 'access_key1',
        'aws_secret_key': 'secret_key1',
        'aws_zones': 'us-east-1a'
    }))
    @mock.patch("slingpy.cloud.AWSPlugin.zones_available", aws_zones)
    def test_terraform_configure_wrong_zone(self):
        ip = TerraformInfraProvider()
        with self.assertRaises(SystemExit):
            ip.variables()

    @mock.patch("__builtin__.open", mock_params({
        'aws_access_key': 'access_key1',
        'aws_secret_key': 'secret_key1',
        'flocker_enabled': 'true'
    }))
    @mock.patch("slingpy.cloud.AWSPlugin.zones_available", aws_zones)
    def test_terraform_configure_flocker_enabled(self):
        ip = TerraformInfraProvider()
        vars = ip.variables()
        self.assertEqual(ip.cloud.flocker_enabled(), True)
        self.assertEqual(vars['flocker_enabled'], 1)

    @mock.patch("__builtin__.open", mock_params({
        'aws_access_key': 'access_key1',
        'aws_secret_key': 'secret_key1',
        'flocker_enabled': 'true'
    }))
    @mock.patch("slingpy.cloud.AWSPlugin.zones_available", aws_zones)
    @mock.patch("slingpy.cloud.AWSPlugin.inventory", lambda self: ['mocked'])
    @mock.patch(
        (
            'slingpy.terraform_infra_provider.'
            'TerraformInfraProvider.terraform_output'
        ),
        example_output_flocker,
    )
    def test_terraform_output_flocker_enabled(self):
        ip = TerraformInfraProvider()
        out = ip.output()
        self.assertEqual(ip.cloud.flocker_enabled(), True)
        self.assertEqual(
            out['custom']['flocker_access_key'],
            'flocker-access-key1',
        )
        self.assertEqual(
            out['custom']['flocker_secret_key'],
            'flocker-secret-key1',
        )
