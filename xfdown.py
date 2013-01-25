#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import subprocess
import random
import json, os, sys, re, hashlib

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

        if cookieload:
            self.main()
        else:
            self.__Login(True)

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
            try:
                subprocess.Popen(['xdg-open', self.__verifyimg])
            except:
                _print("请打开%s查看验证码" % self.__verifyimg)
            print("请输入验证码：")
            vf = raw_input("vf # ").strip()
            verify[1] = vf

        return verify


    def __request_login(self):
        urlv = "http://ptlogin2.qq.com/login?u=%s&p=%s&verifycode=%s" % (self.__qq, self.passwd, self.__verifycode[1]) + "&aid=567008010&u1=http%3A%2F%2Flixian.qq.com%2Fmain.html&h=1&ptredirect=1&ptlang=2052&from_ui=1&dumy=&fp=loginerroralert&action=2-10-&mibao_css=&t=1&g=1"
        str = self.__request(urlv)
        if str.find(_('登录成功')) != -1:
            self.__getlogin()
            self.main()
        elif str.find(_('验证码不正确')) != -1:
            self.__getverifycode()
            self.__Login(False, True)
        elif str.find(_('不正确')) != -1:
            _print('你输入的帐号或者密码不正确，请重新输入。')
            self.__Login(True)
        else:
            #print('登录失败')
            _print(str)
            self.__Login(True)

    def main(self):
        self.__getlist()

    def getfilename_url(self, url):
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

    def __getlist(self):
        """
        得到任务名与hash值
        """
        res = self.__request(LIST_URL)
        res = json.JSONDecoder().decode(res)
        if res["msg"] == _('未登录!'):
            res = json.JSONDecoder().decode(self.__getlogin())
            if res["msg"] == _('未登录!'):
                self.__Login()

            else:
                self.main()
        elif not res["data"]:
            print(_('无离线任务!'))
            self.main()
        else:
            self.filename = []
            self.filehash = []
            self.filemid = []
            res['data'].sort(key=lambda x: x["file_name"])
            _print("\n===================离线任务列表====================")
            _print("序号\t大小\t进度\t文件名")
            for num in range(len(res['data'])):
                index = res['data'][num]
                self.filename.append(index['file_name'].encode("u8"))
                self.filehash.append(index['code'])
                size = index['file_size']
                self.filemid.append(index['mid'])
                if size == 0:
                    percent = "-0"
                else:
                    percent = str(index['comp_size'] / size * 100).split(".")[0]

                dw = ["B", "K", "M", "G"]
                for i in range(4):
                    _dw = dw[i]
                    if size >= 1024:
                        size = size / 1024
                    else:
                        break
                size = "%.1f%s" % (size, _dw)
                out = "%d\t%s\t%s%%\t%s" % (num + 1, size, percent, _(self.filename[num]))
                if num % 2 == 0 and os.name == 'posix':
                    out = "\033[m\033[40m%s\033[m" % out

                _print(out)
            _print("=======================END=========================\n")

    def get_download_info(self, filename, filehash):
        data = {'hash': filehash, 'filename': filename, 'browser': 'other'}
        result = self.__request(DOWNLOAD_INFO_URL, data)
        url = re.search(r'\"com_url\":\"(.+?)\"\,\"', result).group(1)
        cookie = re.search(r'\"com_cookie":\"(.+?)\"\,\"', result).group(1)
        return url, cookie

    def get_aria2c_cmd_line(self, filename, filehash):
        url, cookie = self.get_download_info(filename, filehash)
        return "aria2c -c -s10 -x10 --header 'Cookie:ptisp=edu; FTN5K=%s' '%s'" % (cookie, url)

    def delete_task(self, task_id):
        return self.__request(DELETE_URL, {'mids': task_id})

    def add_task(self, url):
        filename = self.getfilename_url(url)
        data = {"down_link": url,
                "filename": filename,
                "filesize": 0,
                }
        return self.__request(ADD_URL, data)

    def __Login(self, needinput=False, verify=False):
        """
        登录
        """
        self.__verifycode = self.__getverifycode()
        self.passwd = self.__preprocess(
            verifycode=self.__verifycode,
            hashpasswd=self.hashpasswd
        )
        self.__request_login()

def main():
    f = open('credential', 'rb')
    xf = XF(f.next().strip(), f.next().strip())
    xf.start()

if __name__ == '__main__':
    main()
