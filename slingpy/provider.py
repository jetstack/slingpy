from tools import memoized
import logging
import yaml
import os
import sys


class Command(object):
    parameters_file_path = os.path.abspath('parameters.yaml')
    output_file_path = os.path.abspath('output.yaml')
    _name = None
    _type = None
    _params = False
    _results = False
    _persist = []
    _cmd = None

    def __init__(
        self,
        name,
        cmd,
        ctype='docker',
        params=False,
        results=False,
        persist=[]
    ):
        self._name = name
        self._cmd = cmd
        self._type = ctype
        self._params = params
        self._results = results
        self._persist = persist

    def discover(self):
        spec = {
            'type': 'docker',
            'execs': [[self._name]]
        }
        if self._params is True:
            spec['parameterFile'] = os.path.basename(self.parameters_file_path)
        if self._results is True:
            spec['resultFile'] = os.path.basename(self.output_file_path)

        if len(self._persist) > 0:
            spec['persistPaths'] = self._persist

        return spec


class Provider(object):
    provider_type = None
    commands = {}

    def __init__(self, ptype):
        self.provider_type = ptype
        self.commands['discover'] = Command('discover', cmd=self.discover)

    @property
    @memoized
    def parameters(self):
        with open(self.parameters_file_path, 'r') as stream:
            self.my_parameters = yaml.load(stream)
            self.log.info(
                "read parameters from '%s'" % self.parameters_file_path
            )
            return self.my_parameters

    @property
    @memoized
    def log(self):
        l = logging.getLogger(__name__)
        l.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        l.addHandler(ch)
        self.my_log = l
        return self.my_log

    def custom_param(self, key):
        return self.parameters['custom'][key]

    def yaml(self, obj):
        Dumper = yaml.SafeDumper
        Dumper.ignore_aliases = lambda self, data: True
        return yaml.dump(obj, Dumper=Dumper, default_flow_style=False)

    def write_to_file(self, path, content):
        dir_path = os.path.dirname(path)
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)

        with open(path, 'w') as stream:
            stream.write(content)

    def discover(self):
        cmds = dict([
            (cmd._name, cmd.discover())
            for cmd in self.commands.values()
        ])
        print(self.yaml({
            'provider': {
                'version': 1,
                'type': self.provider_type,
            },
            'commands': cmds,
        }))

    def command(self, argv):
        if len(argv) < 2:
            print("Please specify an command ./%s <%s>" % (
                argv[0],
                '|'.join(self.commands.keys())
            ))
            sys.exit(1)
        cmd = argv[1]
        try:
            cmd_dict = self.commands[cmd]
            cmd_dict._cmd()
        except KeyError:
            print("Unknown command '%s'" % cmd)
            sys.exit(1)
