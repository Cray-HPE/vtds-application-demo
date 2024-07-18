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
"""Mock SCS service which demonstrates REST API access between FSM and
SCS nodes on the cluster.

"""
from getopt import (
    getopt,
    GetoptError
)
import json
import sys
from flask import (
    Flask,
    request
)
from requests import (
    get as url_get,
    post as url_post,
    delete as url_delete
)


class ContextualError(Exception):
    """Exception to report failures seen and contextualized within the
    application.

    """


class UsageError(Exception):  # pylint: disable=too-few-public-methods
    """Exception to report usage errors

    """


JSON_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
TEXT_HEADERS = {
    'Content-Type': 'text/plain',
    'Accept': 'text/plain'
}
# pylint: disable=invalid-name
server_port = "5000"

app = Flask(__name__)


def write_err(string):
    """Write an arbitrary string on stderr and make sure it is
    flushed.

    """
    sys.stderr.write(string)
    sys.stderr.flush()


def usage(usage_msg, err=None):
    """Print a usage message and exit with an error status.

    """
    if err:
        write_err("ERROR: %s\n" % err)
    write_err("%s\n" % usage_msg)
    sys.exit(1)


class MyData:
    """SCS Data served by the server.

    """
    my_scone = "I don't have a scone, please give me one..."
    fsm = {}

    @classmethod
    def give_scone(cls, new_scone):
        """Give SCS a new scone, overwriting the old one...

        """
        cls.my_scone = new_scone
        return cls.my_scone

    @classmethod
    def new_fsm(cls, fsm_info):
        """Connect to an FSM.

        """
        cls.fsm = fsm_info
        return cls.fsm

    @classmethod
    def del_fsm(cls):
        """Disconnect from an FSM

        """
        old_fsm = cls.fsm
        cls.fsm = {}
        return old_fsm

    @classmethod
    def new_fsm_muffin(cls, muffin):
        """Update the FSM muffin

        """
        cls.fsm['muffin'] = muffin
        return cls.fsm


app = Flask(__name__)


@app.route('/scone', methods=('GET', 'POST'))
def scone():
    """The '/scone' path handler.

    """
    if request.method == 'POST':
        return MyData.give_scone(request.get_data().decode('UTF-8'))
    if request.method == 'GET':
        return MyData.my_scone
    raise ContextualError(
        "internal error: unknown request method '%s' passed to "
        "'/scone' handler" % request.method
    )


@app.route('/fsm', methods=('GET', 'POST', 'DELETE'))
def fsm():
    """The '/fsm' path handler.

    """
    if request.method == 'GET':
        if not MyData.fsm:
            return json.dumps(None)
        ip_addr = MyData.fsm['ip']
        port = MyData.fsm['port']
        muffin_url = "http://%s:%s/muffin" % (ip_addr, port)
        response = url_get(
            muffin_url, headers=TEXT_HEADERS, verify=False, timeout=300
        )
        if not response.ok:
            return 'Getting muffin from FSM FAILED: %s' % (str(response))
        MyData.new_fsm_muffin(response.text)
        return json.dumps(MyData.fsm)
    if request.method == 'POST':
        raw_data = request.get_data().decode('UTF-8')
        fsm_data = json.loads(raw_data)
        try:
            ip_addr = fsm_data['ip']
            port = fsm_data['port']
        except KeyError as err:
            print("FSM data was missing '%s'" % str(err))
            return None
        register_data = {'port': server_port}
        register_url = "http://%s:%s/scs_list" % (ip_addr, port)
        response = url_post(
            register_url, headers=JSON_HEADERS, verify=False, timeout=300,
            json=register_data
        )
        if not response.ok:
            return 'Register with FSM FAILED: %s' % (str(response))
        muffin_url = "http://%s:%s/muffin" % (ip_addr, port)
        response = url_get(
            muffin_url, headers=TEXT_HEADERS, verify=False, timeout=300
        )
        if not response.ok:
            return 'Getting muffin from FSM FAILED: %s' % (str(response))
        fsm_data['muffin'] = response.text
        return json.dumps(MyData.new_fsm(fsm_data))
    if request.method == 'DELETE':
        ip_addr = MyData.fsm['ip']
        port = MyData.fsm['port']
        delete_url = "http://%s:%s/scs_list" % (ip_addr, port)
        response = url_delete(
            delete_url, headers=JSON_HEADERS, verify=False, timeout=300
        )
        if not response.ok:
            return 'Register with FSM FAILED: %s' % (str(response))
        return json.dumps(MyData.del_fsm())
    raise ContextualError(
        "internal error: unknown request method '%s' passed to "
        "'/fsm' handler" % request.method
    )


def main(argv):
    """Main entry point for the mock SCS

    """
    # pylint: disable=global-statement
    global server_port
    try:
        optlist, _ = getopt(
            argv,
            "p:h",
        )
    except GetoptError as err:
        raise UsageError(str(err)) from err
    for opt, arg in optlist:
        if opt in ['-p']:
            try:
                server_port = str(int(arg))
            except ValueError as err:
                raise UsageError(
                    "server port ('%s') must be an integer value" % arg
                ) from err
    app.run(host='0.0.0.0', port=server_port)


def entrypoint(usage_msg, main_func):
    """Generic entrypoint function. This sets up command line
    arguments for the invocation of a 'main' function and takes care
    of handling any vTDS exceptions that are raised to report
    errors. Other exceptions are allowed to pass to the caller for
    handling.

    """
    try:
        main_func(sys.argv[1:])
    except ContextualError as err:
        write_err("ERROR: %s\n" % str(err))
        sys.exit(1)
    except UsageError as err:
        usage(usage_msg, str(err))


if __name__ == '__main__':
    USAGE_MSG = """
usage: scs [-p SERVER_PORT]

Where:

    SERVER_PORT is the port on which the mock SCS should listen on the
                node.
"""[1:-1]
    entrypoint(USAGE_MSG, main)
