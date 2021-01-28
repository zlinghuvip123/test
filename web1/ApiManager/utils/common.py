import io
import json
from json import JSONDecodeError
import stat
import time
import yaml
import socket
from django.db.models import Sum
from djcelery.models import PeriodicTask
from django.conf import settings

from ApiManager.utils.operation import *
from ApiManager.utils.task_opt import create_task
from chardet.universaldetector import UniversalDetector
import traceback


logger = logging.getLogger('UIH Interface Assembler')


def type_change(type, value):
    """
    数据类型转换
    :param type: str: 类型
    :param value: object: 待转换的值
    :return: ok or error
    """
    try:
        if type == 'float':
            value = float(value)
        elif type == 'int':
            value = int(value)
        elif type == "file":
            value = [value]
    except ValueError:
        logger.error('{value}转换{type}失败'.format(value=value, type=type))
        return 'exception'
    if type == 'boolean':
        if value == 'False':
            value = False
        elif value == 'True':
            value = True
        else:
            return 'exception'

    return value


def key_value_list(keyword, **kwargs):
    """
    dict change to list
    :param keyword: str: 关键字标识
    :param kwargs: dict: 待转换的字典
    :return: ok or tips
    """
    if not isinstance(kwargs, dict) or not kwargs:
        return None
    else:
        lists = []
        test = kwargs.pop('test')
        for value in test:
            # 是否需要在这里修改，前端传过来之前就保留之前的格式？
            if keyword == 'setup_hooks':
                if value.get('key') != '':
                    lists.append(value.get('key'))
            elif keyword == 'teardown_hooks':
                if value.get('value') != '':
                    lists.append(value.get('value'))
            else:
                key = value.pop('key')
                val = value.pop('value')
                if 'type' in value.keys():
                    type = value.pop('type')
                else:
                    type = 'str'
                tips = '{keyword}: {val}格式错误,不是{type}类型'.format(keyword=keyword, val=val, type=type)
                if key != '':
                    if keyword == 'validate':
                        vTemp = {}
                        tmp = []
                        tmp.append(key)
                        msg = type_change(type, val)
                        if msg == 'exception':
                            return tips
                        tmp.append(msg)
                        #tmp.append(key)
                        vTemp[value["comparator"]] = tmp
                        value = vTemp
                    elif keyword == 'extract':
                        value[key] = val
                    elif keyword == 'variables':
                        if type == "file":
                            #参数类型是文件类型时，将key值赋值为FFF
                            project = kwargs.get("project", "")
                            module = kwargs.get("module", "")
                            tmp = val
                            val = get_file_path(project, module, val)
                            if not val:
                                return '项目：[{project}]模块:[{module}]中不存在文件[{file}],请确认！'.format(project=project,
                                                                                               file=tmp, module=module)
                            #val = os.path.join('upload', project, module, val)
                        msg = type_change(type, val)
                        if msg == 'exception':
                            return tips
                        value[key] = msg
                    elif keyword == 'parameters':
                        try:
                            if '[' in value and ']' in val:
                                value[key] = eval(val)
                            else: #file
                                value[key] = val
                        except Exception:
                            logging.error('{val}->eval 异常'.format(val=val))
                            return '{keyword}: {val}格式错误'.format(keyword=keyword, val=val)

                lists.append(value)
        return lists


def key_value_dict(keyword, **kwargs):
    """
    字典二次处理
    :param keyword: str: 关键字标识
    :param kwargs: dict: 原字典值
    :return: ok or tips
    """
    if not isinstance(kwargs, dict) or not kwargs:
        return None
    else:
        dicts = {}
        test = kwargs.pop('test')
        for value in test:
            key = value.pop('key')
            val = value.pop('value')
            if 'type' in value.keys():
                type = value.pop('type')
            else:
                type = 'str'

            if key != '':
                if keyword == 'headers':
                    value[key] = val
                elif keyword == 'data':
                    if type == "file":
                        project = kwargs.get("project", "")
                        module = kwargs.get("module", "")
                        #将文件路径组装成完整的路径（upload/project/module）
                        #为什么使用list, 在传参数的是，可能给url，可能直接给字符串，如果变量值是str，则完全是字符串
                        #否则传参过来是文件名
                        file_path = get_file_path(project, module, val)
                        if not file_path:
                            return '项目：[{project}]模块:[{module}]中不存在文件[{file}],请确认！'.format(project=project, file=val, module=module)
                        #file_path = os.path.join('upload', project, module, val)
                        value[key] = [file_path]
                    else:
                        msg = type_change(type, val)
                        if msg == 'exception':
                            return '{keyword}: {val}格式错误,不是{type}类型'.format(keyword=keyword, val=val, type=type)
                        value[key] = msg
                dicts.update(value)
        return dicts


