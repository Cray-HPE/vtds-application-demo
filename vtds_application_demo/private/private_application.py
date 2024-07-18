#
# MIT License
#
# (C) Copyright [2024] Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
"""Private layer implementation module for the demo application.

"""
import os
from os.path import join as path_join

from vtds_base import (
    ContextualError,
    info_msg
)
from . import (
    FSM_MOCK_NAME,
    SCS_MOCK_NAME,
    FSM_DEPLOY_SCRIPT_NAME,
    SCS_DEPLOY_SCRIPT_NAME,
    script
)


class PrivateApplication:
    """PrivateApplication class, implements the demo application layer
    accessed through the python Application API.

    """
    def __init__(self, stack, config, build_dir):
        """Constructor, stash the root of the platfform tree and the
        digested and finalized application configuration provided by the
        caller that will drive all activities at all layers.

        """
        self.config = config
        self.stack = stack
        self.build_dir = build_dir
        self.prepared = False

    def prepare(self):
        """Prepare operation. This drives creation of the application
        layer definition and any configuration that need to be driven
        down into the application layer to be ready for deployment.

        """
        self.prepared = True

    def validate(self):
        """Run the terragrunt plan operation on a prepared demo
        application layer to make sure that the configuration produces a
        useful result.

        """
        if not self.prepared:
            raise ContextualError(
                "cannot validate an unprepared application, "
                "call prepare() first"
            )

    def deploy(self):
        """Deploy operation. This drives the deployment of application
        layer resources based on the layer definition. It can only be
        called after the prepare operation (prepare()) completes.

        """
        if not self.prepared:
            raise ContextualError(
                "cannot deploy an unprepared application, call prepare() first"
            )
        # Open up connections to all of the vTDS Virtual Nodes so I can
        # reach SSH (port 22) on each of them to copy in files and run
        # the deployment script.
        virtual_nodes = self.stack.get_cluster_api().get_virtual_nodes()
        node_files = {
            'fsm_node': {
                'script_files': [
                    (FSM_MOCK_NAME, 'fsm-mock'),
                    (FSM_DEPLOY_SCRIPT_NAME, 'fsm-deploy'),
                ],
                'script': path_join(os.sep, 'root', FSM_DEPLOY_SCRIPT_NAME),
            },
            'scs_node': {
                'script_files': [
                    (SCS_MOCK_NAME, 'scs-mock'),
                    (SCS_DEPLOY_SCRIPT_NAME, 'scs-deploy'),
                ],
                'script': path_join(os.sep, 'root', SCS_DEPLOY_SCRIPT_NAME),
            }
        }
        for node_type, data in node_files.items():
            files = data['script_files']
            deploy_script = data['script']
            with virtual_nodes.ssh_connect_nodes([node_type]) as connections:
                for filename, tag in files:
                    source = script(filename)
                    dest = path_join(os.sep, 'root', filename)
                    info_msg(
                        "copying '%s' to Virtual Nodes of type %s "
                        "'%s'" % (
                            source, node_type, dest
                        )
                    )
                    connections.copy_to(
                        source, dest,
                        recurse=False, logname="upload-application-%s-to" % tag
                    )
                    cmd = (
                        "chmod 755 %s;" % deploy_script +
                        "python3 " +
                        "%s " % deploy_script
                    )
                info_msg(
                    "running '%s' on Virtual Nodes of type %s" %
                    (
                        cmd, node_type
                    )
                )
                connections.run_command(cmd, "run-app-deploy-script-on")

    def remove(self):
        """Remove operation. This will remove all resources
        provisioned for the application layer.

        """
        if not self.prepared:
            raise ContextualError(
                "cannot deploy an unprepared application, call prepare() first"
            )
