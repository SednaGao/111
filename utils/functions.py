from jsonpath_ng.ext import parse as jparse


def find_by_jpath(data, jsonpath, get_first=False):
    if jsonpath.endswith('::first'):
        get_first = True
        jsonpath = jsonpath[:-7]
    matches = jparse(jsonpath).find(data)
    ret_list = [match.value for match in matches]
    if get_first:
        if len(ret_list):
            return ret_list[0]
        else:
            return None
    return ret_list