def load_modules(**kwargs):
    """
    加载对应项目的模块信息，用户前端ajax请求返回
    :param kwargs:  dict：项目相关信息
    :return: str: module_info
    """
    belong_project = kwargs.get('name').get('project')
    module_info = ModuleInfo.objects.filter(belong_project__project_name=belong_project) \
        .values_list('id', 'module_name').order_by('-create_time')
    module_info = list(module_info)
    string = ''
    for value in module_info:
        string = string + str(value[0]) + '^=' + value[1] + 'replaceFlag'
    return string[:len(string) - 11]


def load_testsuites(**kwargs):
    """
    加载对应项目的模块信息，用户前端ajax请求返回
    :param kwargs:  dict：项目相关信息
    :return: str: module_info
    """
    belong_project = kwargs.get('name').get('project')
    module_info = TestSuite.objects.filter(belong_project__project_name=belong_project) \
        .values_list('id', 'suite_name').order_by('-create_time')
    module_info = list(module_info)
    string = ''
    for value in module_info:
        string = string + str(value[0]) + '^=' + value[1] + 'replaceFlag'
    return string[:len(string) - 11]


def load_cases(type=1, **kwargs):
    """
    加载指定项目模块下的用例
    :param kwargs: dict: 项目与模块信息
    :return: str: 用例信息
    """
    belong_project = kwargs.get('name').get('project')
    module = kwargs.get('name').get('module')
    if module == '请选择':
        return ''
    case_info = TestCaseInfo.objects.filter(belong_project=belong_project, belong_module=module, type=type). \
        values_list('id', 'name').order_by('-create_time')
    case_info = list(case_info)
    string = ''
    for value in case_info:
        string = string + str(value[0]) + '^=' + value[1] + 'replaceFlag'
    return string[:len(string) - 11]


def module_info_logic(type=True, **kwargs):
    """
    模块信息逻辑处理
    :param type: boolean: True:默认新增模块
    :param kwargs: dict: 模块信息
    :return:
    """
    if kwargs.get('module_name') is '':
        return '模块名称不能为空'
    if kwargs.get('belong_project') == '请选择':
        return '请选择项目，没有请先添加哦'
    if kwargs.get('test_user') is '':
        return '测试人员不能为空'
    return add_module_data(type, **kwargs)


def project_info_logic(type=True, **kwargs):
    """
    项目信息逻辑处理
    :param type: boolean:True 默认新增项目
    :param kwargs: dict: 项目信息
    :return:
    """
    if kwargs.get('project_name') is '':
        return '项目名称不能为空'
    if kwargs.get('responsible_name') is '':
        return '负责人不能为空'
    if kwargs.get('test_user') is '':
        return '测试人员不能为空'
    if kwargs.get('dev_user') is '':
        return '开发人员不能为空'
    if kwargs.get('publish_app') is '':
        return '发布应用不能为空'

    return add_project_data(type, **kwargs)


