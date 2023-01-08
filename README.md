# jenkins-inbound-agent-with-docker-provisioner

Warning: I didn't design this with security in mind. There is no warranty. I have no idea what I am doing, etc.

This repo provides a Dockerfile as well as the scripts you need to get an inbound agent with Docker support connected to Jenkins.

## Requirements

- Python >= 3.8
- Docker
- The stuff in `requirements.txt`

## Usage

```text
usage: jenkins-inbound-agent-with-docker-provisioner.py [-h] [--agent-description AGENT_DESCRIPTION] [--agent-executors AGENT_EXECUTORS] [--agent-labels [AGENT_LABELS ...]] [--delete]
                                                        [--jenkins-username JENKINS_USERNAME] [--docker] [--ssh-docker-username SSH_DOCKER_USERNAME] [--ssh-docker-host SSH_DOCKER_HOST]
                                                        [--ssh-docker-port SSH_DOCKER_PORT]
                                                        jenkins_url agent_name

positional arguments:
  jenkins_url           Jenkins controller URL
  agent_name            Jenkins agent name

options:
  -h, --help            show this help message and exit
  --agent-description AGENT_DESCRIPTION
                        Jenkins agent description (create only)
  --agent-executors AGENT_EXECUTORS
                        number of executors for the agent (create only)
  --agent-labels [AGENT_LABELS ...]
                        Jenkins agent labels (create only)
  --delete              delete the specified agent (delete only)
  --jenkins-username JENKINS_USERNAME
                        Jenkins username
  --docker              add Docker support
  --ssh-docker-username SSH_DOCKER_USERNAME
                        SSH username for Docker host
  --ssh-docker-host SSH_DOCKER_HOST
                        hostname for Docker host
  --ssh-docker-port SSH_DOCKER_PORT
                        port for SSH for Docker host
```

## Notes

- You must have SSH password auth enabled on the Docker host before running this, so that the container is automatically able to log in and drop off its key (this is unnecessary and subject to change)
- You must have SSH key auth enabled on the Docker host in order to use it, as Docker over SSH does not accept password auth
