# This code is part of Qiskit.
#
# (C) Copyright IBM 2019
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""API server for listening to events from github."""

import logging
import os
import sys
from urllib import parse

import fasteners
import flask
import github_webhook

from qiskit_bot import config
from qiskit_bot import git
from qiskit_bot import release_process
from qiskit_bot import repos


LOG = logging.getLogger(__name__)

APP = flask.Flask(__name__)
WEBHOOK = github_webhook.Webhook(APP)

REPOS = {}
META_REPO = None
CONFIG = None


@APP.before_first_request
def _setup():
    setup()


def get_app():
    return APP


def setup():
    """Setup config."""
    global CONFIG
    global META_REPO
    if not CONFIG:
        CONFIG = config.load_config('/etc/qiskit_bot.yaml')
    if not os.path.isdir(CONFIG['working_dir']):
        os.mkdir(CONFIG['working_dir'])
    if not os.path.isdir(os.path.join(CONFIG['working_dir'], 'lock')):
        os.mkdir(os.path.join(CONFIG['working_dir'], 'lock'))
    for repo in CONFIG['repos']:
        REPOS[repo['name']] = repos.Repo(CONFIG['working_dir'], repo['name'],
                                      CONFIG['api_key'])
    META_REPO = repos.Repo(CONFIG['working_dir'], CONFIG['meta_repo'],
                           CONFIG['api_key'])


@APP.route("/", methods=['GET'])
def list_routes():
    """List routes on gets to root."""
    output = []
    for rule in APP.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)
        url = flask.url_for(rule.endpoint, **options)
        out_dict = {
            'name': rule.endpoint,
            'methods': sorted(rule.methods),
            'url': parse.unquote(url),
        }
        output.append(out_dict)
    return flask.jsonify({'routes': output})


@WEBHOOK.hook(event_type='push')
def on_push(data):
    """Handle github pushes."""
    LOG.debug('Received push event for repo: %s sha1: %s' % (
        data['repository']['full_name'], data['after']))
    global REPOS
    print(type(data))
    import pprint
    pprint.pprint(data)
#    data = json.loads(body)
#    repo_name = data['repository']['full_name']
#    git_url = data['repository']['git_url']


@WEBHOOK.hook(event_type='create')
def on_create(data):
    global REPOS
    if data['ref_type']:
        tag_name = data['ref']
        repo_name = data['repository']['full_name']
        if repo_name in REPOS:
            release_process.finish_release(tag_name, REPOS[repo_name],
                                           CONFIG, META_REPO)
        else:
            LOG.warn('Recieved webhook event for %s, but this is not a '
                     'configured repository.' % repo_name)


@WEBHOOK.hook(event_type='pull_request')
def on_pull_event(data):
    global META_REPO
    global CONFIG
    if data['action'] == 'closed':
        if data['pull_request']['repo']['full_name'] == META_REPO.repo_name:
            if data['pull_request']['title'] == 'Bump Meta':
                with fasteners.InterProcessLock(
                    os.path.join(os.path.join(CONFIG.working_dir, 'lock'),
                                 META_REPO.name)):
                    # Delete github branhc:
                    META_REPO.get_git_ref("heads/source" 'bump_meta').delete()
                    # Delete local branch
                    git.checkout_master(META_REPO)
                    git.delete_local_branch('bump_meta')


@WEBHOOK.hook(event_type='pull_request_review')
def on_pull_request_review(data):
    pass


def main():
    """Run APP."""
    global CONFIG
    CONFIG = config.load_config(sys.argv[1])
    log_format = ('%(asctime)s.%(msecs)03d %(process)d %(levelname)s '
                  '%(name)s [-] %(message)s')
    logging.basicConfig(level=logging.DEBUG, format=log_format)
    APP.run(debug=True, host='127.0.0.1', port=8080)


if __name__ == "__main__":
    main()