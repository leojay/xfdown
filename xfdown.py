#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import random
import json, os, sys, re, hashlib
import subprocess
from os.path import dirname, exists

HANDLER = 'http://lixian.qq.com/handler/lixian/'

ADD_URL = HANDLER + 'add_to_lixian.php'
DELETE_URL = HANDLER + 'del_lixian_task.php'
DOWNLOAD_INFO_URL = HANDLER + 'get_http_url.php'
LOGIN_URL = HANDLER + 'do_lixian_login.php'
LIST_URL = HANDLER + 'get_lixian_list.php'
CHECK_TOKEN_URL = HANDLER + 'check_tc.php'

try:
    import urllib as parse
    import urllib2 as request
    import cookielib as cookiejar
except:
    from urllib import parse, request
    from http import cookiejar

    raw_input = input

def _(string):
    try:
        return string.decode("u8")
    except:
        return string


def _print(str):
    print(_(str)).encode("utf-8", "ignore")


def get_module_path():
    if hasattr(sys, "frozen"):
        module_path = os.path.dirname(sys.executable)
    else:
        module_path = os.path.dirname(os.path.abspath(__file__))
    return module_path

module_path = get_module_path()

def hexchar2bin(hex):
    arry = bytearray()
    for i in range(0, len(hex), 2):
        arry.append(int(hex[i:i + 2], 16))
    return arry


def get_gtk(strs):
    hash = 5381
    for i in strs:
        hash += (hash << 5) + ord(i)
    return hash & 0x7fffffff


class TaskInfo(object):
    def __init__(self, task_id, hash, filename, file_size, completed_size, status):
        self.id = task_id
        self.hash = hash
        self.filename = filename
        self.file_size = file_size
        self.completed_size = completed_size
        self.status = status

    def is_completed(self):
        return self.file_size > 0 and self.file_size == self.completed_size

    def get_native_name(self):
        return self.filename.replace('\\', os.sep)

