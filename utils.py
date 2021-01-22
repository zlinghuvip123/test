# encoding=utf-8
import os
import shutil
import traceback
from bs4 import BeautifulSoup
import re
import datetime
import sys
import stat
import requests
import time
import copy
import json
import subprocess
import csv

class HealthException(Exception):
    pass


def _get_remotesession_name():
    # 通过query user来获取远程连接的session name, 然后通过tscon.exe命令来关闭远程连接
    try:
        p = subprocess.Popen("query user", stdout=subprocess.PIPE)
        u_line = p.stdout.readlines()[1]
        s_name = u_line.split()[1]
        s_name = str(s_name, encoding = "utf-8")
        assert s_name.startswith(r"rdp-tcp")
        return s_name
    except:
        traceback.print_exc()
        return r'rdp-tcp#0'


def _kill_remoteconn():
    try:
        session_name = _get_remotesession_name()
        print(session_name)
        # 如果系统有被远程桌面过，则系统会处于登录界面，可能会造成寻找控件失败的问题，所以先关闭远程桌面连接。
        subprocess.call(r'tscon %s /dest:console' %(session_name))
        # subprocess.call(os.path.join(os.path.dirname(__file__), "CloseRDP.bat"))
    except:
        traceback.print_exc()
    try:
        # 如果远程连接已经手动关闭了，则通过上述的方案无法关闭，无法恢复默认显示分辨率。需要使用以下方式。
        bat_path = os.path.join(os.path.dirname(__file__), "Close_RDP.bat")
        subprocess.call(bat_path)
    except:
        traceback.print_exc()


def _kill_process(p_name):
    try:
        subprocess.call("taskkill /F /IM %s" %(p_name))
    except:
        pass


def _get_resolution(msg):
    import win32api
    import win32con
    print(msg)
    print(win32api.GetSystemMetrics(win32con.SM_CXSCREEN))
    print(win32api.GetSystemMetrics(win32con.SM_CYSCREEN))


def init_env():
    try:
        _get_resolution("==== resolution before kill remoteconn=====")
        _kill_remoteconn()
        _get_resolution("==== resolution after kill remoteconn=====")
        _kill_process("chrome.exe")
        _kill_process("chromedriver.exe")
        _kill_process("katalon.exe")
    except:
        pass


def del_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)


if sys.version_info.major == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
    # python2默认使用ascii编码方式去读取python源文件，所以需要重新设置一下
else:
    print(sys.version_info)


def health_check(start_time, url):
    fp = sys.stdout
    print("============healthCheck:" + url)
    print("============start_time:" + str(start_time))
    fp.flush()
    if url.split(r'/')[-1] == 'health':
        def url_check(url):
            #print("i am in health")
            ret_json = requests.get(url, verify=True).json()
            if ret_json['status'] == 'UP':
                return True
            else:
                return False
    else:
        def url_check(url):
            #print("i am in other")
            if requests.get(url, verify=True).status_code == 200:
                return True
            else:
                return False

    try:
        if url_check(url):
            time.sleep(10)
            if url_check(url):
                print("==========healthCheck:%s =======passed" %(url))
                fp.flush()
                return
    except:
        pass
    # 600s内如果没有响应200的话，直接exception.测试直接不执行
    # 600s内需要检测两次，如果间隔5秒的状态都是200，则说明的确是OK了。
    # 解决问题：上一秒是200，下一秒又不是200了，具体为什么会出现这种情况，我也不知道。
    ret_status = False
    pass_cnt = 0
    while (time.time() - start_time < 600):
        try:
            if url_check(url):
                pass_cnt += 1
                if pass_cnt == 2:
                    ret_status = True
                    break
            else:
                pass_cnt = 0
        except:
            pass_cnt = 0
            print("==========healthCheck:%s =======not 200!" % (url))
            fp.flush()
            pass
        time.sleep(5)
        print("============== current time:" + str(time.time()))
    # if resp.status_code != 200, raise exception
    if ret_status: # 可能在超时时pass_cnt ==1, 这时候也算为不通过把。
        print("==========healthCheck:%s =======passed" % (url))
        fp.flush()
    else:
        print("==========healthCheck:%s =======failed" % (url))
        fp.flush()
        raise HealthException


