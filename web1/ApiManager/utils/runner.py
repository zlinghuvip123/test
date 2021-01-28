import os
import shutil
import logging
logger = logging.getLogger('HttpRunnerManager')

from django.core.exceptions import ObjectDoesNotExist

from ApiManager.models import TestCaseInfo, ModuleInfo, ProjectInfo, TestSuite
from ApiManager.utils.testcase import dump_yaml_file
from ApiManager.utils.common import *
import mimetypes

def run_by_single(index, base_url, path, cfg_id, ca_map={}):
    """
    加载单个case用例信息
    :param index: int or str：用例索引
    :param base_url: str：环境地址
    :return: dict
    """
    """
    httprunner已经更新到2.2.5版本，所以，在config中没有request子项，直接写base_url.
    config = {
        'config': {
            'name': '',
            'request': {
                'base_url': base_url
            }
        }
    }
    """

    config = {
        'config': {
            'name': '',
            'base_url': base_url
        }
    }
    testcase_list = []

    testcase_list.append(config)

    try:
        obj = TestCaseInfo.objects.get(id=index)
    except ObjectDoesNotExist:
        return testcase_list

    include = eval(obj.include)
    request = eval(obj.request)
    #If ca is needed
    ca_id = obj.ca.id if obj.ca else ''
    ca_value = ca_map.get(ca_id, '')
    name = obj.name
    project = obj.belong_project
    module = obj.belong_module.module_name

    config['config']['name'] = name


    testcase_dir_path = os.path.join(path, project)

    if not os.path.exists(testcase_dir_path):
        os.makedirs(testcase_dir_path)
        #update by zlinghu: 共用主目录下的debugtalk.py文件，所以直接copy过来即可
        debugtalk = os.path.join(os.getcwd(), "debugtalk.py")
        if not os.path.exists(debugtalk):
            logger.info("No debugtalk found, please check if you have provided debugtalk!")
            return
        elif not os.path.exists(os.path.join(path, 'debugtalk.py')):
            shutil.copy(debugtalk, os.path.join(path, 'debugtalk.txt'))
            os.rename(os.path.join(path, 'debugtalk.txt'), os.path.join(path, 'debugtalk.py'))
    testcase_dir_path = os.path.join(testcase_dir_path, module)

    if not os.path.exists(testcase_dir_path):
        os.mkdir(testcase_dir_path)

    has_cfg = False
    # 这里是判断它的前提条件里面是否有依赖用例或者是配置文件
    for test_info in include:
        try:
            if isinstance(test_info, dict):
                config_id = test_info.pop('config')[0]
                config_request = eval(TestCaseInfo.objects.get(id=config_id).request)
                # setdefault: 如果存在键值，则返回当前值，否则新增键值，且它的值为给定的默认值（第二个参数）。
                config_request.get('config').setdefault('base_url', base_url)
                #因为httprunner升级，config节点下没有request子节点，而是直接写base_url
                #config_request.get('config').get('request').setdefault('base_url', base_url)
                config_request['config']['name'] = name
                testcase_list[0] = config_request
                has_cfg = True
            else:
                id = test_info[0]
                # TODO：消除测试用例级别的params.... 直接移除字典中的key(params)-value不知是否可行
                pre_request = eval(TestCaseInfo.objects.get(id=id).request)
                if pre_request['test']['request']['url'] != '':
                    #if ca is needed
                    obj = TestCaseInfo.objects.get(id=id)
                    ca_id = obj.ca.id if obj.ca else ''
                    ca_value_pre = ca_map.get(ca_id, '')
                    pre_request = update_request(pre_request, ca_value_pre)
                    testcase_list.append(pre_request)

        except ObjectDoesNotExist as e:
            logger.info(e)
            return testcase_list

    # 将cfg提到suite级别后，在每个test中都手动添加suite级别添加的config文件。
    # TODO：suite级别的测试配置文件，需要更新到每一个测试用例级别吗？直接放在suite级别不可以吗？
    if not has_cfg:
        config_id = cfg_id
        config_request = eval(TestCaseInfo.objects.get(id=config_id).request)
        config_request.get('config').setdefault('base_url', base_url)
        #因为httprunner升级，config节点下没有request子节点，而是直接写base_url
        #config_request.get('config').get('request').setdefault('base_url', base_url)
        config_request['config']['name'] = name
        testcase_list[0] = config_request

    if request['test']['request']['url'] != '':
        request = update_request(request, ca_value)
        testcase_list.append(request)

    #更新每个测试用例，将配置文件中的header等信息更新到用例中去。
    update_request_ex(testcase_list, cfg_id)

    dump_yaml_file(os.path.join(testcase_dir_path, name + '.yml'), testcase_list)
    #dump_json_file(os.path.join(testcase_dir_path, name + '.json'), testcase_list)
    #TODO: 在这里修改YAML文件，针对文件参数修改YAML文件？
    #update_yaml_file(os.path.join(testcase_dir_path, name + '.yml'))

