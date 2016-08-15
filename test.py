import sys
from slingpy import TerraformInfraProvider


class InfraProvider(TerraformInfraProvider):
    pass


def main():
    ip = InfraProvider()
    ip.command(sys.argv)

if __name__ == "__main__":
    main()