def delete_recursively(dPath):
    for pf in os.listdir(dPath):
        if os.path.isfile(os.path.join(dPath, pf)):
            os.chmod(os.path.join(dPath, pf), stat.S_IWRITE)
            os.remove(os.path.join(dPath, pf))
        else:
            delete_recursively(os.path.join(dPath, pf))
    os.rmdir(dPath)


report_head = """
<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.0 Strict//EN''http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'>
<html xmlns='http://www.w3.org/1999/xhtml'>
<meta http-equiv='Content-Type' content='text/html; charset=utf-8' />
 <head>
 </head> 
   <style>
     .table1 { 
     	  background-repeat: repeat-x; 
     	  background-attachment: scroll;
     	  background-position: center center;
     	  border-collapse:collapse; 
     	  width: 750px; 
        } 
      .div { 
      	  background-repeat: repeat; 
      	  background-attachment: scroll; 
     	  background-position: center center; 
      	  margin-top: 10px; 
      	  white-space: nowrap; 
          } 
       .td { 
      	  border: 1px solid #61C3ED; 
      	  border-right-color: #0093D9; 
      	  border-bottom-color: #0093D9; 
      	  background: #fff; 
      	  font-size:15px; 
      	  padding: 2px; 
      	  color: #4f6b72; 
      	  text-align:center; 
      	  font-family: Calibri; 
          } 
        .link { 
          color: #00AAAA; 
           text-decoration:none; 
          } 
      </style> 
       <body> 
      	  <div class='div' align='center'> 
      		  <table class='table1'> 
      			 <tbody> 
                     <tr> 
                       <td class='td' style='font-size:20px ; color:white; background:#0B9BB5' colspan=6><b> Test Result</b></td> 
                     </tr>
"""
report_sheet_templ = """
</tbody>
 </table>
 	  </div>
 	  <div  align='center' style='margin-top:10px'>
 		  <table class='table1'>
 			  <tbody>
 			  <tr>
 				<td class='td' style='font-size:20px ; color:white; background:#0B9BB5' colspan=6><b>Test Report Details:</b></td>
 			   </tr>
 			<tr>
                 <td class='td' colspan=2><b>Test Case</b></td>
                 <td class='td' colspan=2><b>Description</b></td>
                 <td class='td'><b>Result</b></td>
                 <td class='td'><b>Run Times</b></td>
 			</tr>
 		"""
report_tail = """
                        </tbody>
                     </table>
                    </div>
                  </body>
                </html>
            """


def gen_summary(feature_name, start_time, duration, total, passed):
    passrate = (100 * float(passed) / total) if total > 0 else 0
    summary = ""
    summary += r"<tr>"
    summary += r"<td class='td' width='100px' style='text-align:right; color:blue'><b>Feature Name:</b></td>"
    summary += r"<td class='td' width='150px' style='text-align:left; color:blue'><b>%s</b></td>" % (feature_name)
    summary += r"<td class='td' width='100px' style='text-align:right; color:blue'><b>Start_time:</b></td>"
    summary += r"<td class='td' width='150px' style='text-align:left; color:blue'><b>%s</b></td>" % (start_time)
    summary += r"<td class='td' width='100px' style='text-align:right; color:blue'><b>Duration:</b></td>"
    summary += r"<td class='td' width='150px' style='text-align:left; color:blue'><b>%ss</b></td>" % (duration)
    summary += r"</tr>"
    summary += r"<tr>"
    summary += r"<td class='td' width='100px' style='text-align:right; color:blue'><b>Total Case:</b></td>"
    summary += r"<td class='td' width='150px' style='text-align:left; color:blue'><b>%s</b></td>" % (total)
    summary += r"<td class='td' width='100px' style='text-align:right; color:blue'><b>Passed:</b></td>"
    summary += r"<td class='td' width='150px' style='text-align:left; color:blue'><b>%s</b></td>" % (passed)
    summary += r"<td class='td' width='100px' style='text-align:right; color:blue'><b>Pass Rate:</b></td>"
    summary += r"<td class='td' width='150px' style='text-align:left; color:%s'><b>%.2f" % ("red" if passrate < 96 else "blue", passrate)
    summary += r"%</b></td></tr>"
    return summary