def case_info_logic(type=True, **kwargs):
    """
    用例信息逻辑处理以数据处理
    :param type: boolean: True 默认新增用例信息， False: 更新用例
    :param kwargs: dict: 用例信息
    :return: str: ok or tips
    """
    test = kwargs.pop('test')
    '''
        动态展示模块
    '''
    if 'request' not in test.keys():
        type = test.pop('type')
        if type == 'module':
            return load_modules(**test)
        elif type == 'case':
            return load_cases(**test)
        else:
            return load_cases(type=2, **test)

    else:
        logging.info('用例原始信息: {kwargs}'.format(kwargs=kwargs))
        if test.get('name').get('case_name') is '':
            return '用例名称不可为空'
        if test.get('name').get('module') == '请选择':
            return '请选择或者添加模块'
        if test.get('name').get('project') == '请选择':
            return '请选择项目'
        if test.get('name').get('project') == '':
            return '请先添加项目'
        if test.get('name').get('module') == '':
            return '请添加模块'

        name = test.pop('name')
        test.setdefault('name', name.pop('case_name'))

        test.setdefault('case_info', name)

        validate = test.pop('validate')
        if validate:
            validate_list = key_value_list('validate', **validate)
            if not isinstance(validate_list, list):
                return validate_list
            test.setdefault('validate', validate_list)

        extract = test.pop('extract')
        if extract:
            test.setdefault('extract', key_value_list('extract', **extract))

        request_data = test.get('request').pop('request_data')
        data_type = test.get('request').pop('type')
        if request_data and data_type:
            if data_type == 'json':
                test.get('request').setdefault(data_type, request_data)
            else:
                request_data.setdefault("project", name.get('project'))
                request_data.setdefault("module", ModuleInfo.objects.get(id=name.get('module')).module_name)
                data_dict = key_value_dict('data', **request_data)
                if not isinstance(data_dict, dict):
                    return data_dict
                test.get('request').setdefault(data_type, data_dict)

        headers = test.get('request').pop('headers')
        if headers:
            test.get('request').setdefault('headers', key_value_dict('headers', **headers))

        variables = test.pop('variables')

        if variables:
            variables.setdefault("project", name.get('project'))
            variables.setdefault("module", ModuleInfo.objects.get(id=name.get('module')).module_name)
            variables_list = key_value_list('variables', **variables)
            if not isinstance(variables_list, list):
                return variables_list
            test.setdefault('variables', variables_list)

        parameters = test.pop('parameters')
        if parameters:
            params_list = key_value_list('parameters', **parameters)
            if not isinstance(params_list, list):
                return params_list
            test.setdefault('parameters', params_list)

        hooks = test.pop('hooks')
        if hooks:

            setup_hooks_list = key_value_list('setup_hooks', **hooks)
            if not isinstance(setup_hooks_list, list):
                return setup_hooks_list
            test.setdefault('setup_hooks', setup_hooks_list)

            teardown_hooks_list = key_value_list('teardown_hooks', **hooks)
            if not isinstance(teardown_hooks_list, list):
                return teardown_hooks_list
            test.setdefault('teardown_hooks', teardown_hooks_list)

        kwargs.setdefault('test', test)
        return add_case_data(type, **kwargs)


def config_info_logic(type=True, **kwargs):
    """
    模块信息逻辑处理及数据处理
    :param type: boolean: True 默认新增 False：更新数据
    :param kwargs: dict: 模块信息
    :return: ok or tips
    """
    config = kwargs.pop('config')
    '''
        动态展示模块
    '''
    if 'request' not in config.keys():
        return load_modules(**config)
    else:
        logging.debug('配置原始信息: {kwargs}'.format(kwargs=kwargs))
        if config.get('name').get('config_name') is '':
            return '配置名称不可为空'
        if config.get('name').get('author') is '':
            return '创建者不能为空'
        if config.get('name').get('project') == '请选择':
            return '请选择项目'
        if config.get('name').get('module') == '请选择':
            return '请选择或者添加模块'
        if config.get('name').get('project') == '':
            return '请先添加项目'
        if config.get('name').get('module') == '':
            return '请添加模块'

        name = config.pop('name')
        config.setdefault('name', name.pop('config_name'))

        config.setdefault('config_info', name)

        # Update: 配置文件中只需要添加变量即可，其它的暂时不需要。

        request_data = config.get('request').pop('request_data')
        data_type = config.get('request').pop('type')
        if request_data and data_type:
            if data_type == 'json':
                config.get('request').setdefault(data_type, request_data)
            else:
                data_dict = key_value_dict('data', **request_data)
                if not isinstance(data_dict, dict):
                    return data_dict
                config.get('request').setdefault(data_type, data_dict)

        headers = config.get('request').pop('headers')
        if headers:
            config.get('request').setdefault('headers', key_value_dict('headers', **headers))

        variables = config.pop('variables')
        if variables:
            variables_list = key_value_list('variables', **variables)
            if not isinstance(variables_list, list):
                return variables_list
            config.setdefault('variables', variables_list)


        parameters = config.pop('parameters')
        if parameters:
            params_list = key_value_list('parameters', **parameters)
            if not isinstance(params_list, list):
                return params_list
            config.setdefault('parameters', params_list)

        hooks = config.pop('hooks')
        if hooks:

            setup_hooks_list = key_value_list('setup_hooks', **hooks)
            if not isinstance(setup_hooks_list, list):
                return setup_hooks_list
            config.setdefault('setup_hooks', setup_hooks_list)

            teardown_hooks_list = key_value_list('teardown_hooks', **hooks)
            if not isinstance(teardown_hooks_list, list):
                return teardown_hooks_list
            config.setdefault('teardown_hooks', teardown_hooks_list)


        kwargs.setdefault('config', config)
        return add_config_data(type, **kwargs)


