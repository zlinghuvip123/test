import shutil
import traceback
from django.conf import settings


from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, StreamingHttpResponse
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe
from dwebsocket import accept_websocket
from django.http import FileResponse
from django.utils.http import urlquote

from ApiManager.utils.auth import auth_user
from ApiManager.tasks import main_hrun
from ApiManager.utils.common import *
from ApiManager.utils.operation import *
from ApiManager.utils.pagination import get_pager_info
from ApiManager.utils.runner import run_by_batch, run_test_by_type, run_sdk_test
from ApiManager.utils.task_opt import delete_task, change_task_status
from ApiManager.utils.testcase import get_time_stamp

from httprunner.api import HttpRunner


logger = logging.getLogger('HttpRunnerManager')

# Create your views here.


def login_check(func):
    def wrapper(request, *args, **kwargs):
        # If the url is begin with debug, ignore login_check.
        if request.path.strip('/').startswith("debug"):
            request.session["now_account"] = request.POST.get('account', "Jenkins")
            print(request.session["now_account"] )
            request.session["login_status"] = True
            return func(request, *args, **kwargs)
        if not request.session.get('login_status'):
            return HttpResponseRedirect('/api/login/')
        return func(request, *args, **kwargs)

    return wrapper

#在进入查询是，会先在session中保存当前页面的url, 当前页面时，如果url还是一致的，则不clear session
#否则清除session(保存的页面中查询时的条件，不要带到下个页面中去)
def set_session(func):
    def wrapper(request, *args, **kwargs):
        last_url = request.session.get("url", "")
        cur_url = request.path
        if last_url:
            if last_url.split('/')[:-2] != cur_url.split('/')[:-2]:
                init_filter_session(request)
        else:
            init_filter_session(request)
        return func(request, *args, **kwargs)

    return wrapper


def login(request):
    """
    登录
    :param request:
    :return:
    """
    if request.method == 'POST':
        username = request.POST.get('account')
        password = request.POST.get('password')
        # Login with ldap
        user = username + "@united-imaging.com"

        if username and password and (auth_user(user, password) or UserInfo.objects.filter(username__exact=username).filter(password__exact=password).count() == 1):
            logger.info('{username} 登录成功'.format(username=username))
            request.session["login_status"] = True
            request.session["now_account"] = username
            return HttpResponseRedirect('/api/index/')
        else:
            logger.info('{username} 登录失败, 请检查用户名或者密码'.format(username=username))
            request.session["login_status"] = False
            ret = {}
            ret["userName"] = username
            ret["passWord"] = password
            ret["message"] = '{username} 登录失败, 请检查用户名或者密码'.format(username=username)
            return render_to_response("login.html", ret)

    elif request.method == 'GET':
        return render_to_response("login.html")


def register(request):
    """
    注册
    :param request:
    :return:
    """
    if request.is_ajax():
        user_info = json.loads(request.body.decode('utf-8'))
        msg = register_info_logic(**user_info)
        return HttpResponse(get_ajax_msg(msg, '恭喜您，账号已成功注册'))
    elif request.method == 'GET':
        return render_to_response("register.html")


@login_check
def log_out(request):
    """
    注销登录
    :param request:
    :return:
    """
    if request.method == 'GET':
        logger.info('{username}退出'.format(username=request.session['now_account']))
        try:
            del request.session['now_account']
            del request.session['login_status']
            init_filter_session(request, type=False)
        except KeyError:
            logging.error('session invalid')
        return HttpResponseRedirect("/api/login/")


@login_check
def index(request):
    """
    首页
    :param request:
    :return:
    """
    project_length = ProjectInfo.objects.count()
    module_length = ModuleInfo.objects.count()
    test_length = TestCaseInfo.objects.filter(type__exact=1).count()
    suite_length = TestSuite.objects.count()

    total = get_total_values()
    manage_info = {
        'project_length': project_length,
        'module_length': module_length,
        'test_length': test_length,
        'suite_length': suite_length,
        'account': request.session["now_account"],
        'total': total
    }

    init_filter_session(request)
    return render_to_response('index.html', manage_info)


@login_check
def add_project(request):
    """
    新增项目
    :param request:
    :return:
    """
    account = request.session["now_account"]
    if request.is_ajax():
        project_info = json.loads(request.body.decode('utf-8'))
        msg = project_info_logic(**project_info)
        return HttpResponse(get_ajax_msg(msg, '/api/project_list/1/'))

    elif request.method == 'GET':
        manage_info = {
            'account': account
        }
        return render_to_response('add_project.html', manage_info)


@login_check
def add_module(request):
    """
    新增模块
    :param request:
    :return:
    """
    account = request.session["now_account"]
    if request.is_ajax():
        module_info = json.loads(request.body.decode('utf-8'))
        msg = module_info_logic(**module_info)
        return HttpResponse(get_ajax_msg(msg, '/api/module_list/1/'))
    elif request.method == 'GET':
        manage_info = {
            'account': account,
            'data': ProjectInfo.objects.all().values('project_name')
        }
        return render_to_response('add_module.html', manage_info)


