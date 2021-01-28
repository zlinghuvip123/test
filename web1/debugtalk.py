# -*- coding: utf-8 -*-
# debugtalk.py
import pymysql
import string
import random
import os
import hashlib
import subprocess
import time
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler
from elasticsearch import Elasticsearch
from logging.handlers import RotatingFileHandler
from chardet.universaldetector import UniversalDetector
import traceback
import urllib
import re
import json
from django.conf import settings


#os.environ['http_proxy'] = 'http://10.6.209.203:8080'
#os.environ['https_proxy'] = 'https://10.6.209.203:8080'

log_file_path = os.path.join(settings.BASE_DIR, "logs", "debugtalk.log")
logger = logging.getLogger(__name__)
logger.setLevel(level = logging.DEBUG)
rHandler = ConcurrentRotatingFileHandler(log_file_path, maxBytes = 5*1024*1024, backupCount=5, encoding='utf-8')
rHandler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] [%(name)s:%(lineno)d] [%(module)s:%(funcName)s] [%(levelname)s]- %(message)s')
rHandler.setFormatter(formatter)
logger.addHandler(rHandler)

def executeES(es, *eslines):
    logger.info("execute es")
    _es = []
    _es.append(es)
    es = Elasticsearch(_es)
    _params = {"refresh": "true"}
    for esline in eslines:
        logger.info("1==================")
        logger.info(esline)
        try:
            esline = esline.replace('\xa0', '')
            esline = esline.replace(' ', '')
            esline = esline.replace('@@', ' ')
            esDict = eval(esline)
            oType = esDict["type"]
            _index = esDict["index"]
            _type = esDict["doc_type"]
            _doc = esDict["doc"]
            logger.info(type(_doc))
            logger.info(_doc)
            logger.info(oType)
            #insert
            if oType.lower() == "index":
                logger.info("2==================")
                _id = esDict.get("id", "")
                if _id:
                    logger.info("no id=============")
                    ret = es.index(index=_index, doc_type=_type, body=_doc, id=_id, params=_params)
                else:
                    ret = es.index(index=_index, doc_type=_type, body=_doc, params=_params)
                logger.info(ret)
            #delete
            if oType.lower() == "delete":
                time.sleep(1.5)
                ret= es.delete_by_query(index=_index, body=_doc, params=_params)
                logger.info(ret)
            #update
            if oType.lower() == "update":
                ret = es.update_by_query(index=_index, body=_doc, params=_params)
                logger.info(ret)
        except:
            logger.info(traceback.print_exc())
            raise

def getEncodeType(filePath):
    bigdata = open(filePath,'rb')
    detector = UniversalDetector()
    for line in bigdata.readlines():
        detector.feed(line)
        if detector.done:
            break
    detector.close()
    bigdata.close()
    #print(getUnifiedEncodeType(detector.result['encoding']))
    return getUnifiedEncodeType(detector.result['encoding'])


def getUnifiedEncodeType(sType):
    sType = sType.lower()
    if sType in ['utf-8-sig', 'utf-8'] or 'utf' in sType:
        return 'utf-8'
    if sType in ['gb2312'] or 'gb' in sType:
        return 'gbk'


def executeBat(fStr):
    if not isinstance(fStr, list):
        return
    subprocess.call(fStr[0])


def executeSql(host, dbUser, dbPw, dbName, *sqlCmd):
    print("============dbConnect============")
    logger.info("============dbConnect============")
    try:
        db = pymysql.connect(host, dbUser, dbPw, dbName, autocommit=True)
        cursor = db.cursor()
        for ss in sqlCmd:
            logger.info(ss)
            if isinstance(ss, list):
                logger.info("execute sql file")
                print("execute sql file")
                _executeSqlwithFile(ss[0], cursor)
            else:
                cursor.execute(ss)
    except Exception as e:
        print(e)
        logger.error("execute sql failed", exc_info=True)
        # traceback.print_exc()
        #db.rollback()
        raise e
    finally:
        logger.info("db close!")
        print("db close!")
        db.close()