def task_logic(**kwargs):
    """
    定时任务逻辑处理
    :param kwargs: dict: 定时任务数据
    :return:
    """
    if 'task' in kwargs.keys():
        if kwargs.get('task').get('type') == 'module':
            return load_modules(**kwargs.pop('task'))
        else:
            return load_testsuites(**kwargs.pop('task'))
    if kwargs.get('name') is '':
        return '任务名称不可为空'
    elif kwargs.get('project') is '':
        return '请选择一个项目'
    elif kwargs.get('crontab_time') is '':
        return '定时配置不可为空'
    elif not kwargs.get('module'):
        kwargs.pop('module')

    try:
        crontab_time = kwargs.pop('crontab_time').split(' ')
        if len(crontab_time) > 5:
            return '定时配置参数格式不正确'
        crontab = {
            'day_of_week': crontab_time[-1],
            'month_of_year': crontab_time[3],  # 月份
            'day_of_month': crontab_time[2],  # 日期
            'hour': crontab_time[1],  # 小时
            'minute': crontab_time[0],  # 分钟
        }
    except Exception:
        return '定时配置参数格式不正确'
    if PeriodicTask.objects.filter(name__exact=kwargs.get('name')).count() > 0:
        return '任务名称重复，请重新命名'
    desc = " ".join(str(i) for i in crontab_time)
    name = kwargs.get('name')
    mode = kwargs.pop('mode')

    if 'module' in kwargs.keys():
        kwargs.pop('project')

        if mode == '1':
            return create_task(name, 'ApiManager.tasks.module_hrun', kwargs, crontab, desc)
        else:
            kwargs['suite'] = kwargs.pop('module')
            return create_task(name, 'ApiManager.tasks.suite_hrun', kwargs, crontab, desc)
    else:
        return create_task(name, 'ApiManager.tasks.project_hrun', kwargs, crontab, desc)


def set_filter_session(request):
    """
    update session
    :param request:
    :return:
    """
    request.session['url'] = request.path
    if 'user' in request.POST.keys():
        request.session['user'] = request.POST.get('user')
    if 'name' in request.POST.keys():
        request.session['name'] = request.POST.get('name')
    if 'project' in request.POST.keys():
        request.session['project'] = request.POST.get('project')
    if 'module' in request.POST.keys():
        try:
            request.session['module'] = ModuleInfo.objects.get(id=request.POST.get('module')).module_name
        except Exception:
            request.session['module'] = request.POST.get('module')
    if 'report_name' in request.POST.keys():
        request.session['report_name'] = request.POST.get('report_name')

    if 'ca_user' in request.POST.keys():
        request.session['ca_user'] = request.POST.get('ca_user')

    if 'keyword' in request.POST.keys():
        request.session['keyword'] = request.POST.get('keyword')

    filter_query = {
        'user': request.session.get("user", ""),
        'name': request.session.get("name", ""),
        'belong_project': request.session.get("project", ""),
        'belong_module': request.session.get("module", ""),
        'report_name': request.session.get("report_name", ""),
        'ca_user': request.session.get("ca_user", ""),
        'keyword': request.session.get("keyword", "")

    }

    return filter_query