@login_check
def add_case(request):
    """
    新增用例
    :param request:
    :return:
    """
    account = request.session["now_account"]
    if request.is_ajax():
        testcase_info = json.loads(request.body.decode('utf-8'))
        msg = case_info_logic(**testcase_info)
        return HttpResponse(get_ajax_msg(msg, '/api/test_list/1/'))
    elif request.method == 'GET':
        manage_info = {
            'account': account,
            'project': ProjectInfo.objects.all().values('project_name').order_by('-create_time'),
            'ca_list': CaInfo.objects.all().order_by("user_name")
        }
        return render_to_response('add_case.html', manage_info)


@login_check
def add_config(request):
    """
    新增配置
    :param request:
    :return:
    """
    account = request.session["now_account"]
    if request.is_ajax():
        testconfig_info = json.loads(request.body.decode('utf-8'))
        msg = config_info_logic(**testconfig_info)
        return HttpResponse(get_ajax_msg(msg, '/api/config_list/1/'))
    elif request.method == 'GET':
        manage_info = {
            'account': account,
            'project': ProjectInfo.objects.all().values('project_name').order_by('-create_time')
        }
        return render_to_response('add_config.html', manage_info)


@login_check
def run_test(request):
    """
    运行用例
    :param request:
    :return:
    """

    kwargs = {
        "failfast": False,
    }
    runner = HttpRunner(**kwargs)

    testcase_dir_path = os.path.join(settings.BASE_DIR, "suite")
    testcase_dir_path = os.path.join(testcase_dir_path, get_time_stamp())

    account = request.session["now_account"]
    if request.is_ajax():
        kwargs = json.loads(request.body.decode('utf-8'))
        id = kwargs.pop('id')
        suite_name = TestSuite.objects.get(id=id).suite_name
        cfg_id = kwargs.pop('cfg_id')
        base_url = kwargs.pop('env_name')
        type = kwargs.pop('type')
        run_test_by_type(id, base_url, testcase_dir_path, type, cfg_id)
        report_name = kwargs.get('report_name', None)
        request.session["base_url"] = base_url
        request.session["cfg_id"] = cfg_id
        main_hrun.delay(testcase_dir_path, report_name)
        return HttpResponse('用例执行中，请稍后查看报告即可,默认时间戳命名报告')
    else:
        id = request.POST.get('id')
        base_url = request.POST.get('env_name')
        type = request.POST.get('type', 'test')
        cfg_id = request.POST.get('cfg_id')
        request.session["base_url"] = base_url
        request.session["cfg_id"] = cfg_id
        run_test_by_type(id, base_url, testcase_dir_path, type, cfg_id)
        if type == "suite":
            suite_name = TestSuite.objects.get(id=id).suite_name
            runner.run(os.path.join(testcase_dir_path, "{}.yml".format(suite_name)))
        else:
            runner.run(testcase_dir_path)
        #删除yml文件,异常的时候不删除，可以用来debug
        shutil.rmtree(testcase_dir_path)
        runner._summary = timestamp_to_datetime(runner.summary, type=False)
        #data = request.body.decode('utf-8')
        # kwargs = json.loads(request.body.decode('utf-8'))
        #report_name = kwargs.get('report_name', None)
        report_name = get_test_name(id, type)
        report_id = add_test_reports(runner, account, report_name)
        if request.POST.get('account') == "Jenkins":
            result = download_report(request, report_id)
            return result
        else:
            runner.summary.setdefault("report_id", report_id)
            return render_to_response('report_template.html', runner.summary)


@login_check
def run_batch_test(request):
    """
    批量运行用例
    :param request:
    :return:
    """

    kwargs = {
        "failfast": False,
    }
    runner = HttpRunner(**kwargs)

    testcase_dir_path = os.path.join(settings.BASE_DIR, "suite")
    testcase_dir_path = os.path.join(testcase_dir_path, get_time_stamp())

    if request.is_ajax():
        kwargs = json.loads(request.body.decode('utf-8'))
        test_list = kwargs.pop('id')
        base_url = kwargs.pop('env_name')
        cfg_id = kwargs.pop('cfg_id')
        type = kwargs.pop('type')
        report_name = kwargs.get('report_name', None)
        run_by_batch(test_list, base_url, testcase_dir_path, cfg_id, type=type)
        main_hrun.delay(testcase_dir_path, report_name)
        return HttpResponse('用例执行中，请稍后查看报告即可,默认时间戳命名报告')
    else:
        type = request.POST.get('type', None)
        base_url = request.POST.get('env_name')
        test_list = request.body.decode('utf-8').split('&')
        cfg_id = request.POST.get('cfg_id')
        if type:
            run_by_batch(test_list, base_url, testcase_dir_path, cfg_id, type=type, mode=True)
        else:
            run_by_batch(test_list, base_url, testcase_dir_path, cfg_id)

        runner.run(testcase_dir_path)

        shutil.rmtree(testcase_dir_path)
        runner.summary = timestamp_to_datetime(runner.summary, type=False)

        return render_to_response('report_template.html', runner.summary)


