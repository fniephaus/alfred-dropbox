import sys
import os
import datetime
from email.utils import parsedate
import time
from workflow import Workflow, PasswordNotFound, ICON_TRASH
from dropbox import client, rest
import config


def main(wf):
    user_input = ''.join(wf.args)

    try:
        wf.get_password('dropbox_access_token')
        file_or_folder = get_file_or_folder(user_input)

        if len(file_or_folder) > 0:
            for f in file_or_folder:
                if user_input == f['path']:
                    wf.add_item(
                        'Share', 'Copy link to clipboard', arg='share ' + f['path'], icon='dbicons/folder_public.png', valid=True)
                    wf.add_item(
                        'Save to Downloads', arg='download ' + f['path'], icon='icons/download.png', valid=True)
                    wf.add_item(
                        'Save to Desktop', arg='desktop ' + f['path'], icon='icons/desktop.png', valid=True)
                    wf.add_item(
                        'Delete', arg='delete ' + f['path'], icon=ICON_TRASH, valid=True)
                else:
                    title = os.path.basename(f['path'])
                    subtitle = 'Modified: ' + \
                        time.strftime(
                            '%Y-%m-%d %H:%M:%S', parsedate(f['modified']))
                    icon = 'dbicons/' + f['icon'] + '.png'
                    if f['is_dir']:
                        title += '/'
                        wf.add_item(
                            title, subtitle, icon=icon, autocomplete=f['path'] + '/', valid=False)
                    else:
                        title += ' (' + f['size'] + ')'
                        wf.add_item(
                            title, subtitle, icon=icon, autocomplete=f['path'], valid=False)
        else:
            wf.add_item(
                'No files were found.', 'Try a different request!', valid=False)

    except PasswordNotFound:
        wf.add_item(
            'Please press enter and click on "Allow" on Dropbox\'s website', 'Then use the code to authorize the workflow.', arg='url ' + get_auth_url(), valid=True)
        wf.add_item(
            'Authorize with "%s"' % user_input, 'Press enter to proceed.', arg='auth ' + user_input, valid=True)

    wf.send_feedback()


def get_file_or_folder(path='/'):
    if len(path) > 1 and path[-1] == '/':
        path = path[:-1]
    access_token = wf.get_password('dropbox_access_token')
    api_client = client.DropboxClient(access_token)
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
            log.debug(last_path)
            log.debug(query)
            output = api_client.search(last_path, query, file_limit=100)

    return output


def get_auth_url():
    flow = client.DropboxOAuth2FlowNoRedirect(
        config.APP_KEY, config.APP_SECRET)
    return flow.start()


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
