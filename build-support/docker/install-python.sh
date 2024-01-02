#!/usr/bin/env bash

set -e

. /build-support/shell/common/log.sh


if [ -z "${PYTHON_VERSIONS}" ]
then
    error "Must set PYTHON_VERSIONS environment variable"
    exit 1
fi

if [ -z "${USERNAME}" ]
then
    error "Must set USERNAME environment variable"
    exit 1
fi

# See: https://github.com/pyenv/pyenv/wiki#suggested-build-environment
info "Installing asdf Python plugin and specified Python version"
apk add --no-cache \
    build-base \
    bzip2-dev \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    linux-headers \
    openssl-dev \
    readline-dev \
    sqlite-dev \
    zlib-dev

sudo -Hiu $USERNAME bash -c '${HOME}/.asdf/bin/asdf plugin add python'
for PYTHON_VERSION in $PYTHON_VERSIONS
do
    sudo -Hiu $USERNAME bash -c "\${HOME}/.asdf/bin/asdf install python ${PYTHON_VERSION} 2>/dev/null"
done
sudo -Hiu $USERNAME bash -c "\${HOME}/.asdf/bin/asdf global python ${PYTHON_VERSIONS}"