@login_check
@set_session
def project_list(request, id):
    """
    项目列表
    :param request:
    :param id: str or int：当前页
    :return:
    """

    account = request.session["now_account"]
    if request.is_ajax():
        project_info = json.loads(request.body.decode('utf-8'))
        if 'mode' in project_info.keys():
            msg = del_project_data(project_info.pop('id'))
        else:
            msg = project_info_logic(type=False, **project_info)
        return HttpResponse(get_ajax_msg(msg, 'ok'))
    else:
        filter_query = set_filter_session(request)
        pro_list = get_pager_info(
            ProjectInfo, filter_query, '/api/project_list/', id)
        manage_info = {
            'account': account,
            'project': pro_list[1],
            'page_list': pro_list[0],
            'info': filter_query,
            'sum': pro_list[2],
            'env': EnvInfo.objects.all().order_by('-create_time'),
            'cfg': TestCaseInfo.objects.filter(type=2),
            'project_all': ProjectInfo.objects.all().order_by('-update_time')
        }
        return render_to_response('project_list.html', manage_info)


@login_check
@set_session
def module_list(request, id):
    """
    模块列表
    :param request:
    :param id: str or int：当前页
    :return:
    """
    account = request.session["now_account"]
    if request.is_ajax():
        module_info = json.loads(request.body.decode('utf-8'))
        if 'mode' in module_info.keys():  # del module
            msg = del_module_data(module_info.pop('id'))
        else:
            msg = module_info_logic(type=False, **module_info)
        return HttpResponse(get_ajax_msg(msg, 'ok'))
    else:
        filter_query = set_filter_session(request)
        module_list = get_pager_info(
            ModuleInfo, filter_query, '/api/module_list/', id)
        manage_info = {
            'account': account,
            'module': module_list[1],
            'page_list': module_list[0],
            'info': filter_query,
            'sum': module_list[2],
            'env': EnvInfo.objects.all().order_by('-create_time'),
            'cfg': TestCaseInfo.objects.filter(type=2),
            'project': ProjectInfo.objects.all().order_by('-update_time')
        }
        return render_to_response('module_list.html', manage_info)

@login_check
@set_session
def test_list(request, id):
    """
    用例列表
    :param request:
    :param id: str or int：当前页
    :return:
    """

    account = request.session["now_account"]
    if request.is_ajax():
        test_info = json.loads(request.body.decode('utf-8'))

        if test_info.get('mode') == 'del':
            msg = del_test_data(test_info.pop('id'))
        elif test_info.get('mode') == 'copy':
            index = test_info.get('data').pop('index')
            name = test_info.get('data').pop('name')
            project = test_info.get('data').pop('project')
            module = test_info.get('data').pop('belong_module')
            author = account
            msg = copy_test_data(index, name, project, module, author)
        return HttpResponse(get_ajax_msg(msg, 'ok'))

    else:
        filter_query = set_filter_session(request)
        test_list = get_pager_info(
            TestCaseInfo, filter_query, '/api/test_list/', id)
        manage_info = {
            'account': account,
            'test': test_list[1],
            'page_list': test_list[0],
            'info': filter_query,
            'env': EnvInfo.objects.all().order_by('env_name'),
            'env_session': request.session.get('base_url', ''),
            'cfg': TestCaseInfo.objects.filter(type=2).order_by('name'),
            'cfg_session': int(request.session.get('cfg_id', -1)),
            'project': ProjectInfo.objects.all().order_by('-update_time'),
            'ca_list': CaInfo.objects.all().order_by('user_name')
        }
        return render_to_response('test_list.html', manage_info)


@login_check
@set_session
def config_list(request, id):
    """
    配置列表
    :param request:
    :param id: str or int：当前页
    :return:
    """
    account = request.session["now_account"]
    if request.is_ajax():
        test_info = json.loads(request.body.decode('utf-8'))

        if test_info.get('mode') == 'del':
            msg = del_test_data(test_info.pop('id'))
        elif test_info.get('mode') == 'copy':
            index = test_info.get('data').pop('index')
            name = test_info.get('data').pop('config')
            project = test_info.get('data').pop('project')
            module = test_info.get('data').pop('belong_module')
            author = account
            msg = copy_test_data(index, name, project, module, author)
        return HttpResponse(get_ajax_msg(msg, 'ok'))
    else:
        filter_query = set_filter_session(request)
        test_list = get_pager_info(
            TestCaseInfo, filter_query, '/api/config_list/', id)
        manage_info = {
            'account': account,
            'test': test_list[1],
            'page_list': test_list[0],
            'info': filter_query,
            'project': ProjectInfo.objects.all().order_by('-update_time')
        }
        return render_to_response('config_list.html', manage_info)


