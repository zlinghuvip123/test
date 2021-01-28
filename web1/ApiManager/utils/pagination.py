from django.utils.safestring import mark_safe

from ApiManager.models import ModuleInfo, TestCaseInfo, TestSuite


class PageInfo(object):
    """
    分页类
    """

    def __init__(self, current, total_item, per_items=5):
        self.__current = current
        self.__per_items = per_items
        self.__total_item = total_item

    @property
    def start(self):
        return (self.__current - 1) * self.__per_items

    @property
    def end(self):
        return self.__current * self.__per_items

    @property
    def total_page(self):
        result = divmod(self.__total_item, self.__per_items)
        if result[1] == 0:
            return result[0]
        else:
            return result[0] + 1


def customer_pager(base_url, current_page, total_page):
    """
    返回可分页的html
    :param base_url: a标签href值
    :param current_page: 当前页
    :param total_page: 总共页
    :return: html
    """
    per_pager = 11
    middle_pager = 5
    start_pager = 1
    if total_page <= per_pager:
        begin = 0
        end = total_page
    else:
        if current_page > middle_pager:
            begin = current_page - middle_pager
            end = current_page + middle_pager
            if end > total_page:
                end = total_page
        else:
            begin = 0
            end = per_pager
    pager_list = []

    if current_page <= start_pager:
        first = "<li><a href=''>首页</a></li>"
    else:
        first = "<li><a href='%s%d'>首页</a></li>" % (base_url, start_pager)
    pager_list.append(first)

    if current_page <= start_pager:
        prev = "<li><a href=''><<</a></li>"
    else:
        prev = "<li><a href='%s%d/'><<</a></li>" % (base_url, current_page - start_pager)
    pager_list.append(prev)

    for i in range(begin + start_pager, end + start_pager):
        if i == current_page:
            temp = "<li><a href='%s%d/' class='selected'>%d</a></li>" % (base_url, i, i)
        else:
            temp = "<li><a href='%s%d/'>%d</a></li>" % (base_url, i, i)
        pager_list.append(temp)
    if current_page >= total_page:
        next = "<li><a href=''>>></a></li>"
    else:
        next = "<li><a href='%s%d/'>>></a></li>" % (base_url, current_page + start_pager)
    pager_list.append(next)
    if current_page >= total_page:
        last = "<li><a href='''>尾页</a></li>"
    else:
        last = "<li><a href='%s%d/' >尾页</a></li>" % (base_url, total_page)
    pager_list.append(last)
    result = ''.join(pager_list)
    return mark_safe(result)  # 把字符串转成html语言


