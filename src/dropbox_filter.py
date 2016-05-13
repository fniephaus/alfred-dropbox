import os
import sys
import time
from email.utils import parsedate

import config
from helpers import get_resource, get_hash, get_account_info, uid_exists

from dropbox import client
from workflow import Workflow, PasswordNotFound, ICON_TRASH
from workflow.background import run_in_background


def main(wf):
    if wf.update_available:
        subtitle = 'New: %s' % wf.update_info['body']
        wf.add_item("An update is available!", subtitle,
                    autocomplete='workflow:update', valid=False)

    user_input = wf.args[0]
    command = query = ''
    if len(user_input) > 0:
        command = user_input.split()[0]
        query = user_input[len(command) + 1:]

    try:
        wf.get_password('dropbox_access_tokens')
        accounts = wf.cached_data(
            'dropbox_accounts', data_func=get_account_info, max_age=360)
    except PasswordNotFound:
        accounts = None

    if command == 'auth':
        if query == '':
            wf.add_item(
                'Please enter your authorization code',
                'If you don\'t have one, simply press enter.',
                arg='url %s' % get_auth_url(), valid=True)
        else:
            wf.add_item(
                'Authorize with "%s"' % query, 'Press enter to proceed',
                arg='auth %s' % query, valid=True)

    elif accounts is not None and command == 'remove':
        for account in accounts:
            wf.add_item(get_title(account), account[
                        'email'], arg='remove %s' % account['uid'], valid=True)
    elif (accounts is not None and len(user_input) > 0 and
            uid_exists(command, accounts)):
        file_or_folder = get_file_or_folder(command, query)
        if isinstance(file_or_folder, dict):  # file
            wf.add_item(
                'Share', 'Copy link to clipboard',
                arg='share %s %s' % (command, file_or_folder['path']),
                icon='icons/folder_public.png', valid=True)
            wf.add_item(
                'Save to Downloads',
                arg='download %s %s' % (command, file_or_folder['path']),
                icon='icons/download.png', valid=True)
            wf.add_item(
                'Save to Desktop',
                arg='desktop %s %s' % (command, file_or_folder['path']),
                icon='icons/desktop.png', valid=True)
            wf.add_item(
                'Delete',
                arg='delete %s %s' % (command, file_or_folder['path']),
                icon=ICON_TRASH, valid=True)
        elif isinstance(file_or_folder, list) and file_or_folder:  # folder
            if query and query != '/':
                path = file_or_folder[0]['path'].split('/')
                path = '/'.join(path[:-2])
                wf.add_item(
                    '..', 'Change to parent directory',
                    icon='icons/folder.png',
                    autocomplete='%s %s/' % (command, path), valid=False)
            for f in file_or_folder:
                title = os.path.basename(f['path'])
                subtitle = 'Modified: %s' % time.strftime(
                    '%Y-%m-%d %H:%M:%S', parsedate(f['modified']))

                icon = 'icons/%s.png' % f['icon']
                if not os.path.isfile(icon):
                    icon = 'icons/page_white.png'

                if f['is_dir']:
                    title += '/'
                    wf.add_item(
                        title, subtitle, icon=icon,
                        autocomplete='%s %s/' % (command, f['path']),
                        valid=False)
                else:
                    title += ' (%s)' % f['size']
                    wf.add_item(
                        title, subtitle, icon=icon,
                        autocomplete='%s %s' % (command, f['path']),
                        valid=False)
        else:
            wf.add_item(
                'No files were found', 'Try a different request.', valid=False)
    else:
        if accounts is not None:
            for account in accounts:
                wf.add_item(get_title(account),
                            account['email'],
                            autocomplete='%s ' % account['uid'],
                            valid=False)

        wf.add_item('Add another Dropbox account',
                    '', autocomplete='auth ', valid=False)
        if accounts is not None and len(accounts) > 0:
            wf.add_item('Remove an existing Dropbox account',
                        '', autocomplete='remove', valid=False)

    wf.send_feedback()


def prefetch(wf, uid, path):
    job_name = 'dropbox_prefetch_%s' % get_hash(uid, path)
    cmd = ['/usr/bin/python', wf.workflowfile('dropbox_prefetch.py'), uid, path]
    run_in_background(job_name, cmd)


def get_file_or_folder(uid, query):
    path = '/' if query == '' else query

    if len(path) > 1 and path[-1] == '/':
        path = path[:-1]

    prefetch(wf, uid, path)

    def wrapper():
        return get_resource(uid, path)

    return wf.cached_data(get_hash(uid, path), wrapper, max_age=120)


def get_auth_url():
    flow = client.DropboxOAuth2FlowNoRedirect(
        config.APP_KEY, config.APP_SECRET)
    return flow.start()


def get_title(account):
    normal_use = account['quota_info']['normal']
    shared_use = account['quota_info']['shared']
    total_quota = account['quota_info']['quota']
    total_used = round(100.0 * (normal_use + shared_use) / total_quota, 2)
    return '%s (%s%% of %s used)' % (
        account['display_name'], total_used,
        sizeof(account['quota_info']['quota']))


def sizeof(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


if __name__ == '__main__':
    wf = Workflow(
        update_settings={'github_slug': 'fniephaus/alfred-dropbox'},
        help_url='https://github.com/fniephaus/alfred-dropbox/issues'
    )
    log = wf.logger
    sys.exit(wf.run(main))
