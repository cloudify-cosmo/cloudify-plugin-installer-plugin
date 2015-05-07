########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import os
import pip
import shutil
import tempfile

from cloudify import exceptions


def parse_pip_version(pip_version=None):
    if not pip_version:
        try:
            pip_version = pip.__version__
        except AttributeError as e:
            raise exceptions.NonRecoverableError(
                'Failed to get pip version: ', str(e))

    if not pip_version:
        raise exceptions.NonRecoverableError('Failed to get pip version')

    if not isinstance(pip_version, basestring):
        raise exceptions.NonRecoverableError(
            'Invalid pip version: {0} is not a string'
            .format(pip_version))

    if not pip_version.__contains__("."):
        raise exceptions.NonRecoverableError(
            'Unknown formatting of pip version: "{0}", expected '
            'dot-delimited numbers (e.g. "1.5.4", "6.0")'
            .format(pip_version))

    version_parts = pip_version.split('.')
    major = version_parts[0]
    minor = version_parts[1]
    micro = ''
    if len(version_parts) > 2:
        micro = version_parts[2]

    if not str(major).isdigit():
        raise exceptions.NonRecoverableError(
            'Invalid pip version: "{0}", major version is "{1}" '
            'while expected to be a number'
            .format(pip_version, major))

    if not str(minor).isdigit():
        raise exceptions.NonRecoverableError(
            'Invalid pip version: "{0}", minor version is "{1}" while '
            'expected to be a number'
            .format(pip_version, minor))

    return major, minor, micro


def extract_plugin_dir(plugin_url):
    plugin_dir = None

    try:
        plugin_dir = tempfile.mkdtemp()
        # check pip version and unpack plugin_url accordingly
        if is_pip6_or_higher():
            pip.download.unpack_url(link=pip.index.Link(plugin_url),
                                    location=plugin_dir,
                                    download_dir=None,
                                    only_download=False)
        else:
            req_set = pip.req.RequirementSet(build_dir=None,
                                             src_dir=None,
                                             download_dir=None)
            req_set.unpack_url(link=pip.index.Link(plugin_url),
                               location=plugin_dir,
                               download_dir=None,
                               only_download=False)

    except Exception as e:
        if plugin_dir and os.path.exists(plugin_dir):
            shutil.rmtree(plugin_dir)
        raise exceptions.NonRecoverableError(
            'Failed to download and unpack plugin from {0}: {1}'
            .format(plugin_url, str(e)))

    return plugin_dir


def is_pip6_or_higher(pip_version=None):
    major, minor, micro = parse_pip_version(pip_version)
    if int(major) >= 6:
        return True
    else:
        return False