def parse_report_api(report_in, report_out, feature_name, msg):
    '''
    解析接口测试平台输出的报告，由于接口测试平台输出的报告中有很多JS，在邮箱中是无法显示的，需要将报告简化成不带JS的形式。
    :param report_in:  接口测试平台输出的报告
    :param report_out:  解析后生成的报告名称
    :param feature_name: feature名称
    :return:
    '''
    if not msg:
        try:
            if sys.version_info.major == 2:
                soup = BeautifulSoup(open(report_in))
            else:
                soup = BeautifulSoup(open(report_in, encoding='utf8'))
            summary = soup.find('table', id='summary')
            test_items = soup.find_all('table', id=re.compile("suite_"))
            start_time = summary.find("th", text="START AT").find_next_sibling().text
            duration = summary.find("th", text="DURATION").find_next_sibling().text
            report_url = soup.find('a', id='url')['href']

            result_detail = ''
            total = 0
            passed = 0
            for test_item in test_items:
                title = test_item.find_previous_sibling().text
                success_cnt_str = test_item.find("td", text=re.compile("SUCCESS")).text
                total_cnt_str = test_item.find("td", text=re.compile("TOTAL")).text
                success_cnt = eval(success_cnt_str.split(':')[1])
                total_cnt = eval(total_cnt_str.split(':')[1])
                result_detail += r"<tr>"
                result_detail += r"<td class='td' style='style='text-align:left; color:green' colspan=4>%s</td>" % (title)
                if  total_cnt == success_cnt:
                    passed += 1
                    result_detail += r"<td class='td' style='color:green'>PASS</td>"
                else:
                    result_detail += r"<td class ='td' style='color:red'>FAILED</td>"
                result_detail += r"<td class ='td' style='color:green'>1</td></tr>"
                total += 1
            attachment_link = "Test Report Details:<a href='" + report_url + "'>Attachment Link</a>"
            report_sheet_templ_tmp = report_sheet_templ.replace("Test Report Details:", attachment_link)
            summary = gen_summary(feature_name, start_time, duration, total, passed)
            result_content = report_head + summary + report_sheet_templ_tmp + result_detail + report_tail
        except IOError:
            result_content = "<h5>解析报告时未找到指定报告，请确认接口测试平台是否正常!</h5>"
        except:
            print(traceback.print_exc())
            # 如果解析报告的时候出错了，则直接将错误页面作为报告页面
            if sys.version_info.major == 2:
                with open(report_in, 'r') as pf:
                    result_content = pf.read()
            else:
                with open(report_in, 'r', encoding='utf8') as pf:
                    result_content = pf.read()

    else:
        result_content = msg
    # 接口测试是默认在master所在机器上运行的，使用的是python2. open函数不支持encoding参数，而Linux系统的默认编码是utf8,所以文件也会默认用utf8编码，不用手动加编码方式。
    with open(report_out, 'w') as pf:
        pf.write(result_content)


def _read_from_file_and_cov2_dict(file_path, caseName_map):
    case_list = []
    assert os.path.exists(file_path)
    with open(file_path, encoding='utf8') as pf:
        for fStr in pf.readlines():
            fJson = json.loads(fStr)
            if fJson.get("testCaseName", ""):
                # 通过map中获取到对应test ID 的description作为测试用例的中文名称
                case_id = fJson.get("testCaseId", "")
                case_desc = caseName_map.get(case_id, case_id)
                case_name_desc = '{}@@@@{}'.format(case_id, case_desc)
                case_list.append([case_name_desc, fJson.get("bindedValues", "")])
    return case_list