def _executeSqlwithFile(filePath, cur):
    eType = getEncodeType(filePath)
    with open(os.path.join(settings.BASE_DIR, filePath), 'r+', encoding=eType) as f:
        sql_list = f.read().split(';')[:-1]
        sql_list = [x.replace('\n', ' ') if '\n' in x else x for x in sql_list]
    for s in sql_list:
        print(s)
        logger.info(s)
        cur.execute(s)
        #db.commit()

def selectSql(host, dbUser, dbPw, dbName, sqlCmd):
    """
    sqlCmd - select name from test where ID = 'test'
    only one result
    :return: 
    None - No result
    Tuple - one result
    None - more one resutl
    """
    print("============dbConnect==selectSql============")
    logger.info("============dbConnect==selectSql==========")
    try:
        logger.info("=try+++selectSql==========")
        db = pymysql.connect(host, dbUser, dbPw, dbName)
        cursor = db.cursor()
        logger.info(sqlCmd)
        cursor.execute(sqlCmd)
        db.commit()
        data = cursor.fetchall()
        logger.info("+++++++++++++++++++++++")
        logger.info(data)
        if len(data) == 0:
            return None
        elif len(data) == 1:
            return data[0][0]
        else:
            return None
            pirnt("result is too much")

    except Exception as e:
        print(e)
        logger.error("execute sql failed", exc_info=True)
        # traceback.print_exc()
        db.rollback()
        raise e
    finally:
        logger.info("db close!")
        print("db close!")
        db.close()

def genRefid(cnt):
    ran_str = ''.join(random.sample(string.ascii_letters + string.digits, cnt))
    return ran_str


def genRanStr(cnt):
    return ''.join(random.sample(
        ['z', 'y', 'x', 'w', 'v', 'u', 't', 's', 'r', 'q', 'p', 'o', 'n', 'm', 'l', 'k', 'j', 'i', 'h', 'g', 'f', 'e',
         'd', 'c', 'b', 'a'], cnt))


def get_name_from_str(txt):
    txt = eval(txt)
    ret = []
    for dic in txt:
        ret.append(dic.get("Name"))
    return ret


def readFileFormLocal(filePath):
    return open(filePath, 'rb')


def getFileMD5(filename):
    flag = False
    if isinstance(filename, bytes):
        flag = True
        tmp_file = "tmp" + genRanStr(5)
        with open(tmp_file, 'wb') as pf:
            pf.write(filename)
        filename = tmp_file
    elif isinstance(filename, list):
        filename = filename[0]
        filename = os.path.join(settings.BASE_DIR, filename)
        if not os.path.isfile(filename):
            return ""

    myhash = hashlib.md5()
    with open(filename, 'rb') as pf:
        while True:
            b = pf.read(8096)
            if not b:
                break
            myhash.update(b)
    if flag:
        os.remove(filename)
    return myhash.hexdigest()


def archiveDicom(hostName, aeName, dcmFile):
    storeScu = os.path.join(settings.BASE_DIR, "utils", "storescu.exe")
    dcmFile = os.path.join(settings.BASE_DIR, dcmFile[0])
    storeCmd = "{} {} -aet UploadClient -aec {} 3333 {}".format(storeScu, hostName, aeName, dcmFile)
    print(storeCmd)
    logger.info(storeCmd)
    subprocess.call(storeCmd)


def getTimeStamp():
    return str(int(time.time() * 1000))


# noinspection SpellCheckingInspection
def getSignature(secret, timestamp, nonce):
    tmpArr = sorted([secret, timestamp, nonce])
    content = ''.join(tmpArr)
    hsobj = hashlib.sha256()
    hsobj.update(content.encode("utf-8"))
    return hsobj.hexdigest()
    
def length(arg):
    return len(arg)
    
def currenttime():
    '''
    : return format: 2019-12-31 11:45:3
    '''
    _ = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    logger.info(_)
    return _

def anystring(arg):
    return str(arg)

def getTokenFromStr(s):
    pa = re.compile(r"&access_token=(.*)&token_type")
    match = re.search(pa, s)
    if match:
        ret = match.group(1)
        logger.info(ret)
        return "Bearer " + ret
    else:
        logger.info("no matched str found!")
        return ""

def getStateListFromArray(dataArray):
    state_list = []
    for data in dataArray:
        json_str = json.loads(json.dumps(data))
        state_list.append(json_str['state'])
    return state_list