def init_filter_session(request, type=True):
    """
    init session
    :param request:
    :return:
    """
    if type:
        request.session['user'] = ''
        request.session['name'] = ''
        request.session['project'] = 'All'
        request.session['module'] = '请选择'
        request.session['report_name'] = ''
        request.session['keyword'] = ''
    else:
        del request.session['user']
        del request.session['name']
        del request.session['project']
        del request.session['module']
        del request.session['report_name']
        del request.session["base_url"]
        del request.session["cfg_id"]


def get_ajax_msg(msg, success):
    """
    ajax提示信息
    :param msg: str：msg
    :param success: str：
    :return:
    """
    return success if msg is 'ok' else msg


def register_info_logic(**kwargs):
    """

    :param kwargs:
    :return:
    """
    return add_register_data(**kwargs)


def upload_file_logic(files, project, module, account):
    """
    解析yaml或者json用例
    :param files:
    :param project:
    :param module:
    :param account:
    :return:
    """

    for file in files:
        file_suffix = os.path.splitext(file)[1].lower()
        if file_suffix == '.json':
            with io.open(file, encoding='utf-8') as data_file:
                try:
                    content = json.load(data_file)
                except JSONDecodeError:
                    err_msg = u"JSONDecodeError: JSON file format error: {}".format(file)
                    logging.error(err_msg)

        elif file_suffix in ['.yaml', '.yml']:
            with io.open(file, 'r', encoding='utf-8') as stream:
                content = yaml.load(stream)

        for test_case in content:
            test_dict = {
                'project': project,
                'module': module,
                'author': account,
                'include': []
            }
            if 'config' in test_case.keys():
                test_case.get('config')['config_info'] = test_dict
                add_config_data(type=True, **test_case)

            if 'test' in test_case.keys():  # 忽略config
                test_case.get('test')['case_info'] = test_dict

                if 'validate' in test_case.get('test').keys():  # 适配validate两种格式
                    validate = test_case.get('test').pop('validate')
                    new_validate = []
                    for check in validate:
                        if 'comparator' not in check.keys():
                            for key, value in check.items():
                                tmp_check = {"check": value[0], "comparator": key, "expected": value[1]}
                                new_validate.append(tmp_check)

                    test_case.get('test')['validate'] = new_validate

                add_case_data(type=True, **test_case)


def get_total_values():
    total = {
        'pass': [],
        'fail': [],
        'percent': []
    }
    today = datetime.date.today()
    for i in range(-11, 1):
        begin = today + datetime.timedelta(days=i)
        end = begin + datetime.timedelta(days=1)

        total_run = TestReports.objects.filter(create_time__range=(begin, end)).aggregate(testRun=Sum('testsRun'))[
            'testRun']
        total_success = TestReports.objects.filter(create_time__range=(begin, end)).aggregate(success=Sum('successes'))[
            'success']

        if not total_run:
            total_run = 0
        if not total_success:
            total_success = 0

        total_percent = round(total_success / total_run * 100, 2) if total_run != 0 else 0.00
        total['pass'].append(total_success)
        total['fail'].append(total_run - total_success)
        total['percent'].append(total_percent)

    return total


def update_include(include_list):
    ret = []
    for include in include_list:
        if isinstance(include, dict):
            id = include['config'][0]
            source_name = include['config'][1]
            try:
                status = include['config'][2]
            except:
                status = "启用中"
            try:
                name = TestCaseInfo.objects.get(id=id).name
            except ObjectDoesNotExist:
                logger.warning('依赖的 {name} 用例/配置已经被删除啦！！'.format(name=source_name))
                continue

            ret.append({
                'config': [id, name, status]
            })
        else:
            id = include[0]
            source_name = include[1]
            try:
                status = include[2]
            except:
                status = "启用中"
            try:
                name = TestCaseInfo.objects.get(id=id).name
            except ObjectDoesNotExist:
                logger.warning('依赖的 {name} 用例/配置已经被删除啦！！'.format(name=source_name))
                continue
            ret.append([id, name, status])

    return ret


