import sys
import os
import json
import unicodedata
import datetime
from email.utils import parsedate
import time
from workflow import Workflow, PasswordNotFound, ICON_TRASH
from dropbox import client, rest
import config


def main(wf):
    user_input = wf.args[0]
    command = query = ''
    if len(user_input) > 0:
        command = user_input.split()[0]
        query = user_input[len(command) + 1:]

    try:
        wf.get_password('dropbox_access_tokens')
        accounts = wf.cached_data(
            'dropbox_accounts', data_func=get_account_info, max_age=60 * 60)
    except PasswordNotFound:
        accounts = None

    if command == 'auth':
        if query == '':
            wf.add_item(
                'Please enter your authorization code', 'If you don\'t have one, simply press enter.', arg='url %s' % get_auth_url(), valid=True)
        else:
            wf.add_item(
                'Authorize with "%s"' % query, 'Press enter to proceed', arg='auth %s' % query, valid=True)

    elif accounts is not None and command == 'remove':
        for account in accounts:
            wf.add_item(get_title(account), account[
                        'email'], arg='remove %s' % account['uid'], valid=True)
    elif accounts is not None and len(user_input) > 0 and uid_exists(command, accounts):
        file_or_folder = get_file_or_folder(command, query)
        if len(file_or_folder) > 0:
            for f in file_or_folder:
                if len(user_input) > 1 and query == f['path']:
                    wf.add_item(
                        'Share', 'Copy link to clipboard', arg='share %s %s' % (command, f['path']), icon='icons/folder_public.png', valid=True)
                    wf.add_item(
                        'Save to Downloads', arg='download %s %s' % (command, f['path']), icon='icons/download.png', valid=True)
                    wf.add_item(
                        'Save to Desktop', arg='desktop %s %s' % (command, f['path']), icon='icons/desktop.png', valid=True)
                    wf.add_item(
                        'Delete', arg='delete %s %s' % (command, f['path']), icon=ICON_TRASH, valid=True)
                else:
                    title = os.path.basename(f['path'])
                    subtitle = 'Modified: %s' % time.strftime(
                        '%Y-%m-%d %H:%M:%S', parsedate(f['modified']))

                    icon = 'icons/%s.png' % f['icon']
                    if not os.path.isfile(icon):
                        icon = 'icons/page_white.png'

                    if f['is_dir']:
                        title += '/'
                        wf.add_item(
                            title, subtitle, icon=icon, autocomplete='%s %s/' % (command, f['path']), valid=False)
                    else:
                        title += ' (%s)' % f['size']
                        wf.add_item(
                            title, subtitle, icon=icon, autocomplete='%s %s' % (command, f['path']), valid=False)
            if query != '':
                path = f['path'].split('/')
                path = '/'.join(path[:-2])
                wf.add_item(
                    '..', 'Change to parent directory', icon='icons/folder.png',
                    autocomplete='%s %s/' % (command, path), valid=False)
        else:
            wf.add_item(
                'No files were found', 'Try a different request.', valid=False)
    else:
        if accounts is not None:
            for account in accounts:
                wf.add_item(get_title(account), account[
                            'email'], autocomplete='%s ' % account['uid'], valid=False)

        wf.add_item('Add another Dropbox account',
                    '', autocomplete='auth ', valid=False)
        if accounts is not None and len(accounts) > 0:
            wf.add_item('Remove an existing Dropbox account',
                        '', autocomplete='remove', valid=False)

    wf.send_feedback()


def get_file_or_folder(uid, query):
    path = '/' if query == '' else query

    if len(path) > 1 and path[-1] == '/':
        path = path[:-1]

    access_tokens = json.loads(wf.get_password('dropbox_access_tokens'))
    api_client = client.DropboxClient(access_tokens[uid])
    output = []
    try:
        resp = api_client.metadata(path, file_limit=100)
        if 'contents' in resp:
            output = resp['contents']
        else:
            output.append(resp)
        wf.cache_data('last_path', path)
        wf.cache_data('last_output', output)
        return output
    except rest.ErrorResponse, e:
        last_path = wf.cached_data('last_path')
        if last_path in path:
            query = path[len(last_path) + 1:]
            output = api_client.search(
                last_path, unicodedata.normalize('NFC', query), file_limit=100)

    return output


def get_account_info():
    output = []
    for access_token in json.loads(wf.get_password('dropbox_access_tokens')).values():
        api_client = client.DropboxClient(access_token)
        output.append(api_client.account_info())
    return output


def get_auth_url():
    flow = client.DropboxOAuth2FlowNoRedirect(
        config.APP_KEY, config.APP_SECRET)
    return flow.start()


def get_title(account):
    total_used = round(100.0 * (account['quota_info']['normal'] + account[
                       'quota_info']['shared']) / account['quota_info']['quota'], 2)
    return '%s (%s%% of %s used)' % (account['display_name'], total_used, sizeof(account['quota_info']['quota']))


def uid_exists(uid, accounts):
    for account in accounts:
        try:
            if account['uid'] == int(uid):
                return True
        except ValueError:
            return False
    return False


def sizeof(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
