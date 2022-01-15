import argparse
import os
import socket

import docker

ssl_args = [
    "server_cert",
    "server_key",
    "ca",
    "cert",
    "key"
]

parser = argparse.ArgumentParser()
for arg in ssl_args:
    parser.add_argument(f"--{arg}", type=os.path.abspath)
parser.add_argument("secret", help="Jenkins secret")
parser.add_argument("name", help="Jenkins agent name")
parser.add_argument("url", help="Jenkins master URL")
args = parser.parse_args()

one_ssl_arg_provided = False
ssl_arg_count = 0
for arg in ssl_args:
    if getattr(args, arg) is not None:
        one_ssl_arg_provided = True
        ssl_arg_count += 1
if one_ssl_arg_provided and ssl_arg_count != len(ssl_args):
    parser.error("Need to provide all SSL args or none")

DOCKER_CLIENT = docker.from_env()

DOCKER_CLIENT.images.build(
    path=".", tag="jenkins-inbound-agent-with-docker", rm=True, quiet=False)

# socat container
volumes = {
    "/var/run/docker.sock": {
        "bind": "/var/run/docker.sock",
        "mode": "ro"
    }
}
command = "openssl-listen:1234,fork,reuseaddr{} UNIX-CONNECT:/var/run/docker.sock"
if one_ssl_arg_provided:
    command = command.format(
        ",verify=1,cert=/certs/server_cert.pem,key=/certs/server_key.pem,cafile=/certs/ca.pem")
    volumes.update(
        {
            getattr(args, arg): {
                "bind": f"/certs/{arg}.pem",
                "mode": "ro"
            } for arg in ssl_args[0:3]
        }
    )
else:
    command = command.format("")
socat_container = DOCKER_CLIENT.containers.run(
    "alpine/socat",
    name="socat-docker-2376",
    detach=True,
    restart_policy={
        "Name": "always",
    },
    volumes=volumes,
    ports={
        '1234/tcp': (
            "0.0.0.0",
            2376
        )
    },
    command=command
)

# Jenkins agent container
command = ["-url", args.url, args.secret, args.name]
volumes = {}
environment = {
    "DOCKER_HOST": f"{socket.gethostname()}:2376",
}
if one_ssl_arg_provided:
    volumes.update(
        {
            getattr(args, arg): {
                "bind": f"/usr/local/.docker/{arg}.pem",
                "mode": "ro"
            } for arg in ssl_args[2:5]
        }
    )
    environment.update(
        {
            "DOCKER_TLS_VERIFY": "true",
            "DOCKER_CERT_PATH": "/usr/local/.docker/"
        }
    )
agent_container = DOCKER_CLIENT.containers.run(
    "jenkins-inbound-agent-with-docker",
    name="jenkins-agent-with-docker",
    detach=True,
    restart_policy={
        "Name": "always",
    },
    environment=environment,
    volumes=volumes,
    command=command
)

print(socat_container.id)
print(agent_container.id)
