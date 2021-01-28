import datetime
import logging
import os
from bs4 import BeautifulSoup
from django.core.exceptions import ObjectDoesNotExist
from django.db import DataError
from django.conf import settings

from ApiManager import separator
from ApiManager.models import *
import requests
import re
import base64


logger = logging.getLogger('UIH Interface Assembler')


def add_register_data(**kwargs):
    """
    用户注册信息逻辑判断及落地
    :param kwargs: dict
    :return: ok or tips
    """
    user_info = UserInfo.objects
    try:
        username = kwargs.pop('account')
        password = kwargs.pop('password')
        email = kwargs.pop('email')

        if user_info.filter(username__exact=username).filter(status=1).count() > 0:
            logger.debug('{username} 已被其他用户注册'.format(username=username))
            return '该用户名已被注册，请更换用户名'
        if user_info.filter(email__exact=email).filter(status=1).count() > 0:
            logger.debug('{email} 昵称已被其他用户注册'.format(email=email))
            return '邮箱已被其他用户注册，请更换邮箱'
        user_info.create(username=username, password=password, email=email)
        logger.info('新增用户：{user_info}'.format(user_info=user_info))
        return 'ok'
    except DataError:
        logger.error('信息输入有误：{user_info}'.format(user_info=user_info))
        return '字段长度超长，请重新编辑'


def add_project_data(type, **kwargs):
    """
    项目信息落地 新建时必须默认添加debugtalk.py
    :param type: true: 新增， false: 更新
    :param kwargs: dict
    :return: ok or tips
    """
    project_opt = ProjectInfo.objects
    project_name = kwargs.get('project_name')
    if type:
        if project_opt.get_pro_name(project_name) < 1:
            try:
                def get_content_from_file(file_path):
                    with open(file_path, 'r', encoding='utf8') as pf:
                        return pf.read()
                project_opt.insert_project(**kwargs)
            except DataError:
                return '项目信息过长'
            except Exception:
                logging.error('项目添加异常：{kwargs}'.format(kwargs=kwargs))
                return '添加失败，请重试'
            logger.info('项目添加成功：{kwargs}'.format(kwargs=kwargs))
        else:
            return '该项目已存在，请重新编辑'
    else:
        if project_name != project_opt.get_pro_name('', type=False, id=kwargs.get(
                'index')) and project_opt.get_pro_name(project_name) > 0:
            return '该项目已存在， 请重新命名'
        try:
            project_opt.update_project(kwargs.pop('index'), **kwargs)  # testcaseinfo的belong_project也得更新，这个字段设计的有点坑了
        except DataError:
            return '项目信息过长'
        except Exception:
            logging.error('更新失败：{kwargs}'.format(kwargs=kwargs))
            return '更新失败，请重试'
        logger.info('项目更新成功：{kwargs}'.format(kwargs=kwargs))

    return 'ok'


'''模块数据落地'''


def add_module_data(type, **kwargs):
    """
    模块信息落地
    :param type: boolean: true: 新增， false: 更新
    :param kwargs: dict
    :return: ok or tips
    """
    module_opt = ModuleInfo.objects
    belong_project = kwargs.pop('belong_project')
    module_name = kwargs.get('module_name')
    if type:
        if module_opt.filter(belong_project__project_name__exact=belong_project) \
                .filter(module_name__exact=module_name).count() < 1:
            try:
                belong_project = ProjectInfo.objects.get_pro_name(belong_project, type=False)
            except ObjectDoesNotExist:
                logging.error('项目信息读取失败：{belong_project}'.format(belong_project=belong_project))
                return '项目信息读取失败，请重试'
            kwargs['belong_project'] = belong_project
            try:
                module_opt.insert_module(**kwargs)
            except DataError:
                return '模块信息过长'
            except Exception:
                logging.error('模块添加异常：{kwargs}'.format(kwargs=kwargs))
                return '添加失败，请重试'
            logger.info('模块添加成功：{kwargs}'.format(kwargs=kwargs))
        else:
            return '该模块已在项目中存在，请重新编辑'
    else:
        if module_name != module_opt.get_module_name('', type=False, id=kwargs.get('index')) \
                and module_opt.filter(belong_project__project_name__exact=belong_project) \
                        .filter(module_name__exact=module_name).count() > 0:
            return '该模块已存在，请重新命名'
        try:
            module_opt.update_module(kwargs.pop('index'), **kwargs)
        except DataError:
            return '模块信息过长'
        except Exception:
            logging.error('更新失败：{kwargs}'.format(kwargs=kwargs))
            return '更新失败，请重试'
        logger.info('模块更新成功：{kwargs}'.format(kwargs=kwargs))
    return 'ok'


