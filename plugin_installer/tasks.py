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
import tempfile
import shutil
import pip

from os import path
from cloudify import utils
from cloudify.constants import VIRTUALENV_PATH_KEY
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import LocalCommandRunner
from cloudify.decorators import operation
from cloudify import ctx



@operation
def install(plugins, **kwargs):

    """
    Installs the given plugins.
    Each method decorated with the 'cloudify.decorators.operation'
    will be registered as a task.

    :param plugins: A collection of plugins to install.
    """

    for plugin in plugins:
        install_plugin(ctx.blueprint.id, plugin)


def install_plugin(blueprint_id, plugin):
    name = plugin['name']
    ctx.logger.info('Installing {0}'.format(name))
    url = get_url(blueprint_id, plugin)
    ctx.logger.debug('Installing {0} from {1}'.format(name, url))
    install_package(url)
    plugin_name = extract_plugin_name(url)
    LocalCommandRunner().run(
        '{0} daemon register --queue={1} --plugin={2}'
        .format(_cloudify_agent(), ctx.task_target, plugin_name))


def install_package(url):

    """
    Installs a package onto the worker's virtualenv.

    :param url: A URL to the package archive.
    """

    command = '{0} install {1}'.format(_pip(), url)
    LocalCommandRunner().run(command)


def extract_plugin_name(plugin_url):
    previous_cwd = os.getcwd()
    fetch_plugin_from_pip_by_url = not os.path.isdir(plugin_url)
    plugin_dir = plugin_url
    try:
        if fetch_plugin_from_pip_by_url:
            plugin_dir = tempfile.mkdtemp()
            req_set = pip.req.RequirementSet(build_dir=None,
                                             src_dir=None,
                                             download_dir=None)
            req_set.unpack_url(link=pip.index.Link(plugin_url),
                               location=plugin_dir,
                               download_dir=None,
                               only_download=False)
        runner = LocalCommandRunner()
        os.chdir(plugin_dir)
        plugin_name = runner.run(
            '{0} {1} {2}'.format(_python(),
                                 path.join(
                                     path.dirname(__file__),
                                     'extract_package_name.py'),
                                 plugin_dir)).std_out
        runner.run('{0} install --no-deps {1}'.format(_pip(), plugin_dir))
        return plugin_name
    finally:
        os.chdir(previous_cwd)
        if fetch_plugin_from_pip_by_url:
            shutil.rmtree(plugin_dir)


def get_url(blueprint_id, plugin):

    source = plugin['source']
    if '://' in source:
        split = source.split('://')
        schema = split[0]
        if schema in ['http', 'https']:
            # in case of a URL, return as is.
            return source
        # invalid schema
        raise NonRecoverableError('Invalid schema: {0}'.format(schema))

    # Else, assume its a relative path from <blueprint_home>/plugins
    # to a directory containing the plugin project.
    # in this case, the archived plugin will reside in the manager file server.

    blueprint_plugins_url = '{0}/{1}/plugins'.format(
        utils.get_manager_file_server_blueprints_root_url(),
        blueprint_id
    )
    return '{0}/{1}.zip'.format(blueprint_plugins_url, source)


def _python():
    return _virtualenv('python')


def _pip():
    return _virtualenv('pip')


def _cloudify_agent():
    return _virtualenv('cloudify-agent')


def _virtualenv(command):
    return os.path.join(os.environ[VIRTUALENV_PATH_KEY],
                        'bin',
                        command)