def timestamp_to_datetime(summary, type=True):
    if not type:
        time_stamp = int(summary["time"]["start_at"])
        summary['time']['start_datetime'] = datetime.datetime. \
            fromtimestamp(time_stamp).strftime('%Y-%m-%d %H:%M:%S')

    for detail in summary['details']:
        try:
            time_stamp = int(detail['time']['start_at'])
            detail['time']['start_at'] = datetime.datetime.fromtimestamp(time_stamp).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
        # summary的格式有变化，需要更新
        '''
        for record in detail['records']:
            try:
                time_stamp = int(record['meta_datas'][0]['request']['start_timestamp'])
                record['meta_data']['request']['start_timestamp'] = \
                    datetime.datetime.fromtimestamp(time_stamp).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
        '''
    return summary


function_regex_compile = re.compile(r"\$\{(\w+)\(([\$\w\.\-/\s=,]*)\)\}")
funcs_map = dict(执行sql语句="executeSql", 归档影像="archiveDicom", 执行bat脚本="executeBat", 执行es语句="executeES")


def convert_hooks(hooks_list):
    ret = []
    if not hooks_list:
        return ret
    for hooks in hooks_list:
        key_value = {}
        func_match = function_regex_compile.match(hooks)
        if func_match:
            func_name = func_match.group(1)
            paras = func_match.group(2)
            key_value.setdefault("value", _get_keywords_for_func(func_name, funcs_map))
            key_value.setdefault("key", paras)
        ret.append(key_value)
    return ret


def _get_keywords_for_func(func, func_map):
    for key, value in func_map.items():
        if value == func:
            return key
    else:
        return ""


def get_hook_options():
    return funcs_map.keys


def update_yaml_file(yaml_file):
    with open(yaml_file,  encoding='utf-8') as pf:
        f_content = yaml.load(pf)
        test_map = f_content[1]

        for f in f_content:
            print(f)


def get_file_path(project_name, module_name, file_name):
    project = ProjectInfo.objects.get_pro_name(project_name, False)
    module = ModuleInfo.objects.get(module_name=module_name)
    file_obj = FileInfo.objects.filter(project=project, module=module, name=file_name)
    if file_obj:
        return file_obj[0].file_path
    else:
        logging.debug("Can't find {} in project:{} and module{}".format(file_name, project_name, module_name))
        return ""

def delete_folder_recursively(dPath):
    for pf in os.listdir(dPath):
        if os.path.isfile(os.path.join(dPath, pf)):
            os.chmod(os.path.join(dPath, pf), stat.S_IWRITE)
            os.remove(os.path.join(dPath, pf))
        else:
            delete_folder_recursively(os.path.join(dPath, pf))
    os.rmdir(dPath)

def get_ca_values_for_suite(test_suite, cfg_id):
    """
    :从test_suite中获取所有的ca_id的value
    :param test_suite: 指定的test_suite
    :return: 返回suite中用到的所有ca的列表
    """
    ca_map = {}
    ca_id_list = []
    config_request = eval(TestCaseInfo.objects.get(id=cfg_id).request)
    cfg_vars_list = config_request.get("config", {}).get("variables", [])
    ca_enable = get_value_from_list(cfg_vars_list, "ca_enable")
    #不在配置文件中定义两个url,而是通过dev/master去数据库找，因为这个是公用的,如果不填，默认就是dev
    ca_type = get_value_from_list(cfg_vars_list, "ca_type", "dev").lower()
    #ca_url = cfg_vars_dict.get("ca_url", "")
    #ca_login_url = cfg_vars_dict.get("ca_login_url", "")
    #redirect_url = get_value_from_list(cfg_vars_list, "redirect_url")
    if ca_enable and ca_type:
        ca_cfg = CaCFG.objects.get(ca_type=ca_type)
        ca_login_url = ca_cfg.ca_loginurl
        ca_url = ca_cfg.ca_url
        for val in test_suite:
            case_index = val[0]
            try:
                ca_ids = get_ca_ids(case_index)
                for ca_id in ca_ids:
                    if not ca_id in ca_id_list:
                        ca_id_list.append(ca_id)
                        ca_obj = CaInfo.objects.get(id=ca_id)
                        urlorpattern = ca_obj.redirect_url
                        redirect_url = parse_redirect_url(urlorpattern, cfg_vars_list)
                        ca_map[ca_id] = get_ca(ca_login_url, ca_url, ca_obj.user_name, ca_obj.password, ca_obj.client_id, redirect_url)
            except ObjectDoesNotExist:
                continue
    return ca_map