'''用例数据落地'''


def add_case_data(type, **kwargs):
    """
    用例信息落地
    :param type: boolean: true: 添加新用例， false: 更新用例
    :param kwargs: dict
    :return: ok or tips
    """
    case_info = kwargs.get('test').get('case_info')
    case_opt = TestCaseInfo.objects
    name = kwargs.get('test').get('name')
    module = case_info.get('module')
    project = case_info.get('project')
    if not case_info.get('ca_user', '') or case_info.get('ca_user', '') == "请选择":
        ca = ''
    else:
        ca = CaInfo.objects.get(id=case_info.get('ca_user'))
    belong_module = ModuleInfo.objects.get_module_name(module, type=False)
    config = case_info.get('config', '')
    if config != '':
        case_info.get('include')[0] = eval(config)

    try:
        if type:

            if case_opt.get_case_name(name, module, project) < 1:
                case_opt.insert_case(belong_module, ca, **kwargs)
                logger.info('{name}用例添加成功: {kwargs}'.format(name=name, kwargs=kwargs))
            else:
                return '用例或配置已存在，请重新编辑'
        else:
            index = case_info.get('test_index')
            if name != case_opt.get_case_by_id(index, type=False) \
                    and case_opt.get_case_name(name, module, project) > 0:
                return '用例或配置已在该模块中存在，请重新命名'
            case_opt.update_case(belong_module, ca, **kwargs)
            logger.info('{name}用例更新成功: {kwargs}'.format(name=name, kwargs=kwargs))

    except DataError:
        logger.error('用例信息：{kwargs}过长！！'.format(kwargs=kwargs))
        return '字段长度超长，请重新编辑'
    return 'ok'

def update_test_ca(ca_id, test_list):
    msg = 'ok'
    for test_case in test_list:
        try:
            case_id = test_case.split('_')[1]
            TestCaseInfo.objects.filter(id=case_id).update(ca=CaInfo.objects.get(id=ca_id))
        except:
            msg = "添加ca失败！"
    return msg


'''配置数据落地'''


def add_config_data(type, **kwargs):
    """
    配置信息落地
    :param type: boolean: true: 添加新配置， fasle: 更新配置
    :param kwargs: dict
    :return: ok or tips
    """
    case_opt = TestCaseInfo.objects
    config_info = kwargs.get('config').get('config_info')
    name = kwargs.get('config').get('name')
    module = config_info.get('module')
    project = config_info.get('project')
    belong_module = ModuleInfo.objects.get_module_name(module, type=False)

    try:
        if type:
            if case_opt.get_case_name(name, module, project) < 1:
                case_opt.insert_config(belong_module, **kwargs)
                logger.info('{name}配置添加成功: {kwargs}'.format(name=name, kwargs=kwargs))
            else:
                return '用例或配置已存在，请重新编辑'
        else:
            index = config_info.get('test_index')
            if name != case_opt.get_case_by_id(index, type=False) \
                    and case_opt.get_case_name(name, module, project) > 0:
                return '用例或配置已在该模块中存在，请重新命名'
            case_opt.update_config(belong_module, **kwargs)
            logger.info('{name}配置更新成功: {kwargs}'.format(name=name, kwargs=kwargs))
    except DataError:
        logger.error('{name}配置信息过长：{kwargs}'.format(name=name, kwargs=kwargs))
        return '字段长度超长，请重新编辑'
    return 'ok'


def add_suite_data(**kwargs):
    belong_project = kwargs.pop('project')
    suite_name = kwargs.get('suite_name')
    kwargs['belong_project'] = ProjectInfo.objects.get(project_name=belong_project)
    include = kwargs.get("include", [])
    kwargs['disabled_cnt'] = len([x for x in include if x[2] == "暂停中"])

    try:
        if TestSuite.objects.filter(belong_project__project_name=belong_project, suite_name=suite_name).count() > 0:
            return 'Suite已存在, 请重新命名'
        TestSuite.objects.create(**kwargs)
        logging.info('suite添加成功: {kwargs}'.format(kwargs=kwargs))
    except Exception:
        return 'suite添加异常，请重试'
    return 'ok'