class XF:
    """
     Login QQ
    """

    __cookiepath = '%s/cookie' % module_path
    __verifyimg = '%s/verify.jpg' % module_path
    __RE = re.compile("(\d+) *([^\d ]+)?")

    def __init__(self, qq, password_hash):
        self.__qq = qq
        self.hashpasswd = password_hash

    def __preprocess(self, password=None, verifycode=None, hashpasswd=None):
        if not hashpasswd:
            self.hashpasswd = self.__md5(password)

        I = hexchar2bin(self.hashpasswd)
        if sys.version_info >= (3, 0):
            H = self.__md5(I + bytes(verifycode[2], encoding="ISO-8859-1"))
        else:
            H = self.__md5(I + verifycode[2])
        G = self.__md5(H + verifycode[1].upper())

        return G

    def __md5(self, item):
        if sys.version_info >= (3, 0):
            try:
                item = item.encode("u8")
            except:
                pass
        return hashlib.md5(item).hexdigest().upper()

    def start(self):
        self.cookieJar = cookiejar.LWPCookieJar(self.__cookiepath)

        cookieload = False

        if os.path.isfile(self.__cookiepath):
            try:
                self.cookieJar.load(ignore_discard=True, ignore_expires=True)
                cookieload = True
            except:
                pass

        opener = request.build_opener(request.HTTPCookieProcessor(self.cookieJar))
        opener.addheaders = [('User-Agent', 'Mozilla/5.0'), ("Referer", "http://lixian.qq.com/main.html")]
        request.install_opener(opener)

        if not cookieload:
            self.__Login()

    def __request(self, url, data=None):
        """
            请求url
        """
        if data:
            data = parse.urlencode(data).encode('utf-8')
            fp = request.urlopen(url, data)
        else:
            fp = request.urlopen(url)
        result = fp.read()
        try:
            result = result.decode('utf-8')
        except UnicodeDecodeError:
            pass

        self.cookieJar.save(ignore_discard=True, ignore_expires=True)

        fp.close()
        return result

    def __getverifycode(self):
        urlv = 'http://check.ptlogin2.qq.com/check?uin=%s&appid=567008010&r=%s' % (self.__qq, random.Random().random())

        str = self.__request(urlv)
        verify = eval(str.split("(")[1].split(")")[0])
        verify = list(verify)
        if verify[0] == '1':
            imgurl = "http://captcha.qq.com/getimage?aid=567008010&r=%s&uin=%s" % (random.Random().random(), self.__qq)
            with open(self.__verifyimg, "wb") as f:
                f.write(request.urlopen(imgurl).read())
            vf = raw_input("vf # ").strip()
            verify[1] = vf

        return verify


    def __get_default_filename(self, url):
        url = url.strip()
        filename = ""
        if url.startswith("ed2k"):
            arr = url.split("|")
            if len(arr) >= 4:
                filename = parse.unquote(arr[2])
        else:
            filename = url.split("/")[-1]
        return filename.split("?")[0]

    def __getlogin(self):
        self.__request(CHECK_TOKEN_URL)
        skey = re.findall('skey="([^"]+)"', open(self.__cookiepath).read())[0]
        return self.__request(LOGIN_URL, {"g_tk": get_gtk(skey)})

    def list_tasks(self):
        """
        @rtype: list of TaskInfo
        """
        res = self.__request(LIST_URL)
        res = json.JSONDecoder().decode(res)
        if res["msg"] == _('未登录!'):
            res = json.JSONDecoder().decode(self.__getlogin())
            if res["msg"] == _('未登录!'):
                if not self.__Login():
                    return None
            return self.list_tasks()

        if not res["data"]:
            return []

        res['data'].sort(key=lambda x: x["file_name"])
        result = []
        for entry in res['data']:
            size = int(entry['file_size'])
            completed = int(entry['comp_size'])
            status = int(entry['dl_status'])
            filename = entry['file_name'].encode("u8")
            result.append(TaskInfo(entry['mid'], entry['code'], filename, size, completed, status))
        return result

    def get_download_info(self, task):
        """
        @type task: TaskInfo
        """
        data = {'hash': task.hash, 'filename': task.filename, 'browser': 'other'}
        result = self.__request(DOWNLOAD_INFO_URL, data)
        url = re.search(r'\"com_url\":\"(.+?)\"\,\"', result).group(1)
        cookie = re.search(r'\"com_cookie":\"(.+?)\"\,\"', result).group(1)
        return url, cookie

    def get_axel_cmd_line(self, task):
        """
        @type task: TaskInfo
        """
        url, cookie = self.get_download_info(task)
        name = task.get_native_name()
        header = 'Cookie:ptisp=edu; FTN5K=%s' % cookie
        return ['axel', '-n', '20', '-q', '-o', name, '-H', header, url]

    def delete_task(self, task):
        """
        @type task: TaskInfo
        """
        return self.__request(DELETE_URL, {'mids': task.id})

    def add_task(self, url):
        filename = self.__get_default_filename(url)
        data = {"down_link": url,
                "filename": filename,
                "filesize": 0,
                }
        return self.__request(ADD_URL, data)

    def __Login(self):
        verifycode = self.__getverifycode()
        passwd = self.__preprocess(verifycode=verifycode, hashpasswd=self.hashpasswd)
        urlv = "http://ptlogin2.qq.com/login?u=%s&p=%s&verifycode=%s" % (self.__qq, passwd, verifycode[1]) + "&aid=567008010&u1=http%3A%2F%2Flixian.qq.com%2Fmain.html&h=1&ptredirect=1&ptlang=2052&from_ui=1&dumy=&fp=loginerroralert&action=2-10-&mibao_css=&t=1&g=1"
        if _('登录成功') in self.__request(urlv):
            self.__getlogin()
            return True
        return False


import threading
N = 5
semaphore = threading.Semaphore(N)
xf_lock = threading.Lock()
xf = None

def download_task(cmd, task):
    try:
        if exists('stop'):
            return
        if subprocess.call(cmd) == 0:
            with xf_lock:
                xf.delete_task(task)
    finally:
        semaphore.release()

def main():
    global xf
    f = open('credential', 'rb')
    xf = XF(f.next().strip(), f.next().strip())
    xf.start()

    for task in xf.list_tasks():
        if task.is_completed():
            cmd_line = xf.get_axel_cmd_line(task)

            name = task.get_native_name()
            dir = dirname(name)
            if dir and not exists(dir):
                os.makedirs(dir)

            semaphore.acquire()
            print 'Downloading:', name
            threading.Thread(target=download_task, args=(cmd_line, task)).start()

    for i in range(N):
        semaphore.acquire()


if __name__ == '__main__':
    main()