@login_check
def edit_case(request, id=None):
    """
    编辑用例
    :param request:
    :param id:
    :return:
    """

    account = request.session["now_account"]
    if request.is_ajax():
        testcase_lists = json.loads(request.body.decode('utf-8'))
        msg = case_info_logic(type=False, **testcase_lists)
        return HttpResponse(get_ajax_msg(msg, '/api/test_list/1/'))

    test_info = TestCaseInfo.objects.get_case_by_id(id)
    req = eval(test_info[0].request)
    include = eval(test_info[0].include)
    case_name = test_info[0].name
    setup_hooks = convert_hooks(req['test'].get('setup_hooks', ""))
    teardown_hooks = convert_hooks(req['test'].get('teardown_hooks', ""))
    manage_info = {
        'testcase_name': case_name,
        'account': account,
        'info': test_info[0],
        'request': req['test'],
        'include': include,
        'project': ProjectInfo.objects.all().values('project_name').order_by('-create_time'),
        "setup_hooks": setup_hooks,
        "teardown_hooks": teardown_hooks,
        "hook_options": get_hook_options(),
        'ca_list': CaInfo.objects.all(),
        'env': EnvInfo.objects.all().order_by('env_name'),
        'env_session': request.session.get('base_url', ''),
        'cfg': TestCaseInfo.objects.filter(type=2).order_by('name'),
        'cfg_session': int(request.session.get('cfg_id', -1))
    }
    return render_to_response('edit_case.html', manage_info)


@login_check
def edit_config(request, id=None):
    """
    编辑配置
    :param request:
    :param id:
    :return:
    """

    account = request.session["now_account"]
    if request.is_ajax():
        testconfig_lists = json.loads(request.body.decode('utf-8'))
        msg = config_info_logic(type=False, **testconfig_lists)
        return HttpResponse(get_ajax_msg(msg, '/api/config_list/1/'))

    config_info = TestCaseInfo.objects.get_case_by_id(id)
    request = eval(config_info[0].request)
    manage_info = {
        'account': account,
        'info': config_info[0],
        'request': request['config'],
        'project': ProjectInfo.objects.all().values(
            'project_name').order_by('-create_time')
    }
    return render_to_response('edit_config.html', manage_info)


@login_check
def env_set(request):
    """
    环境设置
    :param request:
    :return:
    """

    account = request.session["now_account"]
    if request.is_ajax():
        env_lists = json.loads(request.body.decode('utf-8'))
        msg = env_data_logic(**env_lists)
        return HttpResponse(get_ajax_msg(msg, 'ok'))

    elif request.method == 'GET':
        return render_to_response('env_list.html', {'account': account})


@login_check
@set_session
def env_list(request, id):
    """
    环境列表
    :param request:
    :param id: str or int：当前页
    :return:
    """

    account = request.session["now_account"]
    if request.method == 'GET':
        env_lists = get_pager_info(
            EnvInfo, None, '/api/env_list/', id)
        manage_info = {
            'account': account,
            'env': env_lists[1],
            'page_list': env_lists[0],
        }
        return render_to_response('env_list.html', manage_info)


@login_check
@set_session
def report_list(request, id):
    """
    报告列表
    :param request:
    :param id: str or int：当前页
    :return:
    """

    if request.is_ajax():
        report_info = json.loads(request.body.decode('utf-8'))

        if report_info.get('mode') == 'del':
            msg = del_report_data(report_info.pop('id'))
        return HttpResponse(get_ajax_msg(msg, 'ok'))
    else:
        filter_query = set_filter_session(request)
        report_list = get_pager_info(
            TestReports, filter_query, '/api/report_list/', id)
        manage_info = {
            'account': request.session["now_account"],
            'report': report_list[1],
            'page_list': report_list[0],
            'info': filter_query
        }
        return render_to_response('report_list.html', manage_info)


@login_check
def view_report(request, id):
    """
    查看报告
    :param request:
    :param id: str or int：报告名称索引
    :return:
    """
    #之前保存的是報告的內容，如果報告過大，會導致數據庫報錯，現改成保存路径，再次需要的时候重新读取即可
    report_name = TestReports.objects.get(id=id).reports
    report_path = os.path.join(settings.BASE_DIR, "reports", report_name)
    with io.open(report_path, 'r', encoding='utf-8') as stream:
        reports = stream.read()

    return render_to_response('view_report.html', {"reports": mark_safe(reports)})