def update_request_ex(testcase_list, cfg_id):
    config_request = eval(TestCaseInfo.objects.get(id=cfg_id).request)
    for testcase in testcase_list:
        #更新非配置级别的header
        if not "config" in testcase.keys():
            headers = {}
            req_headers = testcase['test']['request'].get('headers', {})
            for k, v in config_request["config"].get("request", {}).get("headers", {}).items():
                headers[k] = v
            #已有的Header值会被配置文件中的值更新掉。
            if req_headers:
                req_headers.update(headers)
            else:
                testcase["test"].get("request", {}).setdefault("headers", headers)

def update_request(request, ca_value):
    req_data = request['test']['request'].get('data', '')
    req_vars = request['test'].get('variables', '')
    if req_data:
        vars = []
        file_name = ""
        for k, v in req_data.items():
            #如果有文件类型的，则添加内容
            if isinstance(v, list):
                #如果是文件，则将文件指定为对应的相对路径下
                #file_path = os.path.join("upload", project, module, v)
                vars.append({"filePath": v[0]})
                vars.append({"file1": "${readFileFormLocal($filePath)}"})
                file_name = os.path.basename(v[0])

        if vars:
            if req_vars:
                request['test']['variables'].extend(vars)
            else:
                request['test']['variables'] = vars

            request['test']['request'].setdefault('files', {"file": [file_name, "$file1", mimetypes.guess_type(file_name)[0]]})

    if ca_value:
        headers = {}
        req_headers = request['test']['request'].get('headers', {})
        headers["Authorization"] = "Bearer " + ca_value
        # 已有的Header值会被配置文件中的值更新掉。
        if req_headers:
            req_headers.update(headers)
        else:
            request["test"].get("request", {}).setdefault("headers", headers)

    return request

def run_by_suite(index, base_url, path, cfg_id):
    obj = TestSuite.objects.get(id=index)
    suite_name = obj.suite_name

    include = eval(obj.include)
    include = [item for item in include if item[2]=='启用中']
    # generate CA according to the cfg
    # 获取当前suite下所有的CA
    ca_map = get_ca_values_for_suite(include, cfg_id)

    # 然后获取当前所有的CA的值
    for val in include:
        run_by_single(val[0], base_url, path, cfg_id, ca_map)

    #TODO: 生成 test suite 文件
    _generate_suite_file(suite_name, include, path, cfg_id)


def _generate_suite_file(suite_name, include, path, cfg_id):
    """
    组装测试用例到Suite中
    config:
        name: test uCloud
        base_url: 10.3.14.78:8888

    testcases:
        login:
            testcase: webviewer.yaml
            variables:
                key1:value1
                key2:value2
                key3:value3
            parameters:
               user_id:[1,2,3,4,5]
            testcase: test_name.yaml
            variables:
                key1:value1
                key2:value2
                key3:value3
            parameters:
                user_name:[a,b,c,d]
    """

    test_suite = {}

    config = {}

    config_request = eval(TestCaseInfo.objects.get(id=cfg_id).request)
    if "variables" in config_request.keys():
        config.setdefault("variables", config_request.get("variables"))
    if "base_url" in config_request.keys():
        config.setdefault("base_url", config_request.get("base_url"))
    config.setdefault("name", suite_name)
    test_suite.setdefault("config", config)

    cases = {}
    for val in include:

        case_detail = {}
        case_id = val[0]
        #case_name = val[1]
        #将测试用例中的parameters中挪到这里来
        try:
            test_obj = TestCaseInfo.objects.get(id=case_id)
        except:
            continue
        case_name = test_obj.name
        project = test_obj.belong_project
        module = test_obj.belong_module.module_name
        #如果所有的文件都是被导出的json，这里就用Json，否则就是yaml文件
        case_detail.setdefault("testcase",  r"{}/{}/{}.yml".format(project, module, case_name))
        test_case_request = eval(test_obj.request)

        if "parameters" in test_case_request["test"].keys():
            params = test_case_request['test']['parameters']
            tmp = []
            for param in params:
                if not param:
                    continue
                par = {}
                for key, value in param.items():
                    if '[' in value and ']' in value:
                        par[key] = eval(value)
                    else:#file
                        file_path = get_file_path(project, module, value)
                        val = os.path.join(os.getcwd(), file_path).replace('\\', '/')
                        par[key] = '${P(' + val + ')}'
                tmp.append(par)
            if tmp:
                case_detail.setdefault("parameters", tmp)
        cases.setdefault(case_name, case_detail)

    test_suite.setdefault("testcases", cases)
    #暂时将测试用例放到主目录下吧
    testcase_dir_path = path
    #dump_json_file(os.path.join(testcase_dir_path, suite_name + '.yaml'), test_case_list)
    dump_yaml_file(os.path.join(testcase_dir_path, suite_name + '.yml'), test_suite)


