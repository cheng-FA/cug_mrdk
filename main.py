import requests
# import json
from urllib import parse
import datetime


url = "http://yqapp.cug.edu.cn/xsfw/sys/swmxsyqxxsjapp/modules/mrbpa/saveMrdk.do"

data = {"data": {"your_data"}}  # 替换为你的填报信息

headers = {
  'Cookie': ('your_cookie'),  # 替换为你的Cookie
  'Content-Type': 'application/x-www-form-urlencoded'
}

begin = datetime.date(2021, 8, 10)  # 填报开始日期
end = datetime.date(2021, 8, 28)  # 填报结束日期
for i in range((end - begin).days + 1):  # 日期循环
    date = begin + datetime.timedelta(days=i)
    print(str(date))
    for j in range(1, 4):  # 每日三次循环
        print(j)
        data['data']['TBSJ'] = str(date)
        data['data']['SJD'] = str(j)
        # print(data)
        # 提交填报请求
        response = requests.request("POST", url, headers=headers, data=parse.urlencode(data))
        print(response.text)