@login_check
def periodictask(request, id):
    """
    定时任务列表
    :param request:
    :param id: str or int：当前页
    :return:
    """

    account = request.session["now_account"]
    if request.is_ajax():
        kwargs = json.loads(request.body.decode('utf-8'))
        mode = kwargs.pop('mode')
        id = kwargs.pop('id')
        msg = delete_task(id) if mode == 'del' else change_task_status(id, mode)
        return HttpResponse(get_ajax_msg(msg, 'ok'))
    else:
        filter_query = set_filter_session(request)
        task_list = get_pager_info(
            PeriodicTask, filter_query, '/api/periodictask/', id)
        manage_info = {
            'account': account,
            'task': task_list[1],
            'page_list': task_list[0],
            'info': filter_query
        }
    return render_to_response('periodictask_list.html', manage_info)


@login_check
def add_task(request):
    """
    添加任务
    :param request:
    :return:
    """

    account = request.session["now_account"]
    if request.is_ajax():
        kwargs = json.loads(request.body.decode('utf-8'))
        msg = task_logic(**kwargs)
        return HttpResponse(get_ajax_msg(msg, '/api/periodictask/1/'))
    elif request.method == 'GET':
        info = {
            'account': account,
            'env': EnvInfo.objects.all().order_by('-create_time'),
            'project': ProjectInfo.objects.all().order_by('-create_time')
        }
        return render_to_response('add_task.html', info)


@login_check
def upload_file(request):
    ret = {
        "status": "Success",
        "message": ""
    }

    if request.method == 'POST':
        try:
            project_name = request.POST.get('project')
            module_id = request.POST.get('module')
        except KeyError as e:
            ret["status"] = "Fail"
            ret["message"] = str(e)
            return JsonResponse(ret)

        if project_name == '请选择' or module_id == '请选择':
            ret["status"] = "Fail"
            ret["message"] = "项目或模块不能为空"
            return JsonResponse(ret)
        #project_name = ProjectInfo.objects.get(id=project_id).project_name
        module_name = ModuleInfo.objects.get(id=module_id).module_name
        # TODO:将文件保存和数据库存储放在同一事务中，保持同步，存在文件保存了，但是数据库未操作成功
        upload_path = os.path.join(settings.BASE_DIR, "upload", project_name, module_name)
        # upload_path = sys.path[0] + separator + 'upload' + separator

        if not os.path.exists(upload_path):
            os.makedirs(upload_path)

        upload_obj = request.FILES.getlist('upload')
        failed_list = []
        for f in upload_obj:
            temp_path = os.path.join(upload_path, f.name)
            try:
                with open(temp_path, 'wb') as data:
                    for line in f.chunks():
                        data.write(line)
            except IOError as e:
                failed_list.append(f.name)
                continue
            #转换文件格式
            try:
                change_file_encoding(temp_path)
            except:
                pass

                #ret["status"] = "Fail"
                #ret["message"] = str(e)
                #return JsonResponse(ret)
            #暂时只保存文件，不将他们转化为测试用例
            #upload_file_logic(file_list, project_name, module_name, account)
            file_info = {
                "belong_project": project_name,
                "belong_module": module_name,
                "project" : ProjectInfo.objects.get_pro_name(project_name, False),
                "module" : ModuleInfo.objects.get(id=module_id),
                "name": f.name,
                "author": request.session["now_account"],
                "file_size": len(f),
                "file_path": os.path.join("upload", project_name, module_name, f.name)
            }
            msg = add_file_data(**file_info)
            if msg != "ok":
                failed_list.append(f.name)
                continue
                #ret["status"] = "Fail"
                #ret["message"] = msg
                #return JsonResponse(ret)
        if failed_list:
            ret["status"] = "Fail"
            ret["message"] = failed_list
        else:
            ret["message"] = "/api/file_upload/1/"
        return JsonResponse(ret)


@login_check
def get_project_info(request):
    """
     获取项目相关信息
     :param request:
     :return:
     """

    if request.is_ajax():
        project_info = json.loads(request.body.decode('utf-8'))

        msg = load_modules(**project_info.pop('task'))
        return HttpResponse(msg)


@login_check
def download_file(request, id):
    #if request.method == 'GET':

        #不必要刪除報告目錄吧。
        #if os.path.exists(os.path.join(os.getcwd(), "reports")):
        #    shutil.rmtree(os.path.join(os.getcwd(), "reports"))
        #os.makedirs(os.path.join(os.getcwd(), "reports"))
        upload_file = FileInfo.objects.get(id=id)
        file_path = upload_file.file_path
        file_name = upload_file.name
        #belong_project = upload_file.belong_project
        #belong_module = upload_file.belong_module
        file_path = os.path.join(settings.BASE_DIR, file_path)

        if not os.path.exists(file_path):
            return HttpResponse(u'请求的文件不存在，请确认后再操作！')

        response = FileResponse(open(file_path, 'rb'))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="{0}"'.format(urlquote(file_name))
        return response


