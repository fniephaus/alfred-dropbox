import os
import sys
from email.utils import parsedate

import dropbox_config
from helpers import get_resource, get_hash, get_account_info, account_id_exists

import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
from workflow import Workflow, PasswordNotFound, ICON_TRASH
from workflow.background import run_in_background


def main(wf):
    if wf.update_available:
        wf.add_item('An update is available!',
                    autocomplete='workflow:update', valid=False)

    assert wf.args, 'Input is required'

    user_input = wf.args[0]
    command = query = ''
    if ' ' in user_input:
        command, _, query = user_input.partition(' ')

    try:
        wf.get_password(dropbox_config.TOKEN_KEY)
        accounts = wf.cached_data(
            'dropbox_accounts', data_func=get_account_info, max_age=360)
    except PasswordNotFound:
        accounts = None

    account_index = None
    try:
        account_index = int(command)
    except ValueError:
        pass

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
            wf.add_item(get_title(account), account[0].email,
                        arg='remove %s' % account[0].account_id, valid=True)
    elif (accounts is not None and account_index is not None and
          account_index <= len(accounts)):
        account = accounts[account_index]
        file_or_folder = get_file_or_folder(account[0].account_id, query)
        if isinstance(file_or_folder, dict):  # file
            wf.add_item(
                'Share', 'Copy link to clipboard',
                arg='share %s %s' % (account_index, file_or_folder['path']),
                icon='icons/folder_public.png', valid=True)
            wf.add_item(
                'Save to Downloads',
                arg='download %s %s' % (account_index, file_or_folder['path']),
                icon='icons/download.png', valid=True)
            wf.add_item(
                'Save to Desktop',
                arg='desktop %s %s' % (account_index, file_or_folder['path']),
                icon='icons/desktop.png', valid=True)
            wf.add_item(
                'Delete',
                arg='delete %s %s' % (account_index, file_or_folder['path']),
                icon=ICON_TRASH, valid=True)
        elif isinstance(file_or_folder, list) and file_or_folder:  # folder
            if query and query != '/':
                path = file_or_folder[0].path_display.split('/')
                path = '/'.join(path[:-2])
                wf.add_item(
                    '..', 'Change to parent directory',
                    icon='icons/folder.png',
                    autocomplete='%s %s/' % (account_index, path), valid=False)
            for f in file_or_folder:
                title = os.path.basename(f.path_display)
                if isinstance(f, dropbox.files.FolderMetadata):
                    title += '/'
                    wf.add_item(
                        title, '', icon='icons/folder.png',
                        autocomplete='%s %s/' % (command, f.path_display),
                        valid=False)
                elif isinstance(f, dropbox.files.FileMetadata):
                    title += ' (%s)' % sizeof(f.size)
                    subtitle = 'Modified: %s' % f.server_modified
                    wf.add_item(
                        title, subtitle, icon='icons/%s' % (guess_icon(f.path_display)),
                        autocomplete='%s %s!' % (command, f.path_display),
                        valid=False)
        else:
            wf.add_item(
                'No files were found', 'Try a different request.', valid=False)
    else:
        if accounts is not None:
            for index, account in enumerate(accounts):
                wf.add_item(get_title(account),
                            account[0].email,
                            autocomplete='%s ' % index,
                            valid=False)

        wf.add_item('Add another Dropbox account',
                    '', autocomplete='auth ', valid=False)
        if accounts is not None and len(accounts) > 0:
            wf.add_item('Remove an existing Dropbox account',
                        '', autocomplete='remove', valid=False)

    wf.send_feedback()


def prefetch(wf, uid, path):
    job_name = 'dropbox_prefetch_%s' % get_hash(uid, path)
    cmd = ['/usr/bin/python', wf.workflowfile('dropbox_prefetch.py'),
           uid, path]
    run_in_background(job_name, cmd)


def get_file_or_folder(uid, path):
    is_file = False

    if len(path) > 1:
        if path.endswith('!'):
            is_file = True
        if is_file or path.endswith('/'):
            path = path[:-1]

    prefetch(wf, uid, path)

    def wrapper():
        return get_resource(uid, path, is_file)

    return wf.cached_data(get_hash(uid, path), wrapper, max_age=120)


def get_auth_url():
    return DropboxOAuth2FlowNoRedirect(
        dropbox_config.APP_KEY, dropbox_config.APP_SECRET).start()


def get_title(account):
    used = account[1].used
    allocation = account[1].allocation
    if allocation.is_team():
        allocated = allocation.get_team().allocated
    else:
        allocated = allocation.get_individual().allocated
    relative_usage = round(100.0 * (used) / allocated, 2)
    return '%s (%s%% of %s used)' % (
        account[0].name.display_name, relative_usage,
        sizeof(allocated))


def sizeof(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def guess_icon(filename):
    if filename.endswith('.pdf'):
        return 'page_white_acrobat.png'
    if filename.endswith('.c'):
        return 'page_white_c.png'
    if any(filename.endswith(x) for x in ['.py', '.r', '.st']):
        return 'page_white_code.png'
    if any(filename.endswith(x) for x in ['.xls', '.xlsx']):
        return 'page_white_excel.png'
    if any(filename.endswith(x) for x in ['.mp4', '.mpeg', '.mov', '.avi']):
        return 'page_white_film.png'
    if filename.endswith('.h'):
        return 'page_white_h.png'
    if filename.endswith('.java'):
        return 'page_white_java.png'
    if filename.endswith('.js'):
        return 'page_white_js.png'
    if filename.endswith('.key'):
        return 'page_white_keynote.png'
    if filename.endswith('.numbers'):
        return 'page_white_numbers.png'
    if filename.endswith('.php'):
        return 'page_white_php.png'
    if any(filename.endswith(x) for x in
            ['.png', '.jpg', '.jpeg', '.bmp', '.psd', '.gif']):
        return 'page_white_picture.png'
    if filename.endswith('.rb'):
        return 'page_white_ruby.png'
    if any(filename.endswith(x) for x in ['.ppt', '.pptx']):
        return 'page_white_powerpoint.png'
    if any(filename.endswith(x) for x in ['.mp3', '.wav', '.ogg', '.flac']):
        return 'page_white_sound.png'
    if any(filename.endswith(x) for x in ['.doc', '.docx']):
        return 'page_white_word.png'
    return 'page_white.png'


if __name__ == '__main__':
    wf = Workflow(
        update_settings={'github_slug': 'fniephaus/alfred-dropbox'},
        help_url='https://github.com/fniephaus/alfred-dropbox/issues'
    )
    log = wf.logger
    sys.exit(wf.run(main))