def _parse_test_result(file_path):
    ret_list = []
    soup = BeautifulSoup(open(file_path, encoding='utf8'), features="html.parser")
    test_items = soup.find_all('testcase')

    for test_item in test_items:
        result = test_item.attrs["status"]
        ret_list.append(result)
    return ret_list


def _parse_test_name_description(file_path):
    case_map = {}
    with open(file_path, "r", encoding='utf8', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0].startswith('Test Cases'):
                case_map[row[0]] = row[2]
    return case_map


def _merge_test_result(case_list, result_list):
    merged_testlist = []
    for index in range(len(case_list)):
        tmp = copy.deepcopy(case_list[index])
        tmp.append(result_list[index])
        merged_testlist.append(tmp)
    return merged_testlist


def _get_result_from_report_folder(folder_path):
    results_list = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if f.endswith('csv'):
                f1 = 'JUnit_Report.xml'
                reportXml_path = os.path.join(root, f1)
                # 通过Csv报告中的用例的描述中获取中文名称
                reportCsv_path = os.path.join(root, f)
                testCase_path = os.path.join(root, "testCaseBinding")
                result_list = _parse_test_result(reportXml_path)
                caseName_map = _parse_test_name_description(reportCsv_path)
                case_list = _read_from_file_and_cov2_dict(testCase_path, caseName_map)
                result = _merge_test_result(case_list, result_list)
                results_list.extend(result)
    return results_list


def _result_duplicate_removal(results_list):
    ret_list = {}
    '''
    {
    "caseName1": [runTimes, result],
    "caseName2": [runTimes, result],
    }
    '''
    for ret in results_list:
        caseEx = ret[0] + "&&&&" + str(ret[1])
        status = True if ret[2] == "PASSED" else False
        if caseEx in ret_list.keys():
            if not (ret_list[caseEx][1] and status):
                ret_list[caseEx][0] += 1
            ret_list[caseEx][1] |= status
        else:
            ret_list.setdefault(caseEx, [1, status])
    return ret_list


def copy_report():
    '''
    Katalon偶现无法将生成的报告拷贝到指定的目录下，当前是testreport目录，然后导致从UI测试机归档到master的时候报错
    这里会再次检测当前是否已经拷贝的报告，如果没有拷贝成功，则手动拷贝报告到testreport目录
    :return:no return
    '''
    try:
        currentPath = os.environ["WORKSPACE"]
        testreport = os.path.join(currentPath, 'testreport')
        if os.path.exists(testreport):
            print("UI报告已生成到对应目录下")
        else:
            projPath = os.path.join(currentPath, 'uih_cloud_ui')
            folderToCopy = ""
            for root, dirs, files in os.walk(projPath):
                for f in files:
                    if f == "JUnit_Report.xml":
                        folderToCopy = root
            if folderToCopy:
                shutil.copytree(folderToCopy, testreport)
    except:
        traceback.print_exc()
        raise


def _get_params_from_report(test_report_path):
    # duration暂时使用所有运行的duration的和。
    # 另外一种计算方法时最后一个报告的开始时间-第一个报告的开始时间+最后一个报告中的duration
    last_duration = 0
    last_start_at = None
    first_start_at = datetime.datetime.now()
    def _inner_func(report_path):
        soup = BeautifulSoup(open(report_path, encoding='utf8'))
        summary = soup.find('testsuite')
        duration = int(summary.attrs["time"])
        start_at = datetime.datetime.strptime(summary.attrs["timestamp"], "%Y-%m-%d %H:%M:%S")
        return duration, start_at

    for root, _ , files in os.walk(test_report_path):
        for f in files:
            if f == "JUnit_Report.xml":
                report_file = os.path.join(root, f)
                duration_in, start_at_in = _inner_func(report_file)
                first_start_at = min(first_start_at, start_at_in)
                last_start_at = max(start_at_in, last_start_at) if last_start_at else start_at_in
                last_duration = duration_in if last_start_at == start_at_in else 0
    time_delta = last_start_at - first_start_at
    duration_1 = time_delta.days * 3600 * 24 + time_delta.seconds  # 计算最后一个start_at和第一个start_at的差
    duration = duration_1 + last_duration
    return duration, first_start_at


