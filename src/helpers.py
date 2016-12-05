import json
import hashlib

import config

from workflow import Workflow
from dropbox import Dropbox
from dropbox.exceptions import HttpError

wf = Workflow()


def get_resource(account_id, path, is_file):
    cached_resource = wf.cached_data(get_hash(account_id, path), max_age=0)
    hash_value = None
    if cached_resource and 'hash' in cached_resource:
        hash_value = cached_resource['hash']
    access_tokens = json.loads(wf.get_password(config.TOKEN_KEY))
    dbx = Dropbox(access_tokens[account_id])
    try:
        if is_file:
            return dbx.files_get_metadata(path)
        resp = dbx.files_list_folder(path)
        if resp.has_more:
            wf.logger.debug('"%s" has more than %s entries' %
                            (path, len(resp.entries)))
        return resp.entries
    except HttpError, e:
        if e.status_code == '304':
            return cached_resource
        elif e.status_code == '404':
            return []
        else:
            wf.logger.debug(e)


def get_hash(account_id, path):
    path_hash = hashlib.md5(path.encode('utf-8')).hexdigest()
    return "_".join([account_id, path_hash])


def get_account_info():
    output = []
    for access_token in json.loads(
            wf.get_password(config.TOKEN_KEY)).values():
        dbx = Dropbox(access_token)
        account = dbx.users_get_current_account()
        space_usage = dbx.users_get_space_usage()
        output.append((account, space_usage))
    return output


def account_id_exists(account_id, accounts):
    for account in accounts:
        if account[0].account_id == account_id:
            return True
    return False
