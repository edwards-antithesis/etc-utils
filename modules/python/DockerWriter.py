"""
    Modules to quickly write docker-compose.yaml files for use.

    These modules rely on yaml configurations that you pass in as an
    argument.
"""
from ruamel import yaml


class ClientWriter(object):
    """
    Generic client class to write services to docker-compose
    Just use this template and add your entrypoint in child class.
    """

    def __init__(self, global_config, client_config, name, curr_node):
        self.global_config = global_config
        self.client_config = client_config
        # used when we have multiple of the same client.
        self.curr_node = curr_node
        # constants.
        self.name = name
        self.image = self.client_config["image"]
        self.tag = self.client_config["tag"]
        self.network_name = self.global_config["docker"]["network-name"]
        self.volumes = [str(x) for x in self.global_config["docker"]["volumes"]]

    # inits for child classes.
    def config(self):
        return {
            "image": f"{self.image}:{self.tag}",
            "volumes": self.volumes,
            "networks": self._networking(),
        }

    def get_config(self):
        config = self.config()
        if self.client_config["debug"]:
            config["entrypoint"] = "/bin/bash"
            config["tty"] = True
            config["stdin_open"] = True
        else:
            config["entrypoint"] = self._entrypoint()
        return config

    def _networking(self):
        # first calculate the ip.
        return {self.network_name: {"ipv4_address": self.get_ip()}}

    def get_ip(self):
        prefix = ".".join(self.client_config["ip-start"].split(".")[:3]) + "."
        base = int(self.client_config["ip-start"].split(".")[-1])
        skip = self.curr_node * int(self.global_config["universal"]["ip-skip"])
        ip = prefix + str(base + skip)
        return ip

    def _entrypoint(self):
        raise Exception("over-ride this method")


class GethClientWriter(ClientWriter):
    def __init__(self, global_config, client_config, curr_node):
        super().__init__(
            global_config, client_config, f"geth-node-{curr_node}", curr_node
        )
        self.out = self.config()

    def _entrypoint(self):
        """
        ./launch-geth <datadir> <genesis.json> <network_id> <http port> <http apis> <ws_port> <ws_apis>
        """
        return [
            "/data/scripts/launch-geth.sh",
            str(self.global_config["pow-chain"]["files"]["docker-geth-data-dir"]),
            str(self.global_config["pow-chain"]["files"]["docker-eth1-genesis-file"]),
            str(self.client_config["network-id"]),
            str(self.client_config["http-port"]),
            str(self.client_config["http-apis"]),
            str(self.client_config["ws-port"]),
            str(self.client_config["ws-apis"]),
        ]

class PrysmClientWriter(ClientWriter):
    def __init__(self, global_config, client_config, curr_node):
        super().__init__(
            global_config, client_config, f"prysm-node-{curr_node}", curr_node
        )
        self.out = self.config()

    def _entrypoint(self):
        """
        ./launch-prysm <datadir> <node-id> <ip-address> <pow-port>
        TODO: bootnodes.
        """
        return [
            "/data/scripts/launch-prysm.sh",
            str(self.client_config["docker-testnet-dir"]),
            str(self.curr_node),
            str(self.get_ip()),
            str(self.client_config["pow-port"]),
        ]

class DockerComposeWriter(object):
    """
    Class to create the actual docker-compose.yaml file.
    """

    def __init__(self, global_config):
        self.global_config = global_config
        self.yml = self._base()

    def _base(self):
        return {
            "services": {},
            "networks": {
                self.global_config["docker"]["network-name"]: {
                    "driver": "bridge",
                    "ipam": {
                        "config": [
                            {"subnet": self.global_config["docker"]["ip-subnet"]}
                        ]
                    },
                }
            },
        }

    def add_services(self):
        """
        POW services + POS services.
        for now POW is geth.
        """
        curr_node = 0
        geth_config = self.global_config["pow-chain"]["geth"]
        for n in range(geth_config["num-nodes"]):
            gcw = GethClientWriter(self.global_config, geth_config, curr_node)
            self.yml["services"][gcw.name] = gcw.get_config()
            curr_node += 1

        prysm_config = self.global_config['pos-chain']['clients']['prysm']
        for n in range(prysm_config['num-nodes']):
            pcw = PrysmClientWriter(self.global_config, prysm_config, curr_node)
            self.yml["services"][pcw.name] = pcw.get_config()
            curr_node += 1

    def write_to_file(self, out_file):
        with open(out_file, "w") as f:
            yaml.dump(self.yml, f)


def create_docker_compose(global_config, out_file):
    dcw = DockerComposeWriter(global_config)
    dcw.add_services()
    dcw.write_to_file(out_file)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", dest="config", help="path to config to consume")
    parser.add_argument(
        "--out", dest="out", help="path to write the generated docker-compose.yaml"
    )

    args = parser.parse_args()

    with open(args.config, "r") as f:
        global_config = yaml.safe_load(f.read())

    create_docker_compose(global_config, args.out)