def edit_suite_data(**kwargs):
    id = kwargs.pop('id')
    project_name = kwargs.pop('project')
    suite_name = kwargs.get('suite_name')
    include = kwargs.pop('include')
    belong_project = ProjectInfo.objects.get(project_name=project_name)

    suite_obj = TestSuite.objects.get(id=id)
    try:
        if suite_name != suite_obj.suite_name and \
                        TestSuite.objects.filter(belong_project=belong_project, suite_name=suite_name).count() > 0:
            return 'Suite已存在, 请重新命名'
        suite_obj.suite_name = suite_name
        suite_obj.belong_project = belong_project
        suite_obj.include = get_unique_test_list(include)
        suite_obj.disabled_cnt = len([x for x in include if x[2] == "暂停中"])
        suite_obj.save()
        logging.info('suite更新成功: {kwargs}'.format(kwargs=kwargs))
    except Exception:
        return 'suite添加异常，请重试'
    return 'ok'


def get_unique_test_list(test_list):
    '''
    test suite中用例去重操作。
    :param test_list: 前端发送过来的用例列表
    :return: 去重后的用例列表
    '''
    id_list = []
    ret_list = []
    for test in test_list:
        if test[0] not in id_list:
            ret_list.append(test)
            id_list.append(test[0])
    return ret_list


def env_data_logic(**kwargs):
    """
    环境信息逻辑判断及落地
    :param kwargs: dict
    :return: ok or tips
    """
    id = kwargs.get('id', None)
    if id:
        try:
            EnvInfo.objects.delete_env(id)
        except ObjectDoesNotExist:
            return '删除异常，请重试'
        return 'ok'
    index = kwargs.pop('index')
    env_name = kwargs.get('env_name')
    if env_name is '':
        return '环境名称不可为空'
    elif kwargs.get('base_url') is '':
        return '请求地址不可为空'
    elif kwargs.get('simple_desc') is '':
        return '请添加环境描述'

    if index == 'add':
        try:
            if EnvInfo.objects.filter(env_name=env_name).count() < 1:
                EnvInfo.objects.insert_env(**kwargs)
                logging.info('环境添加成功：{kwargs}'.format(kwargs=kwargs))
                return 'ok'
            else:
                return '环境名称重复'
        except DataError:
            return '环境信息过长'
        except Exception:
            logging.error('添加环境异常：{kwargs}'.format(kwargs=kwargs))
            return '环境信息添加异常，请重试'
    else:
        try:
            if EnvInfo.objects.get_env_name(index) != env_name and EnvInfo.objects.filter(
                    env_name=env_name).count() > 0:
                return '环境名称已存在'
            else:
                EnvInfo.objects.update_env(index, **kwargs)
                logging.info('环境信息更新成功：{kwargs}'.format(kwargs=kwargs))
                return 'ok'
        except DataError:
            return '环境信息过长'
        except ObjectDoesNotExist:
            logging.error('环境信息查询失败：{kwargs}'.format(kwargs=kwargs))
            return '更新失败，请重试'


def del_module_data(id):
    """
    根据模块索引删除模块数据，强制删除其下所有用例及配置
    :param id: str or int:模块索引
    :return: ok or tips
    """
    try:
        module_name = ModuleInfo.objects.get_module_name('', type=False, id=id)
        TestCaseInfo.objects.filter(belong_module__module_name=module_name).delete()
        ModuleInfo.objects.get(id=id).delete()
    except ObjectDoesNotExist:
        return '删除异常，请重试'
    logging.info('{module_name} 模块已删除'.format(module_name=module_name))
    return 'ok'


def del_project_data(id):
    """
    根据项目索引删除项目数据，强制删除其下所有用例、配置、模块、Suite
    :param id: str or int: 项目索引
    :return: ok or tips
    """
    try:
        project_name = ProjectInfo.objects.get_pro_name('', type=False, id=id)

        belong_modules = ModuleInfo.objects.filter(belong_project__project_name=project_name).values_list('module_name')
        for obj in belong_modules:
            TestCaseInfo.objects.filter(belong_module__module_name=obj).delete()

        TestSuite.objects.filter(belong_project__project_name=project_name).delete()

        ModuleInfo.objects.filter(belong_project__project_name=project_name).delete()

        #DebugTalk.objects.filter(belong_project__project_name=project_name).delete()

        ProjectInfo.objects.get(id=id).delete()

    except ObjectDoesNotExist:
        return '删除异常，请重试'
    logging.info('{project_name} 项目已删除'.format(project_name=project_name))
    return 'ok'


