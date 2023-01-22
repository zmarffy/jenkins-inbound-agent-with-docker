import argparse
import getpass
import json
import socket
import typing
import uuid
import xml.etree.ElementTree as ET

import docker
import requests
from fabric import Connection

if typing.TYPE_CHECKING:
    import docker.models.containers


def run_command_in_docker_container(
    docker_container: docker.models.containers.Container,
    cmd: str,
    environment: typing.Optional[dict] = None,
    acceptable_exit_codes: typing.Optional[list[int]] = None,
) -> str:
    """Run a command in a Docker container.

    Args:
        docker_container (docker.models.containers.Container): The container to run the command in.
        cmd (str): The command to run.
        environment (typing.Optional[dict], optional): Environment variables for the command. Defaults to None.
        acceptable_exit_codes (typing.Optional[list[int]], optional): Throw an error if the exit code of the command is not in this list. If None, use [0]. Defaults to None.

    Raises:
        ValueError: If the command returns an unacceptable exit code.

    Returns:
        str: The command output.
    """
    if acceptable_exit_codes is None:
        acceptable_exit_codes = [0]

    result = docker_container.exec_run(cmd, environment=environment)
    if result.exit_code not in acceptable_exit_codes:
        raise ValueError(f"Bad exit code for command {cmd}")
    return result.output.decode().strip()


def jenkins_request(
    session: requests.Session,
    url: str,
    username: str,
    password: str,
    crumb: str,
    method: str = "GET",
    params: typing.Optional[dict] = None,
    data: typing.Optional[dict] = None,
    raise_for_status: bool = True,
) -> requests.Response:
    """Perform a request to a Jenkins server

    Args:
        session (requests.Session): The requests Session object
        url (str): The URL to hit
        username (str): The Jenkins username to use
        password (str): The Jenkins password to use
        crumb (str): The Jenkins crumb needed for the request
        method (str, optional): The HTTP method to use. Defaults to "GET".
        params (typing.Optional[dict], optional): Query params to pass. Defaults to None.
        data (typing.Optional[dict], optional): Form data to pass. Defaults to None.
        raise_for_status (bool, optional): If True, throw an error if the server returns a bad HTTP code. Defaults to True.

    Returns:
        requests.Response: The Response object resulting from the request
    """
    if params is None:
        params = {}
    if data is None:
        data = {}

    data["json"] = json.dumps(data)
    response = session.request(
        method,
        url,
        headers={"Jenkins-Crumb": crumb},
        auth=(username, password),
        params=params,
        data=data,
    )
    if raise_for_status:
        response.raise_for_status()
    return response


parser = argparse.ArgumentParser()

# Create
parser.add_argument(
    "--agent-description", help="Jenkins agent description (create only)"
)
parser.add_argument(
    "--agent-executors",
    default=1,
    type=int,
    help="number of executors for the agent (create only)",
)
parser.add_argument(
    "--agent-labels", nargs="*", help="Jenkins agent labels (create only)"
)

# Delete
parser.add_argument(
    "--delete", action="store_true", help="delete the specified agent (delete only)"
)

# All
parser.add_argument("jenkins_url", help="Jenkins controller URL")
parser.add_argument("agent_name", help="Jenkins agent name")
parser.add_argument("--jenkins-username", default="admin", help="Jenkins username")
parser.add_argument("--docker", action="store_true", help="add Docker support")
parser.add_argument("--ssh-docker-username", help="SSH username for Docker host")
parser.add_argument("--ssh-docker-host", help="hostname for Docker host")
parser.add_argument(
    "--ssh-docker-port", default=22, help="port for SSH for Docker host"
)
args = parser.parse_args()

if args.ssh_docker_username is None:
    SSH_DOCKER_USERNAME = getpass.getuser()
else:
    SSH_DOCKER_USERNAME = args.ssh_docker_username
if args.ssh_docker_host is None:
    SSH_DOCKER_HOST = socket.gethostname()
else:
    SSH_DOCKER_HOST = args.ssh_docker_host
JENKINS_URL = args.jenkins_url.removesuffix("/")
DOCKER_HOST = f"{SSH_DOCKER_USERNAME}@{SSH_DOCKER_HOST}"
DOCKER_HOST_STRING = f"ssh://{DOCKER_HOST}:{args.ssh_docker_port}"
DOCKER_HOST_PASSWORD = getpass.getpass("Docker host SSH password: ")
JENKINS_USERNAME = args.jenkins_username
JENKINS_PASSWORD = getpass.getpass("Jenkins password: ")
DOCKER_CLIENT = docker.DockerClient(base_url=DOCKER_HOST_STRING)
CONTAINER_NAME = f"jenkins-agent_{args.agent_name}"
SESSION = requests.Session()
JENKINS_CRUMB = SESSION.get(
    f"{JENKINS_URL}/crumbIssuer/api/json", auth=(JENKINS_USERNAME, JENKINS_PASSWORD)
).json()["crumb"]

