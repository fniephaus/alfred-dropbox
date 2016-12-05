import sys

from workflow import Workflow
from helpers import get_resource, get_hash, get_account_info, account_id_exists

wf = Workflow()


def cache_resource(uid, path):
    def wrapper():
        return get_resource(uid, path)
    wf.cached_data(get_hash(uid, path), wrapper)


def prefetch(uid, path):
    accounts = wf.cached_data(
        'dropbox_accounts', data_func=get_account_info, max_age=60 * 60)
    if path is None or uid is None or not account_id_exists(uid, accounts):
        return 0
    path_content = wf.cached_data(get_hash(uid, path))
    if path_content is None:
        return 0
    for resource in path_content:
        if resource['is_dir']:
            cache_resource(uid, resource['path'])

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit()
    [_, uid, path] = sys.argv
    prefetch(uid, path)