def get_ca_ids(case_id):
    '''
    :根据给定的case的id找到case中用到的所有的ca的id（包含前提条件的ca id）
    :param case_id: 用例的id
    :return: 返回所有ca id的列表（去重过的）。
    '''
    ca_id_list = []
    try:
        obj = TestCaseInfo.objects.get(id=case_id)
    except ObjectDoesNotExist:
        return ca_id_list
    if obj.ca:
        ca_id_list.append(obj.ca.id)
    include = eval(obj.include)
    for test_info in include:
        if not isinstance(test_info, dict):
            case_id = test_info[0]
            try:
                obj = TestCaseInfo.objects.get(id=case_id)
                if obj.ca:
                    ca_id_list.append(obj.ca.id)
            except ObjectDoesNotExist:
                continue
    return list(set(ca_id_list))

def get_value_from_list(key_value_list, key, default=''):
    '''
    :从字典列表中找出对应Key的值
    :param key_value_list: [dict, dict...]
    :param key: 需要查找的key
    :param default: 默认值
    :return: 返回对应key 的值，如果没有找到，则返回默认值
    '''
    for kv in key_value_list:
        if key in kv.keys():
            return kv[key]
    else:
        return default

def get_ca_values_for_case(case_id, cfg_id):
    """
    :从test_suite中获取所有的ca_id的value
    :param test_suite: 指定的test_suite
    :return: 返回ca_id的列表
    """
    ca_map = {}
    config_request = eval(TestCaseInfo.objects.get(id=cfg_id).request)
    cfg_vars_list = config_request.get("config", {}).get("variables", [])
    ca_enable = get_value_from_list(cfg_vars_list, "ca_enable")
    #不在配置文件中定义两个url,而是通过dev/master去数据库找，因为这个是公用的,如果不填，默认就是dev
    ca_type = get_value_from_list(cfg_vars_list, "ca_type", "dev").lower()
    #ca_url = cfg_vars_dict.get("ca_url", "")
    #ca_login_url = cfg_vars_dict.get("ca_login_url", "")
    #redirect_url = get_value_from_list(cfg_vars_list, "redirect_url")
    if ca_enable and ca_type:
        ca_cfg = CaCFG.objects.get(ca_type=ca_type)
        ca_login_url = ca_cfg.ca_loginurl
        ca_url = ca_cfg.ca_url
        for ca_id in get_ca_ids(case_id):
            ca_obj = CaInfo.objects.get(id=ca_id)
            urlorpattern = ca_obj.redirect_url
            redirect_url = parse_redirect_url(urlorpattern, cfg_vars_list)
            ca_map[ca_id] = get_ca(ca_login_url, ca_url, ca_obj.user_name, ca_obj.password, ca_obj.client_id,
                                   redirect_url)
    return ca_map

import validators
def parse_redirect_url(urlorpattern, cfg_vars_list):
    '''
    :parse url from cainfo and then get the value from cfg
    :param urlorpattern: url or pattern of url var
    :param cfg_vars_list: variables of cfg
    :return: redirect_url
    '''
    if validators.url(urlorpattern):# 如果填写的是完整的url地址，则不需要替换
        return urlorpattern
    else:
        pa = re.compile('@@@(.*)@@@')
        match = pa.search(urlorpattern)
        if match:
            var_redirect_url = match.group(1)
            return get_value_from_list(cfg_vars_list, var_redirect_url, "notfoundincfg")
        else:#如果没有匹配到，直接返回空
            return 'patternwrong'

