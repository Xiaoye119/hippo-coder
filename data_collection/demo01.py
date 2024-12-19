"""
encoding: utf-8
    @Author: Jacob
    @Date  : 2024/06/28
    @Desc  : 抓取播放列表
"""
import csv
import json
import time
import datetime
import requests
from lxml import etree


proxy = {
    "http": "http://127.0.0.1:10792",
    "https": "http://127.0.0.1:10792",
}


def save_to_csv(data, filename='result.csv'):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Repository URL'])
        for item in data:
            writer.writerow([item])


def save_to_json(data):
    current_time = datetime.datetime.now().strftime("%m_%d%H%M%S")
    filename = f'result_{current_time}.json'

    with open(filename, mode='w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)



def req(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Cookie': "_octo=GH1.1.1862059235.1730266436; _device_id=757ed3a403dfc638738332f2c6e9718e; saved_user_sessions=51373282%3AHKn5aeZLGEYi9EUhgAP2v3gB--pJK3ZAVB1XYKtRixPZRIRB; user_session=HKn5aeZLGEYi9EUhgAP2v3gB--pJK3ZAVB1XYKtRixPZRIRB; __Host-user_session_same_site=HKn5aeZLGEYi9EUhgAP2v3gB--pJK3ZAVB1XYKtRixPZRIRB; logged_in=yes; dotcom_user=Jacob-Yangman; color_mode=%7B%22color_mode%22%3A%22auto%22%2C%22light_theme%22%3A%7B%22name%22%3A%22light%22%2C%22color_mode%22%3A%22light%22%7D%2C%22dark_theme%22%3A%7B%22name%22%3A%22dark%22%2C%22color_mode%22%3A%22dark%22%7D%7D; cpu_bucket=xlg; preferred_color_mode=light; tz=Asia%2FShanghai; _gh_sess=scWuNN%2BihIFjbrcHiP67pDMTDIumrbRliSXvURSQX23ZWRbC1Ts4J1IyKUk3x57FRkR4XaCtZnnglneiJ04%2FY4XkccaU%2Bt%2FKytUXiCZBnJjZc%2FNuz9fAgoqYp6WcDxedyT5OolTLx%2BTTv%2B9VYMHTSzAZlvp7xAz7woMOIRVAss8k6e5K%2Fp4KZGdjczCn57JbwdAmCjBdL60zRKf%2BIjw522z2Meu4ehoeMRdgyTFlNNkBi%2Bl0uH%2FV169blIsRcranH8lHfA6rgYarVB1QMNRAtQ9IdTVH2EbehtBGTe62IcOLKCObw3%2B3vhloFGNvcFFCURZ5LrpXNCGqTn6ei7fOyYRTIun03OL2N7WxmMZnMwF41Dl5ZEk5bi6EF8tUMA6z7WpHy0M30zEWrHQ2PMuva2yVlGcn25uUvDqEfWHHK%2Bane30phpvKHBxgRTJn0oQMBq%2BwP7BYUsTCfbbU--vGT6%2FlipxfMSv6u8--LFbk0eHcf4yJA%2FDuN%2F9eTQ%3D%3D",
        # 'Referer': 'https://www.bilibili.com/'
    }

    res = requests.get(url, headers=headers, proxies=proxy)

    return res.text


def parse(html):
    global count
    selector = etree.HTML(html)

    repoLst = selector.xpath('/html/body/div[1]/div[5]/main/react-app/div/div/div[1]/div/div/div[2]/div[2]/div/div[1]/div[4]/div/div/div')

    result = list()


    for repoNode in repoLst:
        try:

            # Description
            repoDesc = repoNode.xpath('div/div[1]/div/span/text()')[0].strip()
            # Stars
            repoStar = repoNode.xpath('div/div[1]/ul/li[2]/a/span/text()')[0].strip()
            # Clone src
            repoSrc = repoNode.xpath('div/div[1]/h3/div/div[2]/a/@href')
            if repoSrc:
                repoSrc = repoSrc[0].strip()
                repoSrc = "https://github.com" + repoSrc + "/archive/refs/heads/master.zip"
                print(f"Parsing >> {repoSrc}")
            # Updated time
            repoUpdated = repoNode.xpath('div/div[1]/ul/li[3]/span/div/span/text()')[0].strip()
            ...
        except:
            continue

        count += 1

        result.append({"info": repoDesc,
                       "src": repoSrc,
                       "stars": repoStar,
                       "updated": repoUpdated})
        time.sleep(0.08)

    return result






if __name__ == '__main__':
    count = 0
    pageNum = 2
    allResult = list()
    for i in range(1, pageNum + 1):
        print(f"Parsing >> Page {i}")
        url = f"https://github.com/search?q=language%3AVerilog+&type=repositories&p={i}"
        html = req(url)
        result = parse(html)
        allResult.extend(result)
        time.sleep(0.3)
    print(f"Total >> {count}")
    save_to_json(allResult)
