#!/usr/bin/env bash

set -e

. /build-support/shell/common/log.sh


if [ -z "${GID}" ]
then
    error "Must set the GID environment variable"
    exit 1
fi

if [ -z "${GROUPNAME}" ]
then
    error "Must set the GROUPNAME environment variable"
    exit 1
fi

addgroup --gid ${GID} ${GROUPNAME}
info "Added group ${GROUPNAME} with id ${GID}"
