#!/usr/bin/env bash

set -e

. /build-support/shell/common/log.sh


if [ -z "${USERNAME}" ]
then
    error "Must set USERNAME environment variable"
    exit 1
fi

sudo -Hiu $USERNAME bash -c '${HOME}/.local/bin/pipx install poetry'
sudo -Hiu $USERNAME bash -c '${HOME}/.local/bin/pipx inject poetry poetry-plugin-export'
