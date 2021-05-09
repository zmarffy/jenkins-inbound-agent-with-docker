FROM jenkins/inbound-agent

COPY --from=docker /usr/local/bin/docker /usr/local/bin/
USER root
RUN mkdir /usr/local/.docker/
USER jenkins