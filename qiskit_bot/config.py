# -*- coding: utf-8 -*-

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

import logging
import os

import voluptuous as vol
import yaml


LOG = logging.getLogger(__name__)


default_changelog_categories = {
    'Changelog: Deprecation': 'Deprecated',
    'Changelog: New Feature': 'Added',
    'Changelog: API Change': 'Changed',
    'Changelog: Removal': 'Removed',
    'Changelog: Bugfix': 'Fixed',
    'Changelog: None': None,
}


schema = vol.Schema({
    vol.Required('api_key'): str,
    vol.Required('working_dir'): str,
    vol.Required('meta_repo'): str,
    vol.Optional('meta_repo_default_branch', default='master'): str,
    vol.Optional('github_webhook_secret'): str,
    vol.Optional('log_level', default='INFO'): str,
    vol.Optional('log_format'): str,
    vol.Required('repos'): vol.All([{
        vol.Required('name'): str,
        vol.Optional('default_branch', default='master'): str,
        vol.Optional('branch_on_release', default=False): bool,
        vol.Optional('optional_package', default=False): bool,
        vol.Optional('uses_community_label', default=False): bool,
        vol.Optional('bump_version', default=False): bool,
        vol.Optional('python_package_name'): str,
    }]),
})


def load_config(path):
    with open(path, 'r') as fd:
        raw_config = yaml.safe_load(fd.read())
    config = schema(raw_config)
    if 'repos' in config:
        LOG.info('Loaded config\nRepos: %s' % ','.join(
            [x['name'] for x in raw_config['repos']]))
    if 'meta_repo' in config:
        LOG.info('meta_repo: %s' % config['meta_repo'])
    return config


local_config_schema = vol.Schema({
    vol.Optional('categories', default=default_changelog_categories): dict,
    vol.Optional('notifications'): {vol.Extra: [str]},
    vol.Optional('notification_prelude'): str,
    vol.Optional('always_notify'): bool,
})


def load_repo_config(repo):
    config_path = os.path.join(repo.local_path, 'qiskit_bot.yaml')
    if not os.path.isfile(config_path):
        return {
            'categories': default_changelog_categories,
            'notifications': {}
        }
    with open(config_path, 'r') as fd:
        raw_config = yaml.safe_load(fd.read())
    try:
        local_config_schema(raw_config)
    except vol.MultipleInvalid:
        LOG.exception('Invalid local repo config for %s' % repo.repo_name)
        return {}
    LOG.info('Loaded local repo config for %s' % repo.repo_name)
    return raw_config