@login_check
def download_report(request, id):
    #if request.method == 'GET':

        #不必要刪除報告目錄吧。
        #if os.path.exists(os.path.join(os.getcwd(), "reports")):
        #    shutil.rmtree(os.path.join(os.getcwd(), "reports"))
        #os.makedirs(os.path.join(os.getcwd(), "reports"))
        report = TestReports.objects.get(id=id)
        report_name = report.reports
        report_path = os.path.join(settings.BASE_DIR, "reports", report_name)
        #update: 在测试报告的HTML中加入tag用来添加报告的URL，当Jenkin脚本解析报告的时候，可以将这个url作为链接放到报告中。
        ip, port = get_host_ip_port()
        report_url = r"http://{}:{}/debug/view_report/{}/".format(ip, port, id)
        add_report_link(report_path, report_url)
        def file_iterator(file_name, chunk_size=512):
            with open(file_name, encoding='utf-8') as f:
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break

        response = StreamingHttpResponse(file_iterator(report_path))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="%s"' %(os.path.basename(report_path))
        return response

@login_check
def download_report_ex(request, report_path):
    def file_iterator(file_name, chunk_size=512):
        with open(file_name, encoding='utf-8') as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    response = StreamingHttpResponse(file_iterator(report_path))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="%s"' %(os.path.basename(report_path))
    return response


@login_check
def debugtalk(request, id=None):
    if request.method == 'GET':
        dt = {}
        #debugtalk从文件中读取
        with open(os.path.join(settings.BASE_DIR, "debugtalk.py"), 'r', encoding='utf8') as pf:
            debugtalk = pf.read()
        print(debugtalk)
        dt['debugtalk'] = debugtalk
        return render_to_response('debugtalk.html', dt)
    else:
        #编辑完debugtalk后直接保存到文件，而不保存到数据库。
        debugtalk = request.POST.get('debugtalk')
        print(debugtalk)
        code = debugtalk.replace('new_line', '\n')
        with open(os.path.join(settings.BASE_DIR, "debugtalk.txt"), 'w') as pf:
            pf.write(code)
        dst_path = os.path.join(settings.BASE_DIR, "debugtalk.py")
        if os.path.exists(dst_path):
            os.remove(dst_path)
        os.rename(os.path.join(settings.BASE_DIR, "debugtalk.txt"), os.path.join(settings.BASE_DIR, "debugtalk.py"))
        return HttpResponseRedirect('/api/index')

@login_check
def show_logs(request, type):
    ret = {}
    account = request.session["now_account"]
    ret["account"] = account
    if request.method == 'GET':
        if type == "system":
            log_file = os.path.join(settings.BASE_DIR, "logs", "all.log")
            ret["type"] = u"系统日志"
        else:
            log_file = os.path.join(settings.BASE_DIR, "logs", "debugtalk.log")
            ret["type"] = u"debugtalk日志"
        log = []
        with open(log_file, 'r', encoding='utf-8') as pf:
            type = 'error'
            for line in pf.readlines():
                if line != '\n':
                    obj = {}
                    if '[ERROR]' in line:
                        type = 'error'
                    elif '[INFO]' in line:
                        type = 'info'
                    obj["type"] = type
                    obj["content"] = line.strip('\n')
                    log.append(obj)
        ret['logs'] = log
        return render_to_response('logs.html', ret)


@login_check
@set_session
def suite_list(request, id):
    account = request.session["now_account"]
    if request.is_ajax():
        suite_info = json.loads(request.body.decode('utf-8'))

        if suite_info.get('mode') == 'del':
            msg = del_suite_data(suite_info.pop('id'))
        elif suite_info.get('mode') == 'copy':
            msg = copy_suite_data(suite_info.get('data').pop('index'), suite_info.get('data').pop('name'))
        return HttpResponse(get_ajax_msg(msg, 'ok'))
    else:
        filter_query = set_filter_session(request)
        pro_list = get_pager_info(
            TestSuite, filter_query, '/api/suite_list/', id)
        manage_info = {
            'account': account,
            'suite': pro_list[1],
            'page_list': pro_list[0],
            'info': filter_query,
            'sum': pro_list[2],
            'env_session': request.session.get('base_url', ''),
            'cfg_session': int(request.session.get('cfg_id', -1)),
            'env': EnvInfo.objects.all().order_by('env_name'),
            'cfg': TestCaseInfo.objects.filter(type=2).order_by('name'),
            'project': ProjectInfo.objects.all().order_by('-update_time')
        }
        return render_to_response('suite_list.html', manage_info)


@login_check
def add_suite(request):
    account = request.session["now_account"]
    if request.is_ajax():
        kwargs = json.loads(request.body.decode('utf-8'))
        msg = add_suite_data(**kwargs)
        return HttpResponse(get_ajax_msg(msg, '/api/suite_list/1/'))

    elif request.method == 'GET':
        manage_info = {
            'account': account,
            'project': ProjectInfo.objects.all().values('project_name').order_by('-create_time')
        }
        return render_to_response('add_suite.html', manage_info)