def get_cacfg(**kwargs):
    """
    加载对应ca_type的ca_url和ca_loginurl
    :param kwargs:  dict：ca_type
    :return: str: ca_url + "replaceFlag" + ca_loginurl
    """
    ca_type = kwargs.get('ca_type', '')
    try:
        ca_info_obj = CaCFG.objects.get(ca_type=ca_type)
        return ca_info_obj.ca_url + 'replaceFlag' + ca_info_obj.ca_loginurl
    except:
        return "nourlreplaceFlagnourl"


def get_encode_type(filePath):
    '''
    通过读取文件内容判断获取文件的编码方式
    :param filePath: 需要获取编码方式的文件路径（绝对路径）
    :return: 文件编码方式
    '''
    bigdata = open(filePath,'rb')
    detector = UniversalDetector()
    for line in bigdata.readlines():
        detector.feed(line)
        if detector.done:
            break
    detector.close()
    bigdata.close()
    return _get_unified_encode_type(detector.result['encoding'])


def _get_unified_encode_type(sType):
    '''
    统一化文件的编码方式
    :param sType: 通过UniversalDetector获取的文件编码方式
    :return: utf-8或者gbk
    '''
    sType = sType.lower()
    if sType in ['utf-8-sig', 'utf-8'] or 'utf' in sType:
        return 'utf-8'
    elif sType in ['gb2312'] or 'gb' in sType:
        return 'gbk'
    else:
        return sType

def change_file_encoding(filePath):
    '''
    强制修改文件的编码格式，先通过文件获取文件的编码方式，然后通过该方式读取文件内容，最后以utf-8的格式强行写入文件。
    :param filePath: 需要转换格式的文件路径。
    :return: 无返回值（如果文件没有中文，则显示文件编码方式未ascii,有中文，则编码方式为utf8）
    '''
    _, type = os.path.splitext(filePath)
    if type not in ['.txt', '.sql']:
        return
    fType = get_encode_type(filePath)
    if fType in ['utf-8', 'ascii']:  #如果是utf-8或者ascii（不可能又中文）的，则不用转换
        return
    tmp = "tmp%s.txt" %(str(time.time()))
    with open(tmp, 'w', encoding='utf8') as fw:
        with open(filePath, 'r', encoding=fType) as fr:
            for line in fr.readlines():
                fw.write(line)
    os.remove(filePath)
    os.rename(tmp, filePath)


def add_report_link(filePath, reportUrl):
    '''
    在report文件的中通过添加一个id为url的tag（a），将报告的链接加入，供Jenkins报告解析时使用。
    :param filePath:  接口测试生成的报告
    :param reportUrl: 报告在接口测试平台上的链接。
    :return: 无返回值
    '''
    with open(filePath, encoding='utf-8') as pf:
        soup = BeautifulSoup(pf,'html.parser')
        new_tag = soup.new_tag('a', id='url', href=reportUrl)
        soup.body.append(new_tag)

    tmp = os.path.join(settings.BASE_DIR, "tmp{}.html".format(str(time.time())))
    print(tmp)
    with open(tmp, 'w', encoding='utf8') as pf:
        pf.write(str(soup))
    os.remove(filePath)
    os.rename(tmp, filePath)

def get_host_ip_port():
    '''
    获取当前服务器的IP
    :return:  当前服务器的IP
    '''
    ip = ''
    port = ''
    try:
        ip = settings.SERVER_IP
    except:
        pass
    try:
        port = settings.SERVER_PORT
    except:
        pass
    if not ip:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
    if not port:
        port = '80'
    return ip, port


def delete_recursively(dPath):
    try:
        for pf in os.listdir(dPath):
            if os.path.isfile(os.path.join(dPath, pf)):
                os.chmod(os.path.join(dPath, pf), stat.S_IWRITE)
                os.remove(os.path.join(dPath, pf))
            else:
                delete_recursively(os.path.join(dPath, pf))
        os.rmdir(dPath)
    except:
        traceback.print_exc()



