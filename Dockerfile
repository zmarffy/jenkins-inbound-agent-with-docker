FROM jenkins/inbound-agent

COPY --from=docker /usr/local/bin/docker /usr/local/bin/
USER root
RUN apt-get update \
    && apt-get install -y sshpass curl lftp rsync openssh-server \
    && rm -rf /var/lib/apt/lists/*
USER jenkins
