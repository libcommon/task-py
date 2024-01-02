#!/usr/bin/env bash

set -e

. /build-support/shell/common/log.sh


if [ -z "${UID}" ]
then
    error "Must set the UID environment variable"
    exit 1
fi

if [ -z "${USERNAME}" ]
then
    error "Must set the USERNAME environment variable"
    exit 1
fi

apk add --no-cache sudo 

if ! ( getent passwd "${USERNAME}" )
then
    adduser \
        -h "/home/${USERNAME}" \
        -s /bin/bash \
        -u ${UID} \
        -D \
        ${USERNAME}
    passwd -d ${USERNAME}
    info "Added user ${USERNAME} with id ${UID}"

    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" && chmod 0440 "/etc/sudoers.d/${USERNAME}"
fi
