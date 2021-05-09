# jenkins-inbound-agent-with-docker

This repo provides a Dockerfile as well as the scripts you need to get an inbound agent with Docker support connected to Jenkins. It also supports protecting the Docker daemon required to be exposed with a cert.

This was made for macOS and presumably works with Linux, but if you are using Linux, you may as well expose the Docker socket rather than run a `socat` container. Therefore, maybe this isn't for Linux users.

**TL;DR:** This helps set up your macOS or Linux computer to be a Jenkins node that has Docker support.

## Requirements

- Python >= 3.6 (I really did not feel like writing the argument stuff in Bash; sorry)
- `docker` (a `pip` package)
- Docker (the actual Docker program)

## Instructions (No SSL)

1. Create a new Jenkins node in your Jenkins UI
2. Switch to the source directory and run `create-jenkins-inbound-agent.py` on the machine that will host the Jenkins inbound agent. Its arguments are as such

    ```text
    create-jenkins-inbound-agent.py secret name url
    ```

## Instructions (SSL)

1. Create a new Jenkins node in your Jenkins UI
2. Switch to the source directory and run `make-certs.sh` on the machine that will host the Jenkins inbound agent
3. Run `create-jenkins-inbound-agent.py` on the machine that will host the Jenkins inbound agent. Its arguments are as such.

    ```text
    create-jenkins-inbound-agent.py [-h] [--server_cert SERVER_CERT] [--server_key SERVER_KEY] [--ca CA] [--cert CERT] [--key KEY] secret name url
    ```

    All of those cert files generated from `make-certs.sh` are under `~/.docker/ssl`, if you're wondering what args to pass

Note that you can run this creation script with certs generated from somewhere else, not the wack "everything self-signed" model that I provide in `make-certs.sh`. Think about doing that maybe

## Do I need this

Probably not, if you're aking that question. You might need it if you want to have a Mac do your work for CI/CD processes.