def del_test_data(id):
    """
    根据用例或配置索引删除数据
    :param id: str or int: test or config index
    :return: ok or tips
    """
    try:
        TestCaseInfo.objects.get(id=id).delete()
    except ObjectDoesNotExist:
        return '删除异常，请重试'
    logging.info('用例/配置已删除')
    return 'ok'


def del_suite_data(id):
    """
    根据Suite索引删除数据
    :param id: str or int: test or config index
    :return: ok or tips
    """
    try:
        TestSuite.objects.get(id=id).delete()
    except ObjectDoesNotExist:
        return '删除异常，请重试'
    logging.info('Suite已删除')
    return 'ok'


def del_report_data(id):
    """
    根据报告索引删除报告
    :param id:
    :return: ok or tips
    """
    try:
        TestReports.objects.get(id=id).delete()
    except ObjectDoesNotExist:
        return '删除异常，请重试'
    return 'ok'


def copy_test_data(id, name, project, module, author):
    """
    复制用例信息，默认插入到当前项目、莫夸
    :param id: str or int: 复制源
    :param name: str：新用例名称
    :param project: 所属项目
    :param module: 所属模块
    :param author: 测试用例作者
    :return: ok or tips
    """
    if project == "请选择" or module == "请选择":
        return "请选择项目和模块！"
    try:
        test = TestCaseInfo.objects.get(id=id)
        belong_project = project
        belong_module = module
    except ObjectDoesNotExist:
        return '复制异常，请重试'
    if TestCaseInfo.objects.filter(name=name, belong_project=belong_project, belong_module=belong_module).count() > 0:
        return '用例/配置名称重复了哦'
    test.id = None
    test.name = name
    test.belong_project = belong_project
    test.belong_module = ModuleInfo.objects.get_module_name(module, type=False)
    test.author = author

    request = eval(test.request)
    if 'test' in request.keys():
        request.get('test')['name'] = name
    else:
        request.get('config')['name'] = name
    test.request = request
    test.save()
    logging.info('{name}用例/配置添加成功'.format(name=name))
    return 'ok'


def copy_suite_data(id, name):
    """
    复制suite信息，默认插入到当前项目、莫夸
    :param id: str or int: 复制源
    :param name: str：新用例名称
    :return: ok or tips
    """
    try:
        suite = TestSuite.objects.get(id=id)
        belong_project = suite.belong_project
    except ObjectDoesNotExist:
        return '复制异常，请重试'
    if TestSuite.objects.filter(suite_name=name, belong_project=belong_project).count() > 0:
        return 'Suite名称重复了哦'
    suite.id = None
    suite.suite_name = name
    suite.save()
    logging.info('{name}suite添加成功'.format(name=name))
    return 'ok'


def add_test_reports(runner, author="Jenkins", report_name=None):
    time_stamp = int(runner.summary["time"]["start_at"])
    runner.summary['time']['start_datetime'] = datetime.datetime.fromtimestamp(time_stamp).strftime('%Y-%m-%d %H:%M:%S')
    report_name = report_name  if report_name else "TestReport"
    report_name = report_name + "-" + runner.summary['time']['start_datetime']
    runner.summary['html_report_name'] = report_name

    report_path = os.path.join(os.getcwd(),
                               "reports{}{}.html".format(separator, int(runner.summary['time']['start_at'])))
    # runner.gen_html_report(html_report_template=os.path.join(os.getcwd(), "templates{}extent_report_template.html".format(separator)))


    #with open(report_path, encoding='utf-8') as stream:
    #    reports = stream.read()

    #保存報告的時候保存報告的原始名稱，查看的時候再讀取文件即可

    orig_report_name = "{}.html".format(int(runner.summary['time']['start_at']))
    test_reports = {
        'report_name': report_name,
        'status': runner.summary.get('success', "unstable"),
        'successes': runner.summary.get('stat').get('testcases').get('success', 0),
        'testsRun': runner.summary.get('stat').get('testcases').get('total', 0),
        'start_at': runner.summary['time']['start_datetime'],
        'reports': orig_report_name,
        'author': author
    }

    obj = TestReports.objects.create(**test_reports)
    return obj.id

def add_test_reports_testng(report_path, author="autoRun"):
    """
    保存testng生成的测试报告
    """
    tests_run, passed_cnt, start_at = parse_testng_report(report_path)
    report_name = os.path.basename(report_path)

    test_reports = {
        'report_name': report_name,
        'status': 1 if passed_cnt == tests_run else 0,
        'successes': passed_cnt,
        'testsRun': tests_run,
        'start_at':  start_at,
        'reports': report_name,
        'author': author
    }

    obj = TestReports.objects.create(**test_reports)
    return obj.id

