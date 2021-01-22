from bson.objectid import ObjectId
from pymongo.errors import InvalidId


def is_object_id(id: str):
    try:
        id = ObjectId(id)
        return id
    except InvalidId:
        return False


def is_exist_obj(Obj: object, id: str):
    """
    模型类Obj中是否存在id=id 的对象
    :param Obj: 验证类
    :param sorce_id: 验证id
    :return:
    :failure:
        Flase: id 非法或id不存在
    :success:
        obj ：查询到的对象
    """
    obj_id = is_object_id(id)
    if not obj_id:
        return False
    obj = Obj.objects(id=id).first()
    if not object:
        return False
    return obj


def text_search(model: object, options: dict, fields: dict, text: str, order: list, page: int, page_size: int,):
    if text:
        options['$or'] = [
            {key: {'$regex': '|'.join(text.split(' '))}} for key in fields.keys()
        ]
    query_list = model.objects(__raw__=options).order_by(*order)[(page - 1) * page_size:page * page_size]
    total = query_list.count()
    return query_list, total
