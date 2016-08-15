import yaml


def generic_yaml():
    return yaml.load("""
general:
  authentication:
    ssh:
      user: root
      privateKey: |
        -----BEGIN RSA PRIVATE KEY-----
        SECRET
        -----END RSA PRIVATE KEY-----
      pubKey: ssh-rsa AAAA
  cluster:
    name: slingshot-aws
    kubernetes:
      masterApiPort: 443
      version: 1.3.4
      serviceNetwork: 10.245.0.0/16
      dns:
        replicas: 1
        domainName: cluster.local
      networking: flannel
      flannel:
        subnet: 172.16.0.0
        prefix: 16
        hostPrefix: 24
      addons:
        clusterLogging: false
        clusterMonitoring: false
        kubeUI: false
        kubeDash: false
    machines:
      master:
        count: 1
        cores: 1
        memory: 512
        instanceType: m3.medium
        roles:
        - master
      worker:
        count: 2
        cores: 2
        memory: 1024
        instanceType: t2.large
        roles:
        - worker
inventory: []
""")