if not args.delete:
    create_json = {
        "name": args.agent_name,
        "nodeDescription": args.agent_description,
        "numExecutors": str(args.agent_executors),
        "remoteFS": "/home/jenkins/agent",
        "labelString": " ".join(args.agent_labels),
        "mode": "NORMAL",
        "": ["hudson.slaves.JNLPLauncher", "0"],
        "launcher": {
            "stapler-class": "hudson.slaves.JNLPLauncher",
            "$class": "hudson.slaves.JNLPLauncher",
            "workDirSettings": {
                "disabled": False,
                "workDirPath": "",
                "internalDir": "remoting",
                "failIfWorkDirIsMissing": False,
            },
            "webSocket": False,
            "tunnel": "",
            "oldCommand": "",
        },
        "retentionStrategy": {
            "stapler-class": "hudson.slaves.RetentionStrategy$Always",
            "$class": "hudson.slaves.RetentionStrategy$Always",
        },
        "nodeProperties": {"stapler-class-bag": "true"},
        "type": "hudson.slaves.DumbSlave",
        "Jenkins-Crumb": JENKINS_CRUMB,
    }
    jenkins_request(
        SESSION,
        f"{JENKINS_URL}/computer/doCreateItem",
        JENKINS_USERNAME,
        JENKINS_PASSWORD,
        JENKINS_CRUMB,
        method="POST",
        params={"name": args.agent_name, "type": "hudson.slaves.DumbSlave"},
        data=create_json,
    )
    out = jenkins_request(
        SESSION,
        f"{JENKINS_URL}/computer/{args.agent_name}/slave-agent.jnlp",
        JENKINS_USERNAME,
        JENKINS_PASSWORD,
        JENKINS_CRUMB,
    )
    print(f"Created Jenkins agent {args.agent_name}")
    secret = ET.fromstring(out.text).find("application-desc/argument")
    if secret is None:
        raise ValueError("Agent secret not found in Jenkins API response")
    secret = secret.text

    environment = {}
    if args.docker:
        environment.update(
            {
                "DOCKER_HOST": DOCKER_HOST_STRING,
            }
        )

    DOCKER_CLIENT.images.build(
        path=".", tag="jenkins-inbound-agent-with-docker", rm=True, quiet=False
    )

    container: docker.models.containers.Container = DOCKER_CLIENT.containers.create(
        "jenkins-inbound-agent-with-docker",
        name=CONTAINER_NAME,
        environment=environment,
        command=["-url", JENKINS_URL, secret, args.agent_name],
        network="host",
        cgroupns="host",
        hostname=str(uuid.uuid4()).replace("-", ""),
    )  # type: ignore

    container.start()
    print(f"Created container {CONTAINER_NAME}")

    if args.docker:
        run_command_in_docker_container(container, 'mkdir "/home/jenkins/.ssh"')
        run_command_in_docker_container(
            container,
            '/bin/sh -c \'ssh-keygen -t ed25519 -C "$HOSTNAME" -f "/home/jenkins/.ssh/id_rsa" -N ""\'',
        )
        run_command_in_docker_container(
            container,
            '/bin/sh -c \'sshpass -e ssh-copy-id -o StrictHostKeyChecking=accept-new -p "$SSH_DOCKER_PORT" "$DOCKER_H"\'',
            environment={
                "SSHPASS": DOCKER_HOST_PASSWORD,
                "SSH_DOCKER_PORT": args.ssh_docker_port,
                "DOCKER_H": DOCKER_HOST,
            },
        )
        run_command_in_docker_container(container, "docker ps")
        print(f"Added Docker support for container {CONTAINER_NAME}")
else:
    jenkins_request(
        SESSION,
        f"{JENKINS_URL}/manage/computer/{args.agent_name}/doDelete",
        JENKINS_USERNAME,
        JENKINS_PASSWORD,
        JENKINS_CRUMB,
        method="POST",
    )
    print("Deleted agent from Jenkins")
    container: docker.models.containers.Container = DOCKER_CLIENT.containers.get(CONTAINER_NAME)  # type: ignore
    container_has_docker_support = bool(
        run_command_in_docker_container(
            container, "printenv DOCKER_HOST", acceptable_exit_codes=[0, 1]
        )
    )
    container_hostname = run_command_in_docker_container(container, "hostname")
    container.remove(force=True)
    print(f"Removed container {CONTAINER_NAME}")
    if container_has_docker_support:
        docker_host_ssh_conn = Connection(
            SSH_DOCKER_HOST,
            user=SSH_DOCKER_USERNAME,
            port=args.ssh_docker_port,
            connect_kwargs={"password": DOCKER_HOST_PASSWORD},
        )
        docker_host_ssh_conn.run(
            f"sed -i'.bak' '/{container_hostname}/d' \"$HOME/.ssh/authorized_keys\""
        )
        print("Removed container from Docker host's authorized_keys file")
