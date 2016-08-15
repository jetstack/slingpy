from tools import memoized
from infra_provider import InfraProvider
from provider import Command
from cloud import AWSPlugin, DigitaloceanPlugin
import sys
import subprocess
import os
import json
import copy


class TerraformInfraProvider(InfraProvider):
    _clouds = []

    def __init__(self):
        super(TerraformInfraProvider, self).__init__()

        self._clouds = [
            AWSPlugin(self),
            DigitaloceanPlugin(self),
        ]

        for name in ['apply', 'destroy', 'plan', 'graph']:
            self.commands[name] = Command(
                name,
                cmd=getattr(self, name),
                params=True,
                results=False,
                persist=['terraform/terraform.tfstate']
            )
        self.commands['apply']._results = True

    @property
    @memoized
    def cloud(self):
        for cloud in self._clouds:
            if cloud.detect():
                self.log.info("cloud '%s' detected" % cloud.name)
                return cloud
            else:
                self.log.debug("cloud no '%s' detected" % cloud.name)

        self.log.fatal("no cloud detected")
        sys.exit(1)

    def variables(self):
        output = {
            'cluster_name':
            self.parameters['general']['cluster']['name'],
            'ssh_pub_key':
            self.parameters['general']['authentication']['ssh']['pubKey']
        }

        for machine_type, machine in \
                self.parameters['general']['cluster']['machines'].iteritems():
            output['%s_type' % machine_type] = machine['instanceType']
            output['%s_count' % machine_type] = machine['count']

        output.update(self.cloud.variables())

        return output

    def terraform_configure(self):
        self.log.info("variables: %s" % self.variables())
        path = os.path.join(self.terraform_cwd(), 'terraform.tfvars')
        content = []

        for key, value in self.variables().iteritems():
            if type(value) == int or type(value) == str:
                l = '%s = "%s"' % (key, value)
            elif type(value) == list:
                l = '%s = "%s"' % (key, ','.join(value))
            else:
                continue
            content.append(l)

        for line in content:
            self.log.debug('tfvars: %s' % line)

        self.write_to_file(path, '\n'.join(content))

    def terraform_args(self):
        return [
            '-state=../terraform.tfstate',
        ]

    def terraform_cwd(self):
        return os.path.abspath('terraform/%s' % self.cloud.name)

    def terraform_exec(self, cmd):
        self.terraform_configure()

        commands = [
            'terraform'
        ] + cmd + self.terraform_args()

        return subprocess.call(
            commands,
            cwd=self.terraform_cwd()
        )

    def terraform_output(self):
        commands = [
            'terraform',
            'output',
            '-json'
        ] + self.terraform_args()

        proc = subprocess.Popen(
            commands,
            cwd=self.terraform_cwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = proc.communicate()
        exitcode = proc.returncode

        if exitcode != 0:
            self.log.fatal("Retrieving terraform output failed: %s" % err)
            sys.exit(1)

        return json.loads(out)

    def apply(self):
        self.terraform_exec(['apply'])
        self.output_write()

    def destroy(self):
        self.terraform_exec(['destroy', '-force'])

    def plan(self):
        self.terraform_exec(['plan'])

    def graph(self):
        self.terraform_exec(['graph'])

    def output(self):
        output = copy.deepcopy(self.parameters)
        self.cloud.output(output)
        return output
        pass

    def output_write(self):
        path = self.output_file_path
        content = self.yaml(self.output())
        self.log.info("write output '%s'" % path)
        self.log.debug("\n%s", content)
        self.write_to_file(path, content)

    pass
