import sys
import os
import datetime
from email.utils import parsedate
import time
from workflow import Workflow, PasswordNotFound
from dropbox import client, rest
import config


def main(wf):
    user_input = ''.join(wf.args)

    try:
        wf.get_password('dropbox_access_token')
        # user_input = '/.ws.agile.1Password.settings'
        file_or_folder = get_file_or_folder(user_input)

        for f in file_or_folder:
            if user_input == f['path']:
                wf.add_item(
                    'Share', 'Copy link to clipboard', arg='share ' + f['path'], valid=True)
                wf.add_item(
                    'Save to Downloads', arg='download ' + f['path'], valid=True)
                wf.add_item(
                    'Save to Desktop', arg='desktop ' + f['path'], valid=True)
                wf.add_item('Delete', arg='delete ' + f['path'], valid=True)
            else:
                title = os.path.basename(f['path'])
                subtitle = 'Modified: ' + \
                    time.strftime(
                        '%Y-%m-%d %H:%M:%S', parsedate(f['modified']))
                icon = 'icons/' + f['icon'] + '.png'
                if f['is_dir']:
                    title += '/'
                    wf.add_item(
                        title, subtitle, icon=icon, autocomplete=f['path'], valid=False)
                else:
                    title += ' (' + f['size'] + ')'
                    wf.add_item(
                        title, subtitle, icon=icon, autocomplete=f['path'], valid=False)

    except PasswordNotFound:
        if user_input == "":
            wf.add_item(
                'Authorize workflow', 'Website...', arg='url ' + get_auth_url(), valid=True)
        else:
            wf.add_item(
                'Authorize with "%s"' % user_input, 'Website...', arg='auth ' + user_input, valid=True)

    wf.send_feedback()


def get_file_or_folder(dir='/'):
    access_token = wf.get_password('dropbox_access_token')
    api_client = client.DropboxClient(access_token)
    try:
        resp = api_client.metadata(dir)

        output = []
        if 'contents' in resp:
            output = resp['contents']
        else:
            output.append(resp)
        wf.cache_data('last_output', output)
        return output
    except rest.ErrorResponse, e:
        return wf.cached_data('last_output')


def get_auth_url():
    flow = client.DropboxOAuth2FlowNoRedirect(
        APP_KEY, APP_SECRET)
    return flow.start()


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
