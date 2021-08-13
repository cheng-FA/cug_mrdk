#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# python3.9 macOS11.4
import os
import re
import time
import codecs
import datetime
import json
import base64
import requests
from PIL import Image, ImageSequence
import pytesseract
from scipy import stats
from selenium import webdriver
from urllib import parse
# configparser 兼容 2.x 与 3.x
try:
    import configparser as configparser
except Exception:
    import ConfigParser as configparser

# 获取py 文件所在路径并设置成工作路径
os.chdir(os.path.dirname(__file__))

content = open('./parameters.cfg').read()  
# Window下用记事本打开配置文件并修改保存后，编码为UNICODE或UTF-8的文件的文件头会被相应地
# 加上\xff\xfe（\xff\xfe）或\xef\xbb\xbf，然后再传递给ConfigParser解析的时候会出错  
# ，因此解析之前，先替换掉
content = re.sub(r"\xfe\xff", "", content)  
content = re.sub(r"\xff\xfe", "", content)
content = re.sub(r"\xef\xbb\xbf", "", content)
open('./parameters.cfg', 'w').write(content)

# 获取配置文件参数
config_raw = configparser.RawConfigParser()
config_raw.read('./parameters.cfg', encoding="utf-8")


# [Path]
# tesseract.exe安装路径
if os.name == 'nt':  # windows系统需要指定
    pytesseract.pytesseract.tesseract_cmd = config_raw.get('Path', 'Tesseract')
logPath = config_raw.get('Path', 'LogPath')  # 日志文件路径

# [Parameter]
userName = config_raw.get('Parameter', 'UserName')  # 用户名
passWord = config_raw.get('Parameter', 'PassWord')  # 密码


# 输入关键词
# text: Unicode, 要输入的文本
# element_id: 输入框网页元素id
def input_by_id(driver, text, element_id):
    input_el = driver.find_element_by_id(element_id)
    input_el.clear()
    input_el.send_keys(text)


# 将gif解析为图片
def parseGIF(gifPath):
    # 读取GIF
    im = Image.open(gifPath)
    # GIF图片流的迭代器
    iter = ImageSequence.Iterator(im)
    # 获取文件名
    file_name = os.path.basename(gifPath).split(".")[0]
    index = 1
    # 判断目录是否存在
    pic_dirct = "{0}".format(file_name)
    # print(pic_dirct)
    mkdirlambda = lambda x: os.makedirs(
        x) if not os.path.exists(x) else True  # 目录是否存在,不存在则创建
    mkdirlambda(pic_dirct)
    # 遍历图片流的每一帧
    for frame in iter:
        # print("image %d: mode %s, size %s" % (index, frame.mode, frame.size))
        frame.save("%s/frame%d.png" % (file_name, index))
        index += 1


# 写入文档
def writeFile(path, textList, writeType):
    with codecs.open(path, writeType, 'utf-8') as f:
        for i in range(len(textList)):
            f.write(textList[i] + "\r\n")


# 写入日志文件
def writeLogFile(log):
    currentDate = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logStr = "[%s]%s" % (currentDate, log)
    writeFile(path=logPath, textList=[logStr], writeType='a')  # 写入日志文件文件