def run_by_batch(test_list, base_url, path, cfg_id, type=None, mode=False):
    """
    批量组装用例数据
    :param test_list:
    :param base_url: str: 环境地址
    :param type: str：用例级别
    :param mode: boolean：True 同步 False: 异步
    :return: list
    """

    if mode:
        #因为添加了cfg_id这个参数，所以参数的数目=project数目+3. 所以这里遍历总数目-3即可。
        for index in range(len(test_list) - 3):
            form_test = test_list[index].split('=')
            value = form_test[1]
            if type == 'project':
                run_by_project(value, base_url, path, cfg_id)
            elif type == 'module':
                run_by_module(value, base_url, path, cfg_id)
            elif type == 'suite':
                run_by_suite(value, base_url, path, cfg_id)
            else:
                run_by_single(value, base_url, path, cfg_id)

    else:
        if type == 'project':
            for value in test_list.values():
                run_by_project(value, base_url, path, cfg_id)

        elif type == 'module':
            for value in test_list.values():
                run_by_module(value, base_url, path, cfg_id)
        elif type == 'suite':
            for value in test_list.values():
                run_by_suite(value, base_url, path, cfg_id)

        else:
            for index in range(len(test_list) - 1):
                form_test = test_list[index].split('=')
                index = form_test[1]
                run_by_single(index, base_url, path, cfg_id)


def run_by_module(id, base_url, path, cfg_id):
    """
    组装模块用例
    :param id: int or str：模块索引
    :param base_url: str：环境地址
    :return: list
    """
    obj = ModuleInfo.objects.get(id=id)
    test_index_list = TestCaseInfo.objects.filter(belong_module=obj, type=1).values_list('id')
    for index in test_index_list:
        run_by_single(index[0], base_url, path, cfg_id)


def run_by_project(id, base_url, path, cfg_id):
    """
    组装项目用例
    :param id: int or str：项目索引
    :param base_url: 环境地址
    :return: list
    """
    obj = ProjectInfo.objects.get(id=id)
    module_index_list = ModuleInfo.objects.filter(belong_project=obj).values_list('id')
    for index in module_index_list:
        module_id = index[0]
        run_by_module(module_id, base_url, path, cfg_id)


def run_test_by_type(id, base_url, path, type, cfg_id):

    if type == 'project':
        run_by_project(id, base_url, path, cfg_id)
    elif type == 'module':
        run_by_module(id, base_url, path, cfg_id)
    elif type == 'suite':
        run_by_suite(id, base_url, path, cfg_id)
    else:
        ca_map = get_ca_values_for_case(id, cfg_id)
        run_by_single(id, base_url, path, cfg_id, ca_map)


def run_sdk_test(test_file_path, test_name, sdk_list):
    #TODO： 针对不同的测试文件类型，使用不同的命令行运行测试，至少支持py,jar,dll三种测试文件的测试
    test_type = os.path.splitext(test_name)[1]
    import subprocess
    import time
    if test_type == '.py':
        subprocess.call("nosetests -s -w %s --with-html-output" %(os.path.join(test_file_path, test_name)))
        return os.path.join(test_file_path, "nosetests.html")
    elif test_type == '.jar':
        cur_path = os.getcwd()
        os.chdir(os.path.abspath(test_file_path))
        try:
            #替换jar包
            if os.path.exists("lib"):
                delete_folder_recursively("lib")
            os.mkdir("lib")
            #sdk有多个（依赖其它sdk吧）
            for sdk_name in sdk_list.split(','):
                print(sdk_name)
                shutil.copy(sdk_name, "lib")
                #time.sleep(60)
                subprocess.call(["jar", "-uvf", test_name, os.path.join("lib", sdk_name)])
            # jar包测试用例运行后的测试报告的为运行环境目录下的test-out目录，
            # 当前的目录为项目的主目录，os.getcwd()
            # 为了避免各个测试用例中的相互干扰，保证各个测试用例的报告输出到对应
            # 的文件夹下面，所以先切换目录到tmp下的私有目录。运行完后再切换回去。
            subprocess.call(["java", "-jar", test_name])
        except:
            traceback.print_exc()
            return ""
        finally:
            os.chdir(cur_path)
        return os.path.join(test_file_path, "test-output", "emailable-report.html")
    elif test_type == ".dll":
        #TODO: 针对dll类型的测试用例，如何运行并返回适当的测试报告。
        return "..."