def _get_case_name(case):
    print(case)
    full_case_name, binding_vars = case.split('&&&&')
    case_name = full_case_name.split(r'/')[-1]
    if binding_vars:
        description = eval(binding_vars).get("description", "")
        if description:
            case_name = "%s[%s]" %(case_name, description)
    return case_name


def parse_report_ui_junit(test_report_path, report_out, feature_name, msg, ret_log=""):
    '''
    解析Katalon生成的UI测试报告
    :param report_in:  Katalon测试平台输出的报告
    :param report_out:  解析后生成的报告名称
    :param feature_name: feature名称
    :return:
    '''
    # sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='gb18030')
    no_result_flag = False
    if not msg:
        try:
            # copy_report()
            results_list = _get_result_from_report_folder(test_report_path)
            ret_list = _result_duplicate_removal(results_list)
            duration, start_at = _get_params_from_report(test_report_path)

            # 如果没有任何结果，则说明测试结果文件未找到
            if not len(ret_list):
                raise Exception

            passed_cnt = 0
            failed_cnt = 0

            result_detail = ""
            for case, result in ret_list.items():
                #title = case.split('&&&&')[0]
                title = _get_case_name(case)
                case_id, case_desc = title.split('@@@@')
                status = result[1]
                run_times = result[0]
                result_detail += r"<tr>"
                result_detail += r"<td class='td' style='text-align:left;color:green' colspan=2>%s</td>" % (case_id)
                result_detail += r"<td class='td' style='text-align:left;color:green' colspan=2>%s</td>" % (case_desc)
                if status:
                    result_detail += r"<td class='td' style='color:green'>PASS</td>"
                    passed_cnt += 1
                else:
                    result_detail += r"<td class='td' style='color:red'>FAILED</td>"
                    failed_cnt +=1
                if run_times > 1:
                    result_detail += r"<td class='td' style='color:red'>%s</td>" %(run_times)
                else:
                    result_detail += r"<td class='td' style='color:green'>%s</td>"%(run_times)
                result_detail += r"</tr>"

            attachment_link = "Test Report Details:<a href='" + os.path.join(os.environ.get("BUILD_URL",""), 'artifact/testreport/') + "'>Attachment Link</a>"
            # attachment_link = "aaaaaa"
            report_sheet_templ_tmp = report_sheet_templ.replace("Test Report Details:", attachment_link)
            summary = gen_summary(feature_name, start_at, duration, passed_cnt + failed_cnt, passed_cnt)
            result_content = report_head + summary + report_sheet_templ_tmp + result_detail + report_tail
            # save_result(feature_name, "ui", passed_cnt + failed_cnt, passed_cnt)
        except:
            traceback.print_exc()
            no_result_flag = True
            result_content = "<h5>解析报告时未找到指定报告,请确认对应UI测试机器中Katalon是否能正常输出报告!</h5>"
    else:
        no_result_flag = True
        result_content = msg

    if no_result_flag:
        pass
        # save_result(feature_name, "ui", 0, 0)
    # UI测试将在Windows机器上运行，Windows机器上是python3, open函数支持使用encoding参数
    with open(report_out, 'w', encoding='utf-8') as pf:
        pf.write(result_content)


DEBUG = True

if __name__ == "__main__":
    parse_report_ui_junit(r"C:\Jenkins_home\workspace\test\fc_ui_auto\Reports", "tmp.html", "DMS", "")