writeLogFile(u'【程序运行】')
try:
    driver = webdriver.Chrome(executable_path='./bin/chromedriver')
    # driver = webdriver.Safari()
    # 访问每日打卡网页
    driver.get('http://yqapp.cug.edu.cn/xsfw/sys/swmxsyqxxsjapp/'
               '*default/index.do#/addmrbpa/mrdk')
    # 注入一段脚本令网页所有img都转换为base64格式
    js = """
        _fetch = function(i,src){
          return fetch(src).then(function(response) {
            if(!response.ok) throw new Error("No image in the response");
            var headers = response.headers;
            var ct = headers.get('Content-Type');
            var contentType = 'image/png';
            if(ct !== null){
              contentType = ct.split(';')[0];
            }
            
            return response.blob().then(function(blob){
              return {
                'blob': blob,
                'mime': contentType,
                'i':i,
              };
            });
          });
        };
        
        _read = function(response){
          return new Promise(function(resolve, reject){
            var blob = new Blob([response.blob], {type : response.mime});
            var reader = new FileReader();
            reader.onload = function(e){
              resolve({'data':e.target.result, 'i':response.i});
            };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
          });
        };
        
        _replace = function(){
            for (var i = 0, len = q.length; i < len; i++) {
                imgs[q[i].item].src = q[i].data;
            }
        }
        
        var q = [];
        var imgs = document.querySelectorAll('img');
        for (var i = 0, len = imgs.length; i < len; i++) {
                _fetch(i,imgs[i].src).then(_read).then(function(data){
            q.push({
              'data': data.data,
              'item': data.i,
            });
          });
            }
        setTimeout(_replace, 1000 );
        """
    driver.execute_script(js)
    time.sleep(2)
    input_by_id(driver, userName, 'un')  # 填充用户名
    input_by_id(driver, passWord, 'pd')  # 填充密码
    # 获取图片base64字符串
    imgSrc = driver.find_element_by_id('codeImage').get_attribute("src")
    with open("source.gif", 'wb') as f:  # 保存gif图片
        f.write(base64.b64decode(imgSrc.split(',')[1]))
    # OCR验证码
    parseGIF('source.gif')  # 获取gif的每一帧
    imgPath = u'./source/'
    numList = [[], [], [], []]  # 存储识别出的数字
    for imgName in os.listdir(imgPath):  # 遍历4帧图片
        imgSrc = os.path.join(imgPath, imgName)
        img = Image.open(imgSrc)  # img.size 90,58
        imgry = img.convert('L')  # 图片灰度化
        # 增加数字和背景对比度
        threshold = 250
        table = []
        for i in range(256):
            if i > threshold:
                table.append(1)  
            else:
                table.append(0)
        blackImg = imgry.point(table, '1')
        # 逐像素去除背景和细化字体
        pim = blackImg.load()
        arr = [[0] * blackImg.size[1] for _ in range(blackImg.size[0])]
        for i in range(1, blackImg.size[0]-1):
            for j in range(1, blackImg.size[1]-1):
                if pim[i, j+1] or pim[i, j-1] or pim[i+1, j] or pim[i-1, j]:
                    arr[i][j] = 1
        for i in range(1, blackImg.size[0]-1):
            for j in range(1, blackImg.size[1]-1):
                if arr[i][j]:
                    pim[i, j] = 1
        # 分割数字字符
        croppedList = [(0, 16, 20, 42),  # 第一个数字
                       (18, 16, 40, 42),  # 第二个数字
                       (38, 16, 60, 42),  # 第三个数字
                       (60, 16, 85, 42)]  # 第四个数字
        numIndex = 0
        for cropSize in croppedList:
            cropNumImg = blackImg.crop(cropSize)  # 分割数字
            # 创建一个新的图片对象
            currentNumImg = Image.new('RGB', (40, 40), (255, 255, 255))
            currentNumImg.paste(cropNumImg, (8, 8))  # 扩充边缘
            # currentNumImg.save("./test/%s%s.png" % (imgName, numIndex))
            text = pytesseract.image_to_string(currentNumImg, lang='eng',
                config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')
            if re.search(r'\d', text):  # 判断是否有数字
                numList[numIndex].append(re.findall(r"\d+", text)[0])
            numIndex = numIndex + 1
    captchaText = ''
    for numIndex in range(4):
        if numList[numIndex] != []:
            captchaText = captchaText + stats.mode(numList[numIndex])[0][0]
    # print(captchaText)
    writeLogFile(u'【OCR验证码成功】%s' % captchaText)
    input_by_id(driver, captchaText, 'code')  # 填充验证码
    driver.find_element_by_id('index_login_btn').click()  # 点击登录
    time.sleep(2)
    cookieStr = ''  # 获取cookies
    for cookie in driver.get_cookies():
        cookieStr = cookieStr + cookie['name'] + '=' + cookie['value'] + '; '
    # print(cookieStr)
    # 获取个人信息data
    url = ("http://yqapp.cug.edu.cn/xsfw/sys/swmxsyqxxsjapp/"
           "modules/mrbpa/getStuXx.do")
    payload = 'data=%7B%22SJD%22%3A%221%22%7D'
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Cookie': cookieStr
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    data = json.loads(response.text)['data']
    # 修改填报信息
    data["BRJKZT_DISPLAY"] = "正常"  # 本人健康状态
    data["BRJKZT"] = "1"
    data["TW_DISPLAY"] = "否"  # 体温是否37.3
    data["TW"] = "0"
    data["JTCYJKZK_DISPLAY"] = "正常"  # 家庭成员健康情况
    data["JTCYJKZK"] = "1"
    data["XLZK_DISPLAY"] = "无"  # 心理状况
    data["XLZK"] = "www"
    data["QTQK"] = ""  # 近14天情况

    data["TBSJ"] = time.strftime("%Y-%m-%d", time.localtime())  # 填报时间
    # 当前时间
    now_localtime = time.strftime("%H:%M:%S", time.localtime())
    # 根据当前时间判断SJD 上午：1 下午：2 晚上：3
    data["SJD"] = "1"
    if "05:00:00" < now_localtime <= "11:30:00":
        data["SJD"] = "1"
    elif "11:30:00" < now_localtime <= "17:30:00":
        data["SJD"] = "2"
    elif "17:30:00" < now_localtime <= "23:30:00":
        data["SJD"] = "3"
    if 'WID' in data:
        data.pop('WID')  # 删除WID键值对
    payload = parse.urlencode({"data": data})
    url = ("http://yqapp.cug.edu.cn/xsfw/sys/swmxsyqxxsjapp/"
           "modules/mrbpa/saveMrdk.do")
    response = requests.request("POST", url, headers=headers, data=payload)
    res = json.loads(response.text)
    if u'成功' in res['msg']:
        writeLogFile(u'【提交成功】\n')
    else:
        writeLogFile(u'【提交失败】%s\n' % res)
    driver.refresh()  # 刷新页面
except Exception as e:
    writeLogFile(u'【出错】 %s\n' % e)
    raise e