def get_pager_info(Model, filter_query, url, id, per_items=12):
    """
    筛选列表信息
    :param Model: Models实体类
    :param filter_query: dict: 筛选条件
    :param url:
    :param id:
    :param per_items: int: m默认展示12行
    :return:
    """
    id = int(id)
    if filter_query:
        belong_project = filter_query.get('belong_project')
        belong_module = filter_query.get('belong_module')
        name = filter_query.get('name')
        user = filter_query.get('user')
        keyword = filter_query.get('keyword')
        ca_user = filter_query.get("ca_user", "")
        report_name = filter_query.get('report_name')
        author = filter_query.get('author')


    obj = Model.objects

    search_dict = {}

    if url == '/api/file_upload/':
        if belong_project not in ['All', '请选择']:
            search_dict['project__project_name__exact'] = belong_project
        if belong_module not in ['All', '请选择']:
            search_dict['module__module_name__exact'] = belong_module
        obj = obj.filter(**search_dict)

    elif url == '/api/sdk_test/':
        if belong_project != 'All':
            obj = obj.filter(belong_project__project_name__contains=belong_project)

        elif belong_module != '请选择':
            obj = obj.filter(belong_module__module_name__contains=belong_module)

    elif url == '/api/project_list/':
        if belong_project not in ['All', '请选择']:
            search_dict['project_name__exact'] = belong_project
        if user:
            search_dict['author__icontains'] = user
        obj = obj.filter(**search_dict)


    elif url == '/api/module_list/':
        if belong_project not in ['All', '请选择']:
            search_dict['belong_project__project_name__exact'] = belong_project
        if belong_module not in ['All', '请选择']:
            search_dict['belong_module__module_name__exact'] = belong_module
        if user:
            search_dict['author__icontains'] = user
        obj = obj.filter(**search_dict)

    elif url == '/api/report_list/':
        if author:
            search_dict['author__exact'] = author
        if report_name:
            search_dict['report_name__contains'] = report_name
        obj = obj.filter(**search_dict)

    elif url == '/api/periodictask/':
        obj = obj.filter(name__contains=name).values('id', 'name', 'kwargs', 'enabled', 'date_changed') \
            if name is not '' else obj.all().values('id', 'name', 'kwargs', 'enabled', 'date_changed', 'description')

    elif url == '/api/suite_list/':
        if belong_project not in ['All', '请选择']:
            search_dict['belong_project__project_name__exact'] = belong_project
        if name:
            search_dict['name__icontains'] = name
        obj = obj.filter(**search_dict)

    elif url == '/api/ca_list/':
        if belong_project not in ['All', '请选择']:
            search_dict['belong_project__project_name__exact'] = belong_project
        obj = obj.filter(**search_dict)

    elif url != '/api/env_list/' and url != '/api/debugtalk_list/':
        if url == '/api/test_list/':
            search_dict['type__exact'] = 1
        else:
            search_dict['type__exact'] = 2
        if belong_project not in ['All', '请选择']:
            search_dict['belong_project__exact'] = belong_project
        if belong_module not in ['All', '请选择']:
            search_dict['belong_module__module_name__exact'] = belong_module
        if name:
            search_dict['name__icontains'] = name
        if user:
            search_dict['author__icontains'] = user
        if keyword:
            search_dict['request__icontains'] = keyword
        obj = obj.filter(**search_dict)

    if url != '/api/periodictask/':
        obj = obj.order_by('-update_time')

    else:
        obj = obj.order_by('-date_changed')

    total = obj.count()

    page_info = PageInfo(id, total, per_items=per_items)
    info = obj[page_info.start:page_info.end]

    sum = {}
    page_list = ''
    if total != 0:
        if url == '/api/project_list/':
            for model in info:
                pro_name = model.project_name
                module_count = str(ModuleInfo.objects.filter(belong_project__project_name__exact=pro_name).count())
                suite_count = str(TestSuite.objects.filter(belong_project__project_name__exact=pro_name).count())
                test_count = str(TestCaseInfo.objects.filter(belong_project__exact=pro_name, type__exact=1).count())
                config_count = str(TestCaseInfo.objects.filter(belong_project__exact=pro_name, type__exact=2).count())
                sum.setdefault(model.id, module_count + '/ ' + suite_count + '/' + test_count + '/ ' + config_count)

        elif url == '/api/module_list/':
            for model in info:
                module_name = model.module_name
                project_name = model.belong_project.project_name
                test_count = str(TestCaseInfo.objects.filter(belong_module__module_name=module_name,
                                                             type__exact=1, belong_project=project_name).count())
                config_count = str(TestCaseInfo.objects.filter(belong_module__module_name=module_name,
                                                               type__exact=2, belong_project=project_name).count())
                sum.setdefault(model.id, test_count + '/ ' + config_count)

        elif url == '/api/suite_list/':
            for model in info:
                suite_name = model.suite_name
                project_name = model.belong_project.project_name
                test_count = str(len(eval(TestSuite.objects.get(suite_name=suite_name,
                                                                belong_project__project_name=project_name).include)))
                sum.setdefault(model.id, test_count)

        page_list = customer_pager(url, id, page_info.total_page)

    return page_list, info, sum
