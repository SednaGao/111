

from app.models_mongo import BaseDocument
from bson.objectid import ObjectId


def test():
    item = BaseDocument(**{'a': 'a', 'b': 'b', 'c': ObjectId()})
    item.save()
    print(item.to_dict())


if __name__ == '__main__':
    test()