def parse_testng_report(report_path):
    soup = BeautifulSoup(open(report_path, encoding='utf8'))
    try:
        summary = soup.find('th', text="Total").find_parent().find_all("th")
    except:
        summary = soup.find('a', href="#t0").find_parent().find_parent().find_all("td")
    passed_cnt = int(summary[1].text)
    skipped_cnt = int(summary[2].text)
    failed_cnt = int(summary[3].text)
    duration = int(summary[4].text.replace(',', ''))
    start_at = datetime.datetime.now() - datetime.timedelta(microseconds=duration)
    start_at = start_at.strftime('%Y/%m/%d %H:%M:%S')
    return passed_cnt + skipped_cnt + failed_cnt, passed_cnt, start_at

def get_test_name(id, type):
    """

    :param id:
    :param type:
    :return:
    """
    if type == 'project':
        return ProjectInfo.objects.filter(id=id)[0].project_name if ProjectInfo.objects.filter(id=id) else ""
    elif type == 'module':
        return ModuleInfo.objects.filter(id=id)[0].module_name if ModuleInfo.objects.filter(id=id) else ""
    elif type == 'suite':
        return TestSuite.objects.filter(id=id)[0].suite_name if TestSuite.objects.filter(id=id) else ""
    else:
        return TestCaseInfo.objects.filter(id=id)[0].name if TestCaseInfo.objects.filter(id=id) else ""


def add_file_data(**kwargs):
    """
    #上传文件落地
    :param kwargs:
    :return:
    """
    """
    :param kwargs:
    :return:
    """

    try:
        if FileInfo.objects.filter(project=kwargs.get('project'), module=kwargs.get('module'), name=kwargs.get('name')).count() > 0:
            return '文件已存在，请重新上传'
        FileInfo.objects.create(**kwargs)
        logging.info('文件添加成功: {kwargs}'.format(kwargs=kwargs))
    except Exception as e:
        return '文件上传异常，请重试'
    return 'ok'

def del_file_data(id):
    """
    根据上传的文件id删除文件
    :param id:
    :return: ok or tips
    """
    try:
        obj = FileInfo.objects.get(id=id)
        file_path = obj.file_path
        objfile = os.path.join(settings.BASE_DIR, file_path)
        if os.path.exists(objfile):
            os.remove(objfile)
        FileInfo.objects.get(id=id).delete()
    except ObjectDoesNotExist:
        return '删除异常，请重试'
    return 'ok'

def add_sdk_test_data(**kwargs):
    #使用pop取出kwargs中数据，防止数据库添加数据的时候，有些key不识别
    belong_project = kwargs.pop('project')
    belong_module = kwargs.pop('module')
    sdk_name = kwargs.pop('sdk')
    test_name = kwargs.pop('testfile')
    others = kwargs.pop('others')

    kwargs['belong_project'] = ProjectInfo.objects.get(project_name=belong_project)
    kwargs['belong_module'] = ModuleInfo.objects.get(id=belong_module)
    kwargs['sdk_name'] = sdk_name
    kwargs['test_name'] = test_name
    kwargs['others'] = others

    try:
        if SDKTestInfo.objects.filter(belong_project__project_name=belong_project, belong_module__id=belong_module, sdk_name=sdk_name, test_name=test_name).count() > 0:
            return 'SDK 测试已存在!'
        SDKTestInfo.objects.create(**kwargs)
        logging.info('SDKTest添加成功: {kwargs}'.format(kwargs=kwargs))
    except Exception:
        import traceback
        traceback.print_exc()
        return 'SDKTest添加异常，请重试'
    return 'ok'

def del_sdk_test_data(id):
    """
    根据上传的sdk_test id删除sdktest数据库中的数据
    :param id:
    :return: ok or tips
    """
    try:
        SDKTestInfo.objects.get(id=id).delete()
    except ObjectDoesNotExist:
        return '删除异常，请重试'
    return 'ok'


def del_ca_data(id):
    try:
        CaInfo.objects.get(id=id).delete()
    except:
        return '删除异常，请重试'
    return 'ok'

