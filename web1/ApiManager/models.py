from django.db import models
from django.forms import widgets

from ApiManager.managers import UserTypeManager, UserInfoManager, ProjectInfoManager, ModuleInfoManager, \
    TestCaseInfoManager, EnvInfoManager, FileInfoManager
import django.utils.timezone as timezone


# Create your models here.


class BaseTable(models.Model):
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        abstract = True
        verbose_name = "公共字段表"
        db_table = 'BaseTable'


class UserType(BaseTable):
    class Meta:
        verbose_name = '用户类型'
        db_table = 'UserType'

    type_name = models.CharField(max_length=20)
    type_desc = models.CharField(max_length=50)
    objects = UserTypeManager()


class UserInfo(BaseTable):
    class Meta:
        verbose_name = '用户信息'
        db_table = 'UserInfo'

    username = models.CharField('用户名', max_length=20, unique=True)
    password = models.CharField('密码', max_length=20)
    email = models.EmailField('邮箱', null=False, unique=True)
    status = models.IntegerField('有效/无效', default=1)
    # user_type = models.ForeignKey(UserType, on_delete=models.CASCADE)
    objects = UserInfoManager()


class ProjectInfo(BaseTable):
    class Meta:
        verbose_name = '项目信息'
        db_table = 'ProjectInfo'

    project_name = models.CharField('项目名称', max_length=50, unique=True)
    responsible_name = models.CharField('负责人', max_length=20)
    test_user = models.CharField('测试人员', max_length=100)
    dev_user = models.CharField('开发人员', max_length=100)
    publish_app = models.CharField('发布应用', max_length=100)
    simple_desc = models.CharField('简要描述', max_length=100, null=True)
    other_desc = models.CharField('其他信息', max_length=100, null=True)
    objects = ProjectInfoManager()


class ModuleInfo(BaseTable):
    class Meta:
        verbose_name = '模块信息'
        db_table = 'ModuleInfo'

    module_name = models.CharField('模块名称', max_length=50)
    belong_project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE)
    test_user = models.CharField('测试负责人', max_length=50)
    simple_desc = models.CharField('简要描述', max_length=100, null=True)
    other_desc = models.CharField('其他信息', max_length=100, null=True)
    objects = ModuleInfoManager()

class CaInfo(BaseTable):
    class Meta:
        verbose_name = 'CA信息管理'
        db_table = 'CaInfo'

    user_name = models.CharField('用户名称', max_length=50)
    author = models.CharField('添加人员', max_length=50, null=True)
    #status = models.BooleanField("状态", default=True)
    belong_project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE)
    #value = models.TextField('ca值', null=True)
    redirect_url = models.CharField("redirect_url", max_length=100,  default='@@@redirect_url@@@' )
    client_id = models.CharField('客户端名称', max_length=50)
    password = models.CharField('密码', max_length=50, default='')
    #expire_time = models.DateTimeField('到期时间', null=True)

class TestCaseInfo(BaseTable):
    class Meta:
        verbose_name = '用例信息'
        db_table = 'TestCaseInfo'

    type = models.IntegerField('test/config', default=1)
    name = models.CharField('用例/配置名称', max_length=100)
    belong_project = models.CharField('所属项目', max_length=50)
    #project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE)
    belong_module = models.ForeignKey(ModuleInfo, on_delete=models.CASCADE)
    include = models.CharField('前置config/test', max_length=1024, null=True)
    author = models.CharField('编写人员', max_length=20)
    request = models.TextField('请求信息')
    ca = models.ForeignKey(CaInfo, null=True, on_delete=models.SET_NULL)

    objects = TestCaseInfoManager()


class TestReports(BaseTable):
    class Meta:
        verbose_name = "测试报告"
        db_table = 'TestReports'

    report_name = models.CharField(max_length=100)
    start_at = models.CharField(max_length=40, null=True)
    status = models.BooleanField()
    testsRun = models.IntegerField()
    successes = models.IntegerField()
    reports = models.TextField()
    author = models.CharField(max_length=100, default='')


class EnvInfo(BaseTable):
    class Meta:
        verbose_name = '环境管理'
        db_table = 'EnvInfo'

    env_name = models.CharField(max_length=40,  unique=True)
    base_url = models.CharField(max_length=200)
    simple_desc = models.CharField(max_length=50)
    objects = EnvInfoManager()


class TestSuite(BaseTable):
    class Meta:
        verbose_name = '用例集合'
        db_table = 'TestSuite'

    belong_project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE)
    suite_name = models.CharField(max_length=100)
    include = models.TextField()
    disabled_cnt = models.IntegerField('停用的用例数目', default=0)


class FileInfo(BaseTable):
    class Meta:
        verbose_name = '上传文件管理'
        db_table = 'FileInfo'

    name = models.CharField('文件名称', max_length=200)
    belong_project = models.CharField('所属项目', max_length=50)
    belong_module = models.CharField('所属模块', max_length=50)
    author = models.CharField('上传人员', max_length=20)
    file_path = models.CharField('文件路径', max_length=250, default='')
    create_time = models.DateTimeField('上传时间', default=timezone.now)
    file_size = models.IntegerField('文件大小', default=0)
    project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE, default=1)
    module = models.ForeignKey(ModuleInfo, on_delete=models.CASCADE, default=1)
    objects = FileInfoManager()

class SDKTestInfo(BaseTable):
    class Meta:
        verbose_name = 'SDK测试信息管理'
        db_table = 'SDKTestInfo'

    sdk_name = models.CharField('SDK文件名称', max_length=500)
    test_name = models.CharField('测试文件名称', max_length=50)
    others = models.CharField('其它文件', max_length=200, null=True)
    author = models.CharField('上传人员', max_length=20)
    create_time = models.DateTimeField('上传时间', default=timezone.now)
    belong_project = models.ForeignKey(ProjectInfo, on_delete=models.CASCADE, default=1)
    belong_module = models.ForeignKey(ModuleInfo, on_delete=models.CASCADE, default=1)
    #objects = FileInfoManager()

class CaCFG(BaseTable):
    class Meta:
        verbose_name = 'CA基础配置'
        db_table = 'CaCfg'

    ca_url = models.CharField('CA请求地址', max_length=500)
    ca_loginurl = models.CharField('CA登录地址', max_length=500)
    ca_type = models.CharField('CA类型', max_length=50, default='dev')
