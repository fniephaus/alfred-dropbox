import json
import os
import subprocess
import sys
import webbrowser

import config

from dropbox import Dropbox, DropboxOAuth2FlowNoRedirect
from dropbox.exceptions import HttpError
from workflow import Workflow, PasswordNotFound

DIR_DOWNLOAD = '~/Downloads/'
DIR_DESKTOP = '~/Desktop/'


def main(wf):
    user_input = ''.join(wf.args)
    command, _, query = user_input.partition(' ')
    access_token, uid, path = _parse(query)

    if access_token:
        if command == 'share':
            share_path(path, access_token)
        elif command == 'download':
            download_path(path, access_token, DIR_DOWNLOAD)
        elif command == 'desktop':
            download_path(path, access_token, DIR_DESKTOP)
        elif command == 'delete':
            delete_path(path, access_token)
        else:
            print 'Invalid command: %s' % command
    elif command == 'url':
        webbrowser.open(query)
    elif command == 'auth':
        authorize(query)
    elif command == 'remove':
        remove(uid)
    else:
        print 'An error occured for command "%s".' % command
    return 0


def _parse(query):
    if ' ' in query:
        uid, _, path = query.partition(' ')
        try:
            access_tokens = json.loads(
                wf.get_password(config.TOKEN_KEY))
            if uid in access_tokens:
                return access_tokens[uid], uid, path
        except PasswordNotFound:
            pass
    return None, None, None


def copy_to_clipboard(text):
    p = subprocess.Popen(['pbcopy', 'w'],
                         stdin=subprocess.PIPE, close_fds=True)
    p.communicate(input=text.encode('utf-8'))


def share_path(path, access_token):
    dbx = Dropbox(access_token)
    try:
        url = dbx.share(path)['url']
        copy_to_clipboard(url)
        print 'Link copied to clipboard'
    except HttpError, e:
        print (e.user_error_msg or str(e))


def download_path(path, access_token, target):
    dbx = Dropbox(access_token)

    try:
        filename = os.path.basename(path)
        to_file_path = os.path.expanduser('%s%s' % (target, filename))
        i = 1
        while os.path.isfile(to_file_path):
            (root, ext) = os.path.splitext(filename)
            to_file_path = os.path.expanduser(
                '%s%s%s%s' % (target, root, '-' + str(i), ext))
            i += 1

        to_file = open(to_file_path, "wb")

        f, metadata = dbx.get_file_and_metadata(path)
        to_file.write(f.read())

        os.popen('open -R "%s"' % to_file_path)

        print '%s saved to %s' % (filename, target)

    except HttpError, e:
        print e.body or str(e)


def delete_path(path, access_token):
    dbx = Dropbox(access_token)
    try:
        dbx.file_delete(path)
        print 'File deleted successfully'
    except HttpError, e:
        print e.body or str(e)


def authorize(auth_code):
    flow = DropboxOAuth2FlowNoRedirect(config.APP_KEY, config.APP_SECRET)
    try:
        oauth_result = flow.finish(auth_code)
        access_tokens = {}
        try:
            access_tokens = json.loads(wf.get_password(config.TOKEN_KEY))
        except PasswordNotFound:
            pass
        access_tokens[oauth_result.account_id] = oauth_result.access_token
        wf.save_password(config.TOKEN_KEY, json.dumps(access_tokens))
        wf.clear_cache()
        print 'Authorization successful'
    except HttpError, e:
        print e.body or str(e)


def remove(uid):
    try:
        access_tokens = json.loads(wf.get_password(config.TOKEN_KEY))
        access_token = access_tokens.pop(uid, None)
        dbx = Dropbox(access_token)
        dbx.disable_access_token()
        wf.save_password(config.TOKEN_KEY, json.dumps(access_tokens))
        wf.clear_cache()
        print 'Deauthorization successful'
    except PasswordNotFound:
        print 'Not access tokens found.'


if __name__ == '__main__':
    wf = Workflow()
    sys.exit(wf.run(main))
