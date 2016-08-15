import unittest
import mock
import generic
import yaml
import logging
from slingpy import TerraformInfraProvider


def example_output(self):
    return {
        u'master_public_ips': {
            u'sensitive': False,
            u'type': u'string',
            u'value': u'178.62.44.51'
        },
        u'master_private_ips': {
            u'sensitive': False,
            u'type': u'string',
            u'value': u'10.131.12.189'
        },
        u'master_floating_ip': {
            u'sensitive': False,
            u'type': u'string',
            u'value': u'139.59.200.249'
        },
        u'worker_private_ips': {
            u'sensitive': False,
            u'type': u'string',
            u'value': u'10.131.24.79,10.131.23.219'
        },
        u'master_hostnames': {
            u'sensitive': False,
            u'type': u'string',
            u'value': u'kube-slingshot-do-master-1'
        },
        u'worker_public_ips': {
            u'sensitive': False,
            u'type': u'string',
            u'value': u'178.62.59.210,178.62.57.249'
        },
        u'worker_floating_ip': {
            u'sensitive': False,
            u'type': u'string',
            u'value': u'139.59.200.244'
        },
        u'worker_hostnames': {
            u'sensitive': False,
            u'type': u'string',
            u'value':
            u'kube-slingshot-do-worker-1,kube-slingshot-do-worker-2'
        }
    }


def mock_params(custom):
    params = generic.generic_yaml()
    params['general']['cluster']['name'] = 'slingshot-digitalocean'
    params['general']['cluster']['machines']['master']['instanceType'] = '1gb'
    params['general']['cluster']['machines']['worker']['instanceType'] = '2gb'
    params['custom'] = custom
    return mock.mock_open(
        read_data=yaml.dump(params)
    )


def aws_zones(self):
    return ['eu-west-1a', 'eu-west-1b', 'eu-west-1c']


class TestAwsTerraform(unittest.TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

    @mock.patch("__builtin__.open", mock_params({
        'digitalocean_token': 'digitalocean_token1',
    }))
    def test_terraform_configure_minmal(self):
        ip = TerraformInfraProvider()
        vars = ip.variables()
        self.assertEqual(vars['token'], 'digitalocean_token1')
        self.assertEqual(vars['region'], 'lon1')
        self.assertEqual(vars['master_type'], '1gb')
        self.assertEqual(vars['master_count'], 1)
        self.assertEqual(vars['worker_type'], '2gb')
        self.assertEqual(vars['worker_count'], 2)
        self.assertEqual(vars['cluster_name'], 'slingshot-digitalocean')

    @mock.patch("__builtin__.open", mock_params({
        'digitalocean_token': 'digitalocean_token1',
    }))
    @mock.patch(
        (
            'slingpy.terraform_infra_provider.'
            'TerraformInfraProvider.terraform_output'
        ),
        example_output,
    )
    def test_terraform_output(self):
        ip = TerraformInfraProvider()
        output = ip.output()
        self.assertEqual(len(output['inventory']), 3)