@login_check
def edit_suite(request, id=None):
    account = request.session["now_account"]
    if request.is_ajax():
        kwargs = json.loads(request.body.decode('utf-8'))
        msg = edit_suite_data(**kwargs)
        return HttpResponse(get_ajax_msg(msg, '/api/suite_list/1/'))

    suite_info = TestSuite.objects.get(id=id)
    belong_project = suite_info.belong_project.project_name
    module_info = ModuleInfo.objects.filter(belong_project__project_name=belong_project) \
        .values_list('id', 'module_name').order_by('-create_time')
    manage_info = {
        'account': account,
        'info': suite_info,
        'moduleList': module_info,
        'project': ProjectInfo.objects.all().values(
            'project_name').order_by('-create_time')
    }
    return render_to_response('edit_suite.html', manage_info)

@login_check
@accept_websocket
def echo2(request):
    if not request.is_websocket():
        return render_to_response('echo.html')
    else:
        message = request.websocket.wait()
        print(message.decode('utf-8'))
        request.websocket.send('sdsd'.encode('utf-8'))

'''
@login_check
def echo(request):
    if not request.is_websocket():
        return render_to_response('echo.html')
    else:
        servers = []
        for message in request.websocket:
            try:
                servers.append(message.decode('utf-8'))
            except AttributeError:
                pass
            if len(servers) == 4:
                break
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(servers[0], 22, username=servers[1], password=servers[2], timeout=10)
        while True:
            cmd = servers[3]
            stdin, stdout, stderr = client.exec_command(cmd)
            for i, line in enumerate(stdout):
                request.websocket.send(bytes(line, encoding='utf8'))
            client.close()
'''

@login_check
@set_session
def file_upload(request, id):
    ret = {}
    info = {}
    account = request.session["now_account"]
    if request.is_ajax():
        info = json.loads(request.body.decode('utf-8'))
        if info.get('mode') == 'del':
            msg = del_file_data(info.pop('id'))
        return HttpResponse(get_ajax_msg(msg, 'ok'))
    else:
        filter_query = set_filter_session(request)
        pro_list = get_pager_info(
            FileInfo, filter_query, '/api/file_upload/', id)
        manage_info = {
            'account': account,
            'file_list': pro_list[1],
            'page_list': pro_list[0],
            'info': filter_query,
            'project': ProjectInfo.objects.all().order_by('-update_time')
        }
    return render_to_response('uploadedfile_list.html', manage_info)

@login_check
@set_session
def sdk_test_list(request, id):
    account = request.session["now_account"]
    if request.is_ajax():
        kwargs = json.loads(request.body.decode('utf-8'))
        kwargs["author"] = account
        if kwargs.get('mode') == 'del':
            msg = del_sdk_test_data(kwargs.pop('id'))
        else:
            msg = add_sdk_test_data(**kwargs)
        return HttpResponse(get_ajax_msg(msg, 'ok'))

    elif request.method == 'GET':
        filter_query = set_filter_session(request)
        pro_list = get_pager_info(
            SDKTestInfo, filter_query, '/api/sdk_test/', id)
        if "msg" in request.session.keys():
            msg = request.session.pop("msg")
        else:
            msg = ""
        manage_info = {
            'account': account,
            'sdk_test_list': pro_list[1],
            'page_list': pro_list[0],
            'info': filter_query,
            'projects': ProjectInfo.objects.all().order_by('-update_time'),
            'msg': msg
        }
        return render_to_response('sdk_test_list.html', manage_info)

