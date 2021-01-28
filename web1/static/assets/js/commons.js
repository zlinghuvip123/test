/*动态改变模块信息*/
var funcsDict = {"执行sql语句":"executeSql",
                "归档影像": "archiveDicom",
                "执行bat脚本" : "executeBat",
                "执行es语句": "executeES"
                }
function show_module(module_info, id) {
    module_info = module_info.split('replaceFlag');
    var a = $(id);
    a.empty();
    for (var i = 0; i < module_info.length; i++) {
        if (module_info[i] !== "") {
            var value = module_info[i].split('^=');
            a.prepend("<option value='" + value[0] + "' >" + value[1] + "</option>")
        }
    }
    //不需要在每个选择前面添加请选择目录。
    a.prepend("<option value='请选择' selected>请选择</option>");

}

function show_case(case_info, id) {
    case_info = case_info.split('replaceFlag');
    var a = $(id);
    a.empty();
    for (var i = 0; i < case_info.length; i++) {
        if (case_info[i] !== "") {
            var value = case_info[i].split('^=');
            a.prepend("<option value='" + value[0] + "' >" + value[1] + "</option>")
        }
    }
    a.prepend("<option value='请选择' selected>请选择</option>");

}

function show_sdk(sdk_info, id) {
    var a = $(id);
    a.empty();
    for(var i = 0; i < sdk_info.length; i++) {
            a.prepend("<option value='" + sdk_info[i] + "' >" + sdk_info[i] + "</option>")
        }
    a.prepend("<option value='请选择' selected>请选择</option>");

}

function show_file(file_info, id) {
    var a = $(id);
    a.empty();
    for (var i = 0; i < file_info.length; i++) {
        {
            a.prepend("<option value='" + file_info[i] + "' >" + file_info[i] + "</option>")
        }
    }
    a.prepend("<option value='请选择' selected>请选择</option>");

}


/*表单信息异步传输*/
function info_ajax(id, url) {
    var data = $(id).serializeJSON();
    if (id === '#add_task') {
        var include = [];
        var i = 0;
        $("ul#pre_case li a").each(function () {
            include[i++] = [$(this).attr('id'), $(this).text()];
        });
        data['module'] = include;
    }

    $.ajax({
        type: 'post',
        url: url,
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (data) {
            if (data !== 'ok') {
                if (data.indexOf('/api/') !== -1) {
                    window.location.href = data;
                } else {
                    myAlert(data);
                }
            }
            else {
                window.location.reload();
            }
        }
        ,
        error: function () {
            myAlert('Sorry，服务器可能开小差啦, 请重试!');
        }
    });

}

function auto_load(id, url, target, type) {
    var data = $(id).serializeJSON();
    if (id === '#form_message' || id ==='#belong_message' || id === '#pro_filter' || id === '#copy_list') {
        data = {
            "test": {
                "name": data,
                "type": type
            }
        }
    } else if (id === '#form_config') {
        data = {
            "config": {
                "name": data,
                "type": type
            }
        }
    } else {
        data = {
            "task": {
                "name": data,
                "type": type
            }
        }
    }
    $.ajax({
        type: 'post',
        url: url,
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (data) {
            if (type === 'module') {
                show_module(data, target)
            } else {
                show_case(data, target)
            }
        }
        ,
        error: function () {
            myAlert('Sorry，服务器可能开小差啦, 请重试!');
        }
    });

}

function refresh_sdk_file(id) {
    data = {
        "project": $('#project').val(),
        "module": $('#module').val()
    }
    $.ajax({
        type: 'post',
        url: "/api/update_sdk/",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (data) {
                //暂时不通过选择，直接手动输入sdk版本。
                //show_sdk(data["sdk"], "#sdk"),
                show_file(data['tests'], "#testfile")
        }
        ,
        error: function () {
            myAlert('Sorry，服务器可能开小差啦, 请重试!');
        }
    });

}

function update_data_ajax(id, url) {
    var data = $(id).serializeJSON();
    $.ajax({
        type: 'post',
        url: url,
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (data) {
            if (data !== 'ok') {
                myAlert(data);
            }
            else {
                window.location.reload();
            }
        },
        error: function () {
            myAlert('Sorry，服务器可能开小差啦, 请重试!');
        }
    });
}

function del_data_ajax(id, url) {
    var data = {
        "id": id,
        'mode': 'del'
    };
    $.ajax({
        type: 'post',
        url: url,
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (data) {
            if (data !== 'ok') {
                myAlert(data);
            }
            else {
                window.location.reload();
            }
        },
        error: function () {
            myAlert('Sorry，服务器可能开小差啦, 请重试!');
        }
    });
}

