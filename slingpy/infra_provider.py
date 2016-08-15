from provider import Provider
import os


class InfraProvider(Provider):
    parameters_file_path = os.path.abspath('parameters.yaml')
    output_file_path = os.path.abspath('output.yaml')

    def __init__(self):
        super(InfraProvider, self).__init__("infra")

    def output(self):
        p = self.parameters
        p['inventory'] = self.inventory()
        p['custom']['aws_secret_key'] = '-removed-'
        elb_dns = self.terraform_output('master_elb_dns_name')
        bastion_eip = self.terraform_output('bastion_instance_eip')
        p['general']['cluster']['kubernetes']['masterApiUrl'] = \
            "https://%s" % elb_dns
        p['general']['cluster']['kubernetes']['masterApiUrlExternal'] = \
            "https://%s" % bastion_eip
        p['general']['cluster']['kubernetes']['masterSan'] = [
            elb_dns,
            bastion_eip
        ]
        p['general']['cluster']['kubernetes']['cloudProvider'] = 'aws'

        if self.flocker_enabled():
            for key in ['flocker_access_key', 'flocker_secret_key']:
                p['custom'][key] = self.terraform_output(key)

        return p

    def output_write(self):
        path = self.output_file_path
        content = self.yaml(self.output())
        self.log.info("write output '%s'" % path)
        self.log.debug("\n%s", content)
        self.write_to_file(path, content)
