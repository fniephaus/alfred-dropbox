import sys
import os
from AppKit import NSPasteboard, NSArray
import webbrowser
from workflow import Workflow
from dropbox import client, rest
import config


def main(wf):
    user_input = ''.join(wf.args)

    command = user_input.split()[0]
    path = args.query[len(command) + 1:]

    if command == "share":
        return share_path(path)
    elif command == "download":
        return download_path(path)
    elif command == "desktop":
        return download_path(path, '~/Desktop/')
    elif command == "delete":
        return delete_path(path)
    elif command == "url":
        webbrowser.open(path)
        return 0
    elif command == "auth":
        return authorize(path)

    print 'An error occured.'
    return 0


def share_path(path):
    access_token = wf.get_password('dropbox_access_token')
    api_client = client.DropboxClient(access_token)
    try:
        url = api_client.share(path)['url']

        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        a = NSArray.arrayWithObject_(url)
        pb.writeObjects_(a)

        print 'Link copied to clipboard'

    except rest.ErrorResponse, e:
        print e.user_error_msg or str(e)

    return 0


def download_path(path, target='~/Downloads/'):
    access_token = wf.get_password('dropbox_access_token')
    api_client = client.DropboxClient(access_token)
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

        f, metadata = api_client.get_file_and_metadata(path)
        to_file.write(f.read())

        os.popen('open -R "%s"' % to_file_path)

        print '%s saved to %s' % (filename, target)

    except rest.ErrorResponse, e:
        print e.user_error_msg or str(e)

    return 0


def delete_path(path):
    access_token = wf.get_password('dropbox_access_token')
    api_client = client.DropboxClient(access_token)
    try:
        self.api_client.file_delete(path)
        print 'File deleted successfully'
    except rest.ErrorResponse, e:
        print e.user_error_msg or str(e)

    return 0


def authorize(auth_code):
    flow = client.DropboxOAuth2FlowNoRedirect(
        APP_KEY, APP_SECRET)

    try:
        access_token, user_id = flow.finish(auth_code)
        wf.save_password(
            'dropbox_access_token', access_token)
        print 'Authorization successful'
    except dbrest.ErrorResponse, e:
        print 'Error: %s' % (e,)

    return 0


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