function update_testca_ajax(id, url) {
    var data = {
        "data": $(id).serializeJSON(),
        "ca_name": $('#ca_name').val()
    };
    $.ajax({
        type: 'post',
        url: url,
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (data) {
        if (data !== 'ok') {
                if (data.indexOf('/api/') !== -1) {
                    window.location.href = data;
                } else {
                    myAlert(data);
                }
            }
            else {
                window.location.reload();
            }
        },
        error: function () {
            myAlert('Sorry，服务器可能开小差啦, 请重试!');
        }
    });
}



function copy_data_ajax(id, url) {
    var data = {
        "data": $(id).serializeJSON(),
        'mode': 'copy'
    };
    $.ajax({
        type: 'post',
        url: url,
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (data) {
            if (data !== 'ok') {
                myAlert(data);
            }
            else {
                window.location.reload();
            }
        },
        error: function () {
            myAlert('Sorry，服务器可能开小差啦, 请重试!');
        }
    });
}

function convert_hooks(hooks){
    var hs = {}
    tests = []
    for (t in hooks.test) {
        var flag = false
        hs_test = {}
        if (!!hooks.test[t].value1 && !!funcsDict[hooks.test[t].value1]) {
            hs_test.key = "${" + funcsDict[hooks.test[t].value1] + "(" + hooks.test[t].key1+ ")}";
        }
        else {
            hs_test.key = ""
        }
        if (!!hooks.test[t].value2 && !!funcsDict[hooks.test[t].value2]) {
            hs_test.value = "${" + funcsDict[hooks.test[t].value2] + "(" + hooks.test[t].key2+ ")}";
        }
        else {
            hs_test.value = ""
        }
        tests.push(hs_test)
    }
    hs["test"] = tests;
    return hs
}

function case_ajax(type, editor) {
    var url = $("#url").serializeJSON();
    var method = $("#method").serializeJSON();
    var dataType = $("#DataType").serializeJSON();
    var caseInfo = $("#form_message").serializeJSON();
    var variables = $("#form_variables").serializeJSON();
    var request_data = null;
    if (dataType.DataType === 'json') {
        try {
            request_data  = eval('(' + editor.session.getValue() + ')');
        }
        catch (err) {
            myAlert('Json格式输入有误！');
            return
        }
    } else {
        request_data = $("#form_request_data").serializeJSON();
    }
    var headers = $("#form_request_headers").serializeJSON();
    var extract = $("#form_extract").serializeJSON();
    var validate = $("#form_validate").serializeJSON();
    var parameters = $('#form_params').serializeJSON();
    var hooks = $('#form_hooks').serializeJSON();
    var include = [];
    var i = 0;
    $("ul#pre_case li a").each(function () {
        include[i++] = [$(this).attr('id'), $(this).text()];
    });
    caseInfo['include'] = include;
    const test = {
        "test": {
            "name": caseInfo,
            "parameters": parameters,
            "variables": variables,
            "request": {
                "url": url.url,
                "method": method.method,
                "headers": headers,
                "type": dataType.DataType,
                "request_data": request_data
            },
            "extract": extract,
            "validate": validate,
            "hooks": convert_hooks(hooks)
        }
    };
    if (type === 'edit') {
        url = '/api/edit_case/';
    } else {
        url = '/api/add_case/';
    }
    $.ajax({
        type: 'post',
        url: url,
        data: JSON.stringify(test),
        contentType: "application/json",
        success: function (data) {
            if (data === 'session invalid') {
                window.location.href = "/api/login/";
            } else {
                if (data.indexOf('/api/') != -1) {
                    window.location.href = data;
                } else {
                    myAlert(data);
                }
            }
        },
        error: function () {
            myAlert('Sorry，服务器可能开小差啦, 请重试!');
        }
    });
}

