"""
Pipeline manager module that provides functionality to add, modify and delete pipelines.
"""

import os
import sys
import json
from argparse import ArgumentParser

if "DJANGO_SETTINGS_MODULE" not in os.environ:
    # django needs to be loaded (eg. when this script is run from the command line)
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    import django
    django.setup()

from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from plugins.models import Plugin
from plugins.serializers import PluginSerializer
from pipelines.models import Pipeline
from pipelines.serializers import PipelineSerializer


class PipelineManager(object):

    def __init__(self):
        parser = ArgumentParser(description='Manage pipelines')
        subparsers = parser.add_subparsers(dest='subparser_name', title='subcommands',
                                           description='valid subcommands',
                                           help='sub-command help')

        # create the parser for the "add" command
        parser_add = subparsers.add_parser('add', help='Add a new pipeline')
        parser_add.add_argument('name', help="Plugin's name")
        parser_add.add_argument('owner', help="Plugin's owner username")
        parser_add.add_argument('publicrepo', help="Plugin's public repo url")
        parser_add.add_argument('dockerimage', help="Plugin's docker image name")
        group = parser_add.add_mutually_exclusive_group()
        group.add_argument("--descriptorfile", dest='descriptorfile', type=str,
                           help="A json descriptor file with the plugin representation")
        group.add_argument("--descriptorstring", dest='descriptorstring', type=str,
                           help="A json string with the plugin representation")

        # create the parser for the "modify" command
        parser_modify = subparsers.add_parser('modify', help='Modify existing pipeline')
        parser_modify.add_argument('id', type=int, help="Plugin's id")
        parser_modify.add_argument('publicrepo', help="Plugin's new public repo url")
        parser_modify.add_argument('--newowner', help="Plugin's new owner username")

        # create the parser for the "remove" command
        parser_remove = subparsers.add_parser('remove', help='Remove an existing pipeline')
        parser_remove.add_argument('id', type=int, help="Plugin's id")

        self.parser = parser

    def add_pipeline(self, args):
        """
        Register/add a new plugin to the system.
        """
        df = self.get_plugin_descriptor_file(args)
        data = {'name': args.name, 'public_repo': args.publicrepo, 'version': 'nullnull',
                'dock_image': args.dockerimage, 'descriptor_file': df}
        plg_serializer = PluginSerializer(data=data)
        plg_serializer.is_valid(raise_exception=True)
        owner = User.objects.get(username=args.owner)
        plg_serializer.save(owner=[owner])

    def modify_pipeline(self, args):
        """
        Modify an existing/registered plugin.
        """
        plugin = self.get_plugin(args.id)
        data = {'public_repo': args.publicrepo, 'dock_image': plugin.dock_image,
                'name': plugin.name, 'descriptor_file': plugin.descriptor_file,
                'version': plugin.version}
        plg_serializer = PluginSerializer(plugin, data=data)
        plg_serializer.is_valid(raise_exception=True)
        if args.newowner:
            new_owner = plg_serializer.validate_new_owner(args.newowner)
            plugin.add_owner(new_owner)
        plg_serializer.save()

    def remove_pipeline(self, args):
        """
        Remove an existing/registered plugin from the system.
        """
        plugin = self.get_plugin(args.id)
        plugin.delete()

    def run(self, args=None):
        """
        Parse the arguments passed to the manager and perform the appropriate action.
        """
        options = self.parser.parse_args(args)
        if (options.subparser_name == 'add') and (not options.descriptorfile) and (
                not options.descriptorstring):
                self.parser.error("Either --descriptorFile or --descriptorString must be "
                                  "specified")
        if options.subparser_name == 'add':
            self.add_pipeline(options)
        elif options.subparser_name == 'modify':
            self.modify_pipeline(options)
        elif options.subparser_name == 'remove':
            self.remove_pipeline(options)

    @staticmethod
    def get_plugin(id):
        """
        Get an existing plugin.
        """
        try:
            plugin = Plugin.objects.get(pk=id)
        except Plugin.DoesNotExist:
            raise NameError("Couldn't find plugin with id '%s' in the system" % id)
        return plugin

    @staticmethod
    def get_plugin_descriptor_file(args):
        """
        Get the plugin descriptor file from the arguments.
        """
        if args.descriptorfile:
            f = args.descriptorfile
        else:
            app_repr = json.loads(args.descriptorstring)
            f = ContentFile(json.dumps(app_repr).encode())
            f.name = args.name + '.json'
        return f



# ENTRYPOINT
if __name__ == "__main__":
    manager = PipelineManager()
    manager.run()