@login_check
def sdk_run(request):
    import time
    account = request.session["now_account"]
    id = request.POST.get('id')
    sdk_test = SDKTestInfo.objects.get(id=id)
    tmp_path = ""
    try:
        #可能存在多个sdk
        sdk_list = sdk_test.sdk_name.split(',')
        for sdk_name in sdk_list:
            sdk_path = os.path.join("sdk", sdk_name)
            if not os.path.exists(os.path.join(settings.BASE_DIR, sdk_path)):
                msg = u"SDK文件%s不存在" %(sdk_test.sdk_name)
                request.session["msg"] = msg
                logger.info(msg)
                return HttpResponseRedirect('/api/sdk_test_list/1/')
        test_file_name = sdk_test.test_name
        test_file_path = FileInfo.objects.get(name=test_file_name).file_path

        #建立临时目录，存储SDK和测试文件，然后只在当前目录下运行
        tmp_path = os.path.join("tmp", str(int(time.time())))

        #针对云存储需要拷贝专用文件
        if test_file_name == 'test_CloudStorageSDK.jar':
            dir_to_copy = os.path.join('files', 'cloudstorage')
            shutil.copytree(dir_to_copy, tmp_path)

        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)
        #拷贝其它文件
        for f in sdk_test.others.split(','):
            f_path = FileInfo.objects.get(name=f).file_path
            shutil.copy(f_path, tmp_path)
        for sdk_name in sdk_list:
            sdk_path = os.path.join("sdk", sdk_name)
            shutil.copy(sdk_path, tmp_path)
        shutil.copy(test_file_path, tmp_path)
        #TODO: py文件应该按照什么样的格式去编写？ py文件中自动去搜索当前目录下的jar文件，加载jar文件即可。
        test_file_path_tmp = os.path.join(tmp_path, test_file_name)
        report_path = run_sdk_test(tmp_path, test_file_name, sdk_test.sdk_name)
        if not os.path.exists(report_path):
            #delete_folder_recursively(tmp_path)
            raise Exception("run test failed!")
        # TODO: 如果是Jenkins运行的，则需要下载报告
        sdk_test_name = os.path.splitext(sdk_test.test_name)[0]
        report_name = "sdk-%s-%s.html" %(sdk_test_name, str(int(1000* time.time())))
        report_path_new = os.path.join("reports", report_name)
        # 将报告拷贝到对应的报告目录下
        shutil.copy(report_path, report_path_new)
        #delete_folder_recursively(tmp_path)
        if request.POST.get('account') == "Jenkins":
            add_test_reports_testng(report_path_new)
            result = download_report_ex(request, report_path_new)
            return result
        else:
            with io.open(report_path_new, 'r', encoding='utf-8') as stream:
                reports = stream.read()
            #TODO：保存报告
            add_test_reports_testng(report_path_new, account)
            # 将报告拷贝到对应的报告目录下

            return render_to_response('view_report.html', {"reports": mark_safe(reports)})
    except:
        request.session["msg"] = u"运行失败"
        logger.info(traceback.format_exc())
        return HttpResponseRedirect('/api/sdk_test_list/1/')


@login_check
def update_sdk(request):
    #account = request.session["now_account"]
    if request.is_ajax():
        kwargs = json.loads(request.body.decode('utf-8'))
        project = kwargs.get("project")
        module_id = kwargs.get("module")
        #过滤出所有指定project和模块下的文件列表
        objs = FileInfo.objects.filter(project__project_name=project, module__id=module_id)
        #TODO：从列表中过滤出SDK和测试用例文件，
        sdk_list = [f.name for f in objs if f.name.endswith(r'.jar')]
        file_list = [f.name for f in objs if "test" in f.name]
        ret = {}
        ret["sdk"] = sdk_list
        ret["tests"] = file_list
        return JsonResponse(ret)

@login_check
@set_session
def ca_list(request, id):
    account = request.session["now_account"]
    #ca operation
    if request.is_ajax():
        kwargs = json.loads(request.body.decode('utf-8'))
        kwargs['author'] = account
        if kwargs.get('mode') == 'del':
            msg = del_ca_data(kwargs.pop('id'))
        elif kwargs.get('mode') == 'add':
            msg = add_ca_data(**kwargs)
        elif kwargs.get('mode') == 'get':
            msg = get_ca_data(**kwargs)
        elif kwargs.get('mode') == 'refresh':
            msg = refresh_ca_data(**kwargs)
        elif kwargs.get('mode') == 'cacfg':
            msg = get_cacfg(**kwargs)
        #operation failed, return error message
        return HttpResponse(get_ajax_msg(msg, 'ok'))

    #show ca list
    else:
        filter_query = set_filter_session(request)
        pro_list = get_pager_info(
            CaInfo, filter_query, '/api/ca_list/', id)

        ca_cfg_obj = CaCFG.objects.get(ca_type='dev')
        manage_info = {
            "ca_url" : ca_cfg_obj.ca_url,
            "ca_loginurl": ca_cfg_obj.ca_loginurl,
            'account': account,
            'page_list': pro_list[0],
            'ca_list': pro_list[1],
            'info': filter_query,
            'projects': ProjectInfo.objects.all().order_by('-update_time'),
        }
        return render_to_response('ca_list.html', manage_info)

@login_check
def update_ca_cfg(request):
    kwargs = json.loads(request.body.decode('utf-8'))
    ca_url = kwargs.get('ca_url', "")
    ca_loginurl = kwargs.get('ca_loginurl', "")
    ca_type = kwargs.get('ca_type_cfg', "")
    msg = update_ca_url_data(ca_url, ca_loginurl, ca_type)
    return HttpResponse(get_ajax_msg(msg, '更新成功！'))

@login_check
def add_ca_batch(request):
    """
    批量添加CA
    :param request:
    :return:
    """
    kwargs = json.loads(request.body.decode('utf-8'))
    ca_id = kwargs.get('ca_name')
    test_list = list(kwargs.get('data').keys())
    msg = update_test_ca(ca_id, test_list)
    return HttpResponse(get_ajax_msg(msg, '/api/test_list/1'))