function config_ajax(type) {
    var dataType = $("#config_data_type").serializeJSON();
    var caseInfo = $("#form_config").serializeJSON();
    var variables = $("#config_variables").serializeJSON();
    var parameters = $('#config_params').serializeJSON();
    var hooks = $('#config_hooks').serializeJSON();
    var request_data = null;
    if (dataType.DataType === 'json') {
        try {
            request_data = eval('(' + editor.session.getValue() + ')');
        }
        catch (err) {
            myAlert('Json格式输入有误！');
            return
        }
    } else {
        request_data = $("#config_request_data").serializeJSON();
    }
    var headers = $("#config_request_headers").serializeJSON();

    const config = {
        "config": {
            "name": caseInfo,
            "variables": variables,
            "parameters": parameters,
            "request": {
                "headers": headers,
                "type": dataType.DataType,
                "request_data": request_data
            },
            "hooks": hooks

        }
    };
    if (type === 'edit') {
        url = '/api/edit_config/';
    } else {
        url = '/api/add_config/';
    }
    $.ajax({
        type: 'post',
        url: url,
        data: JSON.stringify(config),
        contentType: "application/json",
        success: function (data) {
            if (data === 'session invalid') {
                window.location.href = "/api/login/";
            } else {
                if (data.indexOf('/api/') != -1) {
                    window.location.href = data;
                } else {
                    myAlert(data);
                }
            }
        },
        error: function () {
            myAlert('Sorry，服务器可能开小差啦, 请重试!');
        }
    });
}

/*提示 弹出*/
function myAlert(data) {
    $('#my-alert_print').text(data);
    $('#my-alert').modal({
        relatedTarget: this
    });
}

function post(url, params) {
    var temp = document.createElement("form");
    temp.action = url;
    temp.method = "post";
    temp.contentType = "application/json";
    temp.style.display = "none";
    for (var x in params) {
        var opt = document.createElement("input");
        opt.name = x;
        opt.value = params[x];
        temp.appendChild(opt);
    }
    document.body.appendChild(temp);
    temp.submit();
    return temp;
}

function del_row(id) {
    var attribute = id;
    var chkObj = document.getElementsByName(attribute);
    var tabObj = document.getElementById(id);
    for (var k = 0; k < chkObj.length; k++) {
        if (chkObj[k].checked) {
            tabObj.deleteRow(k + 1);
            k = -1;
        }
    }
}

function add_hooks(id) {

    var tabObj = document.getElementById(id);//获取添加数据的表格
    var rowsNum = tabObj.rows.length;  //获取当前行数
    var style = 'width:100%; border: none';
    var cell_check = "<input type='checkbox' name='" + id + "' style='width:55px' />";
    var cell_key1 = "<input type='text' name='test[][key1]'  value='' style='" + style + "' />";
    var cell_value1 = "<select name='test[][value1]' class='form-control' style='height: 25px; font-size: 15px; " +
        "padding-top: 0px; padding-left: 0px; border: none'> " + "<option></option>"
    var cell_key2 = "<input type='text' name='test[][key2]'  value='' style='" + style + "' />";
    var cell_value2 = "<select name='test[][value2]' class='form-control' style='height: 25px; font-size: 15px; " +
        "padding-top: 0px; padding-left: 0px; border: none'> " + "<option></option>"

    for (var key in funcsDict) {
        cell_value1 += "<option>" + key + "</option>";
        cell_value2 += "<option>" + key + "</option>";
    }
    cell_value1 += "</select>";
    cell_value2 += "</select>";

    var myNewRow = tabObj.insertRow(rowsNum);
    var newTdObj0 = myNewRow.insertCell(0);
    var newTdObj1 = myNewRow.insertCell(1);
    var newTdObj2 = myNewRow.insertCell(2);
    var newTdObj3 = myNewRow.insertCell(3);
    var newTdObj4 = myNewRow.insertCell(4);
    newTdObj0.innerHTML = cell_check
    newTdObj1.innerHTML = cell_value1;
    newTdObj2.innerHTML = cell_key1;
    newTdObj3.innerHTML = cell_value2;
    newTdObj4.innerHTML = cell_key2;
}


