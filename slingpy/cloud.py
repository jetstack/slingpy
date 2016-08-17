import itertools
import boto3
import sys


class Plugin(object):
    _provider = None
    name = 'null'
    instance_types = []
    regions = []
    region_default = None
    required_params = []

    def __init__(self, provider):
        self._provider = provider

    def validate(self):
        pass

    def detect(self):
        keys = self._provider.parameters["custom"].keys()
        for key in self.required_params:
            if self.key(key) not in keys:
                return False
        return True

    def region(self):
        try:
            r = self.param('region').lower()
            if r not in self.regions:
                self._provider.log.fatal("Wrong region '%s'", r)
                sys.exit(1)
            return r
        except KeyError:
            return self.region_default
            pass

    def key(self, name):
        return '%s_%s' % (self.name, name)

    def param(self, name):
        return self._provider.custom_param(self.key(name))

    def is_valid_instance_type(self, value):
        if value in self.instance_types:
            return True
        return False

    def terraform_output(self, key):
        tf = self._provider.terraform_output()
        return tf[key]['value']

    def variables(self):
        output = {}

        for key in self.required_params:
            output[key] = self.param(key)

        return output

    def zones(self):
        try:
            z = self.param('zones').split(',')
            z_available = self.zones_available()

            if z_available is None:
                return z

            for zone in z:
                if zone not in z_available:
                    self._provider.log.fatal("Wrong zone '%s'", zone)
                    sys.exit(1)

            return z
        except KeyError:
            return self.zones_available()

    def zones_available(self):
        return None

    def output(self, output):
        return output


class AWSPlugin(Plugin):
    name = 'aws'
    required_params = [
        'access_key',
        'secret_key',
    ]
    instance_type_default = 'm3.medium'
    instance_types = [
        'c1.medium',
        'c1xlarge',
        'c3.2xlarge',
        'c3.4xlarge',
        'c3.8xlarge',
        'c3.large',
        'c3.xlarge',
        'c4.2xlarge',
        'c4.4xlarge',
        'c4.8xlarge',
        'c4.large',
        'c4.xlarge',
        'cc2.8xlarge',
        'cg1.4xlarge',
        'cr1.8xlarge',
        'd2.2xlarge',
        'd2.4xlarge',
        'd2.8xlarge',
        'd2.xlarge',
        'g2.2xlarge',
        'g2.8xlarge',
        'hi1.4xlarge',
        'hs1.8xlarge',
        'i2.2xlarge',
        'i2.4xlarge',
        'i2.8xlarge',
        'i2.xlarge',
        'm1.large',
        'm1.medium',
        'm1.small',
        'm1.xlarge',
        'm2.2xlarge',
        'm2.4xlarge',
        'm2.xlarge',
        'm3.2xlarge',
        'm3.large',
        'm3.medium',
        'm3.xlarge',
        'm4.10xlarge',
        'm4.2xlarge',
        'm4.4xlarge',
        'm4.large',
        'm4.xlarge',
        'r3.2xlarge',
        'r3.4xlarge',
        'r3.8xlarge',
        'r3.large',
        'r3.xlarge',
        't1.micro',
        't2.large',
        't2.medium',
        't2.micro',
        't2.nano',
        't2.small',
        'x1.32xlarge',
    ]
    region_default = 'eu-west-1'
    regions = [
        'us-east-1',
        'us-west-2',
        'us-west-1',
        'eu-west-1',
        'eu-central-1',
        'ap-southeast-1',
        'ap-northeast-1',
        'ap-southeast-2',
        'ap-northeast-2',
        'ap-south-1',
        'sa-east-1',
    ]

    @property
    def session(self):
        return boto3.Session(
            aws_access_key_id=self.param('access_key'),
            aws_secret_access_key=self.param('secret_key'),
            region_name=self.region(),
        )

    @property
    def ec2(self):
        return self.session.resource('ec2')

    @property
    def iam(self):
        return self.session.resource('iam')

    @property
    def client_autscaling(self):
        return self.session.client('autoscaling')

    @property
    def client_ec2(self):
        return self.session.client('ec2')

    def autoscaling_instances(self, name):
        result = self.client_autscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[
                name,
            ]
        )

        instances = []

        for instance in result['AutoScalingGroups'][0]['Instances']:
            instances.append(self.ec2.Instance(instance['InstanceId']))

        return instances

    def zones_available(self):
        zones = self.client_ec2.describe_availability_zones()
        return [
            zone['ZoneName']
            for zone in zones['AvailabilityZones']
            if zone['State'] == 'available'
        ]

    def variables(self):
        output = super(AWSPlugin, self).variables()

        output['region'] = self.region()
        output['zones'] = self.zones()
        if self.flocker_enabled():
            output['flocker_enabled'] = 1

        return output

    @property
    def worker_instances(self):
        return self.autoscaling_instances(
            self.terraform_output('worker_asg')
        )

    @property
    def bastion_instance(self):
        return self.ec2.Instance(self.terraform_output('bastion_instance_id'))

    @property
    def master_instances(self):
        return self.autoscaling_instances(
            self.terraform_output('master_asg')
        )

    def inventory_for_instance(self, i):
        inventory = {
            'name': i.id,
        }

        if i.public_ip_address is not None:
            inventory['publicIP'] = i.public_ip_address

        if i.private_ip_address is not None:
            inventory['privateIP'] = i.private_ip_address

        return inventory

    def inventory(self):
        inventory = []
        roles = ['master']
        for instance in self.master_instances:
            i = self.inventory_for_instance(instance)
            i['roles'] = roles
            inventory.append(i)

        roles = ['worker']
        for instance in self.worker_instances:
            i = self.inventory_for_instance(instance)
            i['roles'] = roles
            inventory.append(i)

        i = self.inventory_for_instance(self.bastion_instance)
        i['roles'] = ['bastion']
        inventory.append(i)

        return inventory

    def flocker_enabled(self):
        try:
            val = self._provider.custom_param('flocker_enabled')
            if val.lower() == 'true' or val == '1':
                return True
            else:
                return False
        except KeyError:
            return False

    def output(self, output):
        output['inventory'] = self.inventory()

        # remove secrets aws
        output['custom']['aws_secret_key'] = '-removed-'

        elb_dns = self.terraform_output('master_elb_dns_name')
        bastion_eip = self.terraform_output('bastion_instance_eip')

        k8soutput = output['general']['cluster']['kubernetes']

        k8soutput['masterApiUrl'] = "https://%s" % elb_dns
        k8soutput['masterApiUrlExternal'] = "https://%s" % bastion_eip
        k8soutput['masterSan'] = [
            elb_dns,
            bastion_eip
        ]

        k8soutput['cloudProvider'] = 'aws'

        if self.flocker_enabled():
            for key in ['flocker_access_key', 'flocker_secret_key']:
                output['custom'][key] = self.terraform_output(key)

        return output


