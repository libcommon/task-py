## setup.py
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


import os
import setuptools

if os.path.isfile("README.md"):
    with open("README.md", "r") as readme:
        long_description = readme.read()
else:
    long_description = ""


setuptools.setup(
    name="PACKAGE_NAME",
    version="PACKAGE_VERSION",
    author="libcommon",
    author_email="libcommon@protonmail.com",
    description="PACKAGE_SHORT_DESCRIPTION",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="PACKAGE_CODE_URL",
    project_urls={
        "Issue Tracker": "PACKAGE_CODE_URL/issues",
        "Releases": "PACKAGE_CODE_URL/releases"
    },
    packages=setuptools.find_packages(),
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=PACKAGE_MIN_PYTHON_VERSION',
)
