#!/usr/bin/python
from os import environ as env
import os
import random, string, logging


class DevelopmentConfig:
    pass


class TestingConfig(DevelopmentConfig):
    pass


for name in env:
    if len(env[name]) and env[name][0] == ',':
        setattr(DevelopmentConfig, name.strip(), [v for v in env[name].split(",") if v])
    elif len(env[name]) >= 6 and env[name].strip()[0:6] == '_int_:':
        setattr(DevelopmentConfig, name.strip(), int(env[name].strip()[6:]))
    elif len(env[name]) >= 7 and env[name].strip()[0:7] == '_eval_:':
        setattr(DevelopmentConfig, name.strip(), eval(env[name].strip()[7:]))
    else:
        setattr(DevelopmentConfig, name.strip(), env[name].strip())


def get_scc_config():
    return globals()['DevelopmentConfig']

app_config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig
}

if __name__ == '__main__':
    # get_scc_config()
    print(dir(DevelopmentConfig))
    data = DevelopmentConfig.OAUTH_CREDENTIALS
    data1 = DevelopmentConfig.FORM_META_LOCALES
    print(type(data), data)
    print(type(data1), data1)
