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

import shutil

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import get_manager_file_server_blueprints_root_url
from cloudify.utils import get_agent_name
from cloudify.decorators import operation

from plugin_installer import VIRTUALENV
from plugin_installer import utils


@operation
def install(plugins, **_):

    for plugin in plugins:
        ctx.logger.info('Installing plugin: {0}'.format(plugin['name']))
        install_plugin(plugin)


def install_plugin(plugin):
    extracted_plugin_dir = None
    try:
        name = plugin['name']
        ctx.logger.info('Installing {0}'.format(name))
        url, install_args = get_url_and_args(plugin)
        ctx.logger.debug(
            'Installing {0} from {1} with args: {2}'
            .format(name, url, install_args))

        extracted_plugin_dir = utils.extract_plugin_dir(url)
        install_package(extracted_plugin_dir, install_args)
        plugin_name = extract_plugin_name(url)
        ctx.runner.run('{0} daemon register --name={1} --plugin={2}'
                       .format(_cloudify_agent(),
                               get_agent_name(),
                               plugin_name))
    finally:
        if extracted_plugin_dir:
            shutil.rmtree(extracted_plugin_dir)


def install_package(extracted_plugin_dir, install_args):

    """
    Installs a package onto the worker's virtualenv.

    :param extracted_plugin_dir:

        The directory containing the extracted plugin.
        If the plugin's source property is a URL, this
        is the directory the plugin was unpacked to.

    :param install_args: Arguments passed to pip install.
                         e.g.: -r requirements.txt
    """

    command = '{0} install {1} {2}'.format(
        _pip(), extracted_plugin_dir, install_args)
    ctx.runner.run(command)


def get_url_and_args(plugin_dict):

    source = plugin_dict.get('source') or ''
    if source:
        source = source.strip()
    else:
        raise NonRecoverableError('Plugin source is not defined')

    install_args = plugin_dict.get('install_arguments') or ''
    install_args = install_args.strip()

    # validate source url
    if '://' in source:
        split = source.split('://')
        schema = split[0]
        if schema not in ['http', 'https']:
            # invalid schema
            raise NonRecoverableError('Invalid schema: {0}'.format(schema))
        else:
            # in case of a URL, return source and args as is.
            return source, install_args
    else:
        # Else, assume its a relative path from <blueprint_home>/plugins
        # to a directory containing the plugin archive.
        # in this case, the archived plugin is expected to reside on the
        # manager file server as a zip file.
        blueprints_root = get_manager_file_server_blueprints_root_url()
        blueprint_plugins_url = '{0}/{1}/plugins'.format(
            blueprints_root, ctx.blueprint.id)

        blueprint_plugins_url_as_zip = '{0}/{1}.zip'. \
            format(blueprint_plugins_url, source)
        return blueprint_plugins_url_as_zip, install_args


def _pip():
    return '{0}/bin/pip'.format(VIRTUALENV)


def _cloudify_agent():
    return '{0}/bin/cfy-agent'.format(VIRTUALENV)
