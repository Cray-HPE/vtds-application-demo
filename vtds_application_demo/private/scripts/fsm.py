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
"""Mock FSM service which demonstrates REST API access between FSM and
FSM nodes on the cluster.

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
)

JSON_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
TEXT_HEADERS = {
    'Content-Type': 'text/plain',
    'Accept': 'text/plain'
}
SERVER_PORT = "5000"

app = Flask(__name__)


class ContextualError(Exception):
    """Exception to report failures seen and contextualized within the
    application.

    """


class UsageError(Exception):  # pylint: disable=too-few-public-methods
    """Exception to report usage errors

    """


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
    """FSM Data served by the server.

    """
    my_muffin = "I don't have a muffin, please give me one..."
    scs_map = {}

    @classmethod
    def give_muffin(cls, new_muffin):
        """Give SCS a new muffin, overwriting the old one...

        """
        cls.my_muffin = new_muffin
        return cls.my_muffin

    @classmethod
    def add_scs(cls, scs_id, scs_info):
        """Add an SCS to the list of known SCSes.

        """
        cls.scs_map[scs_id] = scs_info
        return scs_info

    @classmethod
    def del_scs(cls, scs_id):
        """Delete an SCS from the list of known SCSes.

        """
        return cls.scs_map.pop(scs_id, None)

    @classmethod
    def get_scs(cls, scs_id):
        """Lookup an SCS by its id and return it.
        """
        return cls.scs_map.get(scs_id, None)

    @classmethod
    def new_scs_scone(cls, scs_id, scone):
        """Update the scone for the specified SCS

        """
        try:
            scs_data = cls.scs_map[scs_id]
            scs_data['scone'] = scone
        except KeyError:
            pass


app = Flask(__name__)


def retrieve_scone(ip_addr, port):
    """Get a scone from the SCS

    """
    scone_url = "http://%s:%s/scone" % (ip_addr, port)
    response = url_get(
        scone_url, headers=TEXT_HEADERS, verify=False, timeout=3000
    )
    if not response.ok:
        return "scone crumbled - %s" % str(response)
    return response.text


@app.route('/muffin', methods=('GET', 'POST'))
def muffin():
    """Path handler for '/muffin'

    """
    if request.method == 'POST':
        print("request data: '%s'" % request.get_data())
        return MyData.give_muffin(request.get_data().decode('UTF-8'))
    if request.method == 'GET':
        return MyData.my_muffin
    raise ContextualError(
        "internal error: unknown request method '%s' passed to "
        "'/muffin' handler" % request.method
    )


@app.route('/scs_list', methods=('GET', 'POST', 'DELETE'))
def scs_list():
    """Path handler for '/scs-list'

    """
    if request.method == 'GET':
        for ip_addr, scs in MyData.scs_map.items():
            port = scs['port']
            scone = retrieve_scone(ip_addr, port)
            MyData.new_scs_scone(ip_addr, scone)
        return json.dumps(MyData.scs_map)
    if request.method == 'POST':
        scs_id = request.remote_addr
        MyData.add_scs(
            scs_id,
            json.loads(request.get_data().decode('UTF-8'))
        )
        return json.dumps(MyData.scs_map)
    if request.method == 'DELETE':
        scs_id = request.remote_addr
        return json.dumps(MyData.del_scs(scs_id))
    raise ContextualError(
        "internal error: unknown request method '%s' passed to "
        "'/scs_list' handler" % request.method
    )


@app.route('/scs_list/<scs_id>', methods=('GET', 'DELETE'))
def scs_list_item(scs_id):
    """Path handler for '/scs-list/<scs_id>'

    """
    if request.method == 'GET':
        for ip_addr, scs in MyData.scs_map.items():
            port = scs['port']
            scone = retrieve_scone(ip_addr, port)
            MyData.new_scs_scone(ip_addr, scone)
        return json.dumps(MyData.get_scs(scs_id))
    if request.method == 'DELETE':
        return json.dumps(MyData.del_scs(scs_id))
    raise ContextualError(
        "internal error: unknown request method '%s' passed to "
        "'/scs-list/<scs_id>' handler" % request.method
    )


def main(argv):
    """Main entry point for the mock FSM

    """
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
usage: fsm [-p SERVER_PORT]

Where:

    SERVER_PORT is the port on which the mock FSM should listen on the
                node.
"""[1:-1]
    entrypoint(USAGE_MSG, main)
