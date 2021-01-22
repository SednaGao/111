# coding: utf8

from ..spider.utils import get_scc_redis


class DbOperation:
    def __init__(self):
        self.key = ''
        self.scc_redis = None

    def get_scc_redis(self):
        self.scc_redis = get_scc_redis()

    def get_list(self, search_key=''):
        """
        获取redis列表信息
        :return:
        """
        self.key = "scc-app:*:*:dupfilter:*" if search_key == '' else search_key
        hkey_list = self.scc_redis.keys(self.key)
        hash_info_list = []
        for hkey in hkey_list:
            hash_info_list.append(self.scc_redis.hgetall(hkey))

        return hash_info_list

    def del_db(self, db_name):
        """
        删除当前db
        :param db_name: 对应db名称
        :return:
            :success:
                0
        """
        self.scc_redis.delete(db_name)

        return 0