class DigitaloceanPlugin(Plugin):
    name = 'digitalocean'
    instance_type = '1gb'
    required_params = [
        'token',
    ]
    instance_types = [
        '512mb',
        '1gb',
        '2gb',
        '4gb',
        '8gb',
        '16gb',
        '32gb',
        '48gb',
        '64gb',
    ]
    region_default = 'lon1'
    regions = [
        'ams1',
        'ams2',
        'ams3',
        'blr1',
        'fra1',
        'lon1',
        'nyc1',
        'nyc2',
        'nyc3',
        'sfo1',
        'sfo2',
        'sgp1',
        'tor1',
    ]

    def variables(self):
        output = super(DigitaloceanPlugin, self).variables()

        output['region'] = self.region()
        return output

    def machines_list(self, mtype):
        for i in itertools.count():
            output = {}
            for name in ['hostnames', 'private_ips', 'public_ips']:
                try:
                    output[name[:-1]] = self.terraform_output(
                        '%s_%s' % (mtype, name)
                    ).split(',')[i]
                except IndexError:
                    break
            else:
                yield output
                continue
            break

    def inventory(self):
        inventory = []
        for mtype, machine in self._provider\
                .parameters['general']['cluster']['machines'].iteritems():
            for data in self.machines_list(mtype):
                inventory.append({
                    'name': data['hostname'],
                    'roles': machine['roles'],
                    'publicIP': data['public_ip'],
                    'privateIP': data['private_ip'],
                })

        return inventory

    def output(self, output):
        output['inventory'] = self.inventory()

        k8soutput = output['general']['cluster']['kubernetes']

        master_ip = self.terraform_output('master_floating_ip')

        k8soutput['masterApiUrl'] = "https://%s" % master_ip
        k8soutput['masterApiUrlExternal'] = "https://%s" % master_ip

        k8soutput['masterSan'] = [
            master_ip,
        ] + self.terraform_output('master_public_ips').split(',')

        return output
