#!/usr/bin/env sh
## remove-tests.sh
##
## Copyright (c) 2019 libcommon
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.


if [ $# -lt 1 ]
then
    echo "::: ERROR: Must supply at least one file/directory to remove tests from"
    exit 1
fi

PATTERN='if os.environ.get("ENVIRONMENT") == "TEST"'

if [ -x $(which gsed) ]
then
    COMMAND="gsed"
else
    COMMAND="sed"
fi

echo "::: INFO: Removing tests from ${@}"
find "${@}" -type f -exec $COMMAND -i'' -n "/${PATTERN}/q;p" {} \; \
    -exec $COMMAND -i'' '$d' {} \; \
    -exec $COMMAND -i'' '$d' {} \;