def add_ca_data(**kwargs):
    try:
        user_name = kwargs.get("ca_name")
        project_name = kwargs.get('project')
        ca_info = {}
        ca_info["user_name"] = user_name
        ca_info["password"] = kwargs.get("ca_password")
        ca_info['belong_project'] = ProjectInfo.objects.get(project_name=project_name)
        ca_info["author"] = kwargs.pop('author')
        ca_info["client_id"] = kwargs.get("ca_client_id")
        ca_info["redirect_url"] = kwargs.get("ca_client_url")

        if CaInfo.objects.filter(belong_project__project_name=project_name, user_name=user_name).count() > 0:
            return 'CA 信息已存在!'
        CaInfo.objects.create(**ca_info)
        return 'ok'
    except:
        import traceback
        traceback.print_exc()
        return "新增CA失败, 请重试！"

def get_ca_data(**kwargs):
    try:
        user_name = kwargs.get("ca_name")
        password = kwargs.get("ca_password")
        client_id = kwargs.get("ca_client_id")
        redirect_url = kwargs.get("ca_client_url")
        ca_type = kwargs.get("ca_type")
        ca_cfg = CaCFG.objects.get(ca_type=ca_type)
        ca_login_url = ca_cfg.ca_loginurl
        ca_url = ca_cfg.ca_url
        ca = get_ca(ca_login_url, ca_url, user_name, password, client_id, redirect_url)
        if ca:
            return "成功获取CA!"
        else:
            return "获取CA失败!"
    except:
        import traceback
        traceback.print_exc()
        return "获取CA失败, 请重试！"

def refresh_ca_data(**kwargs):
    """
    更新CA内容
    :param id:
    :return: ok or tips
    """
    try:
        user_name = kwargs.get("ca_name")
        ca_id = kwargs.get("ca_id")
        project_name = kwargs.get('project')
        #更新的时候，需要判断除了当前的一个记录外，是否还有另外一条记录
        if CaInfo.objects.filter(belong_project__project_name=project_name, user_name=user_name).count() > 1:
            return 'CA 信息已存在!'
        ca_info = {}
        ca_info["user_name"] = user_name
        ca_info["password"] = kwargs.get("ca_password")
        ca_info['belong_project'] = ProjectInfo.objects.get(project_name=kwargs.pop('project'))
        ca_info["author"] = kwargs.pop('author')
        ca_info["client_id"] = kwargs.get("ca_client_id")
        ca_info["update_time"] = datetime.datetime.now()
        ca_info["redirect_url"] = kwargs.get("ca_client_url")
        CaInfo.objects.filter(id=ca_id).update(**ca_info)
        return 'ok'
    except:
        import traceback
        traceback.print_exc()
        return "更新CA信息失败, 请重试！"

def update_ca_url_data(ca_url, ca_loginurl, ca_type):
    """
    更新CA配置
    :param ca_url: 获取令牌的地址
    :param ca_loginurl: 获取令牌的登录地址
    :return: ok or tips
    """

    try:
        if CaCFG.objects.filter(ca_type=ca_type).count() > 0:
            CaCFG.objects.filter(ca_type=ca_type).update(ca_url=ca_url, ca_loginurl=ca_loginurl)
        else:
            info = {
                'ca_url': ca_url,
                'ca_loginurl': ca_loginurl,
                'ca_type': ca_type
            }
            CaCFG.objects.create(**info)
    except:
        return "更新CA请求地址失败 ，请重试！"
    return "ok"

def get_ca(ca_loginurl, ca_url, username, password, client_id, redirect_url):
    """
    获取CA值
    :param ca_loginurl:登录地址
    :param ca_url:获取CA令牌的地址
    :param username:用户名
    :param password:密码
    :param client_id:客户端IDURL
    :param redirect_url:重定向
    :return: ca_value, expires_in
    """
    try:
        data = {
            'action' : 'login',
            'userName': username,
            'passWord': str(base64.b64encode(password.encode("utf-8")), "utf-8")
        }
        sess = requests.Session()
        resp = sess.post(ca_loginurl, data=data, allow_redirects=False, verify=False)
        print(resp.content)
        '''
        cookies = requests.utils.dict_from_cookiejar(resp.cookies)
        cookie = "; ".join([str(x) + "=" + str(y) for x, y in cookies.items()])
        headers = {
            'cookie': cookie,
        }
        '''
        #因为公用的是一个session,所以不需要手动添加cookie.
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_url,
            'response_type': 'id_token token',
            'scope': 'openid'
        }

        resp = sess.get(ca_url, params=params, verify=False)
        sess.close()
        print(resp.url)
        pa = re.compile(r"#id_token=(.*)&access_token")
        match = re.search(pa, resp.url)
        if match:
            return match.group(1)
        else:
            return ""
    except:
        return ""





