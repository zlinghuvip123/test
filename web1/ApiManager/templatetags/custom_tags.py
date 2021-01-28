import json
import re
import sys
from django import template

from ApiManager.utils.common import update_include

register = template.Library()


@register.filter(name='data_type')
def data_type(value):
    """
    返回数据类型 自建filter
    :param value:
    :return: the type of value
    """
    return str(type(value).__name__)


@register.filter(name='convert_eval')
def convert_eval(value):
    """
    数据eval转换 自建filter
    :param value:
    :return: the value which had been eval
    """
    return update_include(eval(value))


@register.filter(name='json_dumps')
def json_dumps(value):
    return json.dumps(value, indent=4, separators=(',', ': '), ensure_ascii=False)


@register.filter(name='is_del')
def id_del(value):
    if value.endswith('已删除'):
        return True
    else:
        return False

@register.filter(name='str_split')
def str_split(value, arg):
    """
    返回数据类型 自建filter
    :param value:
    :return: the type of value
    """
    #保存路径的时候，统一使用了os.path.join, 导致不同的操作系统服务器会保存不同的格式：
    # linux下会保存为a/b/v.txt
    # windows下会保存为a\b\v.txt
    tmp = arg
    if arg == "sp":
        if '/' in value:
            tmp = "/"
        else:
            tmp = "\\"
    return value.split(tmp)

@register.filter(name='str_match')
def str_match(value, arg):
    """
    返回数据类型 自建filter
    :param value:
    :return: the type of value
    """
    pa = re.compile(arg)
    mat = pa.search(value)
    if mat:
        return mat.group(1)
    else:
        return value

