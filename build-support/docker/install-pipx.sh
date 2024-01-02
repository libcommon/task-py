#!/usr/bin/env bash

set -e

. /build-support/shell/common/log.sh


if [ -z "${USERNAME}" ]
then
    error "Must set USERNAME environment variable"
    exit 1
fi

sudo -Hiu $USERNAME bash -c '. ${HOME}/.asdf/asdf.sh && python3 -m pip install -U pip wheel'
sudo -Hiu $USERNAME bash -c '. ${HOME}/.asdf/asdf.sh && python3 -m pip install -U --user pipx'