function add_row(id) {
    var tabObj = document.getElementById(id);//获取添加数据的表格
    var rowsNum = tabObj.rows.length;  //获取当前行数
    var style = 'width:100%; border: none';
    var cell_check = "<input type='checkbox' name='" + id + "' style='width:55px' />";
    var cell_key = "<input type='text' name='test[][key]'  value='' style='" + style + "' />";
    var cell_value = "<input type='text' name='test[][value]'  value='' style='" + style + "' />";
    var cell_type = "<select name='test[][type]' class='form-control' style='height: 25px; font-size: 15px; " +
        "padding-top: 0px; padding-left: 0px; border: none'> " +
        "<option>string</option><option>int</option><option>float</option><option>boolean</option><option>file</option></select>";
    var cell_comparator = "<select name='test[][comparator]' class='form-control' style='height: 25px; font-size: 15px; " +
        "padding-top: 0px; padding-left: 0px; border: none'> " +
        "<option>equals</option> <option>contains</option> <option>startswith</option> <option>endswith</option> <option>regex_match</option> <option>type_match</option> <option>contained_by</option> <option>less_than</option> <option>less_than_or_equals</option> <option>greater_than</option> <option>greater_than_or_equals</option> <option>not_equals</option> <option>string_equals</option> <option>length_equals</option> <option>length_greater_than</option> <option>length_greater_than_or_equals</option> <option>length_less_than</option> <option>length_less_than_or_equals</option></select>";

    var myNewRow = tabObj.insertRow(rowsNum);
    var newTdObj0 = myNewRow.insertCell(0);
    var newTdObj1 = myNewRow.insertCell(1);
    var newTdObj2 = myNewRow.insertCell(2);


    newTdObj0.innerHTML = cell_check
    newTdObj1.innerHTML = cell_key;
    if (id === 'variables' || id === 'data') {
        var newTdObj3 = myNewRow.insertCell(3);
        newTdObj2.innerHTML = cell_type;
        newTdObj3.innerHTML = cell_value;
    } else if (id === 'validate') {
        var newTdObj3 = myNewRow.insertCell(3);
        newTdObj2.innerHTML = cell_comparator;
        newTdObj3.innerHTML = cell_type;
        var newTdObj4 = myNewRow.insertCell(4);
        newTdObj4.innerHTML = cell_value;
    } else {
        newTdObj2.innerHTML = cell_value;
    }
}

function add_params(id) {
    var tabObj = document.getElementById(id);//获取添加数据的表格
    var rowsNum = tabObj.rows.length;  //获取当前行数
    var style = 'width:100%; border: none';
    var check = "<input type='checkbox' name='" + id + "' style='width:55px' />";
    var placeholder = '单个:["value1", "value2],  多个:[["name1", "pwd1"],["name2","pwd2"]]';
    var key = "<textarea  name='test[][key]'  placeholder='单个:key, 多个:key1-key2'  style='" + style + "' />";
    var value = "<textarea  name='test[][value]'  placeholder='" + placeholder + "' style='" + style + "' />";
    var myNewRow = tabObj.insertRow(rowsNum);
    var newTdObj0 = myNewRow.insertCell(0);
    var newTdObj1 = myNewRow.insertCell(1);
    var newTdObj2 = myNewRow.insertCell(2);
    newTdObj0.innerHTML = check;
    newTdObj1.innerHTML = key;
    newTdObj2.innerHTML = value;
}


function init_acs(language, theme, editor) {
    editor.setTheme("ace/theme/" + theme);
    editor.session.setMode("ace/mode/" + language);

    editor.setFontSize(17);

    editor.setReadOnly(false);

    editor.setOption("wrap", "free");

    ace.require("ace/ext/language_tools");
    editor.setOptions({
        enableBasicAutocompletion: true,
        enableSnippets: true,
        enableLiveAutocompletion: true,
        autoScrollEditorIntoView: true
    });
}

function initFileInput(ctrlName) {
    var control = $('#' + ctrlName);
    control.fileinput({
        resizeImage: true,
        resizePreference: 'width',
        uploadAsync: false,                             //采用同步上传
        language: 'zh', //设置语言
        uploadUrl: '/api/upload_file/',
        //allowedFileExtensions: ['yml', 'yaml', 'json'],//接收的文件后缀
        showUpload: true, //是否显示上传按钮
        showRemove: true,
        showCaption: true,//是否显示标题
        browseClass: "btn btn-primary", //按钮样式
        previewFileIcon: "<i class='glyphicon glyphicon-king'></i>",
        maxFileCount: 10,
        msgFilesTooMany: "选择文件超过了最大数量",
        maxFileSize: 200000,
        autoReplace: true,
        showPreview: false,
        uploadExtraData:
            function () {     //上传时要传输的其他参数
                project_name = $('#project option:selected').text();//选中的文本
                module_name = $('#upload_belong_module_id option:selected').val();//选中的module的ID
                return {"project": project_name, "module": module_name};
            },
        showClose: true,//显示右上角X关闭
        overwriteInitial: false,
        dropZoneEnabled: true//是否显示拖拽区域
    });
    control.on('fileerror', function (event, data, msg) {
        myAlert(msg)
    });
    control.on("filepredelete", function(event, key) {
        return !confirm("确定删除该文件？")
    });
    control.on("filebatchuploadsuccess", function (event, data) {
        var obj = data.response;
        $("#bulk_uploadcase").trigger('click');
        if (obj.status === "Success") {
            window.location.href = obj.message;
        } else {
            myAlert("以下文件上传失败:" + obj.message);
            //window.location.reload();
        }
    });
}


