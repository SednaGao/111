import enum

from flask_sqlalchemy import SQLAlchemy
from flask_mongoengine import MongoEngine

from config.config import DevelopmentConfig

uri = DevelopmentConfig.DATABASE_URI


class EngineType(enumerate):
    SQLEngine = enum.auto()
    MongoEngine = enum.auto()


def get_db():
    if not uri:
        raise Exception('DATABASE_URI is a must config')
    if uri.startswith('mongo'):
        db = MongoEngine()
        DevelopmentConfig.MONGODB_SETTINGS = {
            'host': uri
        }
        DevelopmentConfig.DATABASE_TYPE = EngineType.MongoEngine
    elif 'sql' in uri.split(':', 1)[0]:
        db = SQLAlchemy()
        DevelopmentConfig.SQLALCHEMY_DATABASE_URI = uri
        DevelopmentConfig.DATABASE_TYPE = EngineType.SQLEngine
    else:
        raise Exception("Only Mongo and SQL are supported")
    return db


db = get_db()
