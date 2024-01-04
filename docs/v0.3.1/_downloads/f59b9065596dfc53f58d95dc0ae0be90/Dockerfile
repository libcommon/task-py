# Base, language-agnostic image with Bash shell and new user
FROM alpine:latest AS base

ARG UID
ARG USERNAME

# Update base packages
RUN apk update && \
    apk upgrade

# Add Bash
# Used as shell for new user.
RUN apk add --no-cache bash

# Copy common shell scripts
COPY build-support/shell/common/ /build-support/shell/common/
COPY build-support/shell/run/ /build-support/shell/run/

# Create new user
# This user is used to run all user-specified commands
# in the container, and the UID/USERNAME should match
# the local (host) user to ensure file permissions of generated
# or touched files are correct.
COPY build-support/docker/adduser.sh /tmp/build-support/docker/adduser.sh
RUN UID=$UID \
    USERNAME=$USERNAME \
    /tmp/build-support/docker/adduser.sh

# Base image for using Python and Poetry
# Uses the asdf-vm project to manage Python and Poetry installation
FROM base AS python_base

# Default Python version to use
ARG DEFAULT_PYTHON_VERSION
# Python versions to instal with asdf
ARG PYTHON_VERSIONS
# Must match USERNAME in base image
ARG USERNAME

# Install asdf
COPY build-support/docker/install-asdf.sh /tmp/build-support/docker/install-asdf.sh
RUN USERNAME=$USERNAME \
    /tmp/build-support/docker/install-asdf.sh

# Install specified Python versions with asdf
COPY build-support/docker/install-python.sh /tmp/build-support/docker/install-python.sh
RUN USERNAME=$USERNAME PYTHON_VERSIONS=$PYTHON_VERSIONS DEFAULT_PYTHON_VERSION=$DEFAULT_PYTHON_VERSION \
    /tmp/build-support/docker/install-python.sh

# Install pipx
COPY build-support/docker/install-pipx.sh /tmp/build-support/docker/install-pipx.sh
RUN USERNAME=$USERNAME \
    /tmp/build-support/docker/install-pipx.sh

# Install Poetry
COPY build-support/docker/install-poetry.sh /tmp/build-support/docker/install-poetry.sh
RUN USERNAME=$USERNAME \
    /tmp/build-support/docker/install-poetry.sh

RUN rm -rf /tmp/build-support/

FROM python_base as build

ENTRYPOINT ["./run.sh"]

CMD ["build"]
