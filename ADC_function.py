import requests
import hashlib
import pathlib
import random
import os.path
import json
import pathlib
import re
import time
import uuid

import requests
from lxml import etree
from zhconv import convert

import config
from urllib.parse import urljoin
from dict_gen import dict_gen


def get_data_state(data: dict) -> bool:  # 元数据获取失败检测
    if "title" not in data or "number" not in data:
        return False

    if data["title"] is None or data["title"] == "" or data["title"] == "null":
        return False

    if data["number"] is None or data["number"] == "" or data["number"] == "null":
        return False

    return True


def getXpathSingle(htmlcode, xpath):
    html = etree.fromstring(htmlcode, etree.HTMLParser())
    result1 = str(html.xpath(xpath)).strip(" ['']")
    return result1


G_USER_AGENT = r'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36'

# 网页请求核心
def get_html(url, cookies: dict = None, ua: str = None, return_type: str = None):
    verify = config.Config().cacert_file()
    configProxy = config.Config().proxy()
    errors = ""

    if ua is None:
        headers = {"User-Agent": G_USER_AGENT}  # noqa
    else:
        headers = {"User-Agent": ua}

    for i in range(configProxy.retry):
        try:
            if configProxy.enable:
                proxies = configProxy.proxies()
                result = requests.get(str(url), headers=headers, timeout=configProxy.timeout, proxies=proxies,
                                      verify=verify,
                                      cookies=cookies)
            else:
                result = requests.get(str(url), headers=headers, timeout=configProxy.timeout, cookies=cookies)

            result.encoding = "utf-8"

            if return_type == "object":
                return result
            elif return_type == "content":
                return result.content
            else:
                return result.text
        except requests.exceptions.ProxyError:
            print("[-]Proxy error! Please check your Proxy")
            return
        except Exception as e:
            print("[-]Connect retry {}/{}".format(i + 1, configProxy.retry))
            errors = str(e)
    print('[-]Connect Failed! Please check your Proxy or Network!')
    print("[-]" + errors)


def post_html(url: str, query: dict, headers: dict = None) -> requests.Response:
    configProxy = config.Config().proxy()
    errors = ""
    headers_ua = {"User-Agent": G_USER_AGENT}
    if headers is None:
        headers = headers_ua
    else:
        headers.update(headers_ua)

    for i in range(configProxy.retry):
        try:
            if configProxy.enable:
                proxies = configProxy.proxies()
                result = requests.post(url, data=query, proxies=proxies, headers=headers, timeout=configProxy.timeout)
            else:
                result = requests.post(url, data=query, headers=headers, timeout=configProxy.timeout)
            return result
        except Exception as e:
            print("[-]Connect retry {}/{}".format(i + 1, configProxy.retry))
            errors = str(e)
    print("[-]Connect Failed! Please check your Proxy or Network!")
    print("[-]" + errors)


# def get_javlib_cookie() -> [dict, str]:
#     import cloudscraper
#     switch, proxy, timeout, retry_count, proxytype = config.Config().proxy()
#     proxies = get_proxy(proxy, proxytype)
#
#     raw_cookie = {}
#     user_agent = ""
#
#     # Get __cfduid/cf_clearance and user-agent
#     for i in range(retry_count):
#         try:
#             if switch == 1 or switch == '1':
#                 raw_cookie, user_agent = cloudscraper.get_cookie_string(
#                     "http://www.javlibrary.com/",
#                     proxies=proxies
#                 )
#             else:
#                 raw_cookie, user_agent = cloudscraper.get_cookie_string(
#                     "http://www.javlibrary.com/"
#                 )
#         except requests.exceptions.ProxyError:
#             print("[-] ProxyError, retry {}/{}".format(i + 1, retry_count))
#         except cloudscraper.exceptions.CloudflareIUAMError:
#             print("[-] IUAMError, retry {}/{}".format(i + 1, retry_count))
#
#     return raw_cookie, user_agent

def is_all_chinese(str1):  # 判断是否全部为中文字符
    for _char in str1:
        if not '\u4e00' <= _char <= '\u9fa5':
            return False
    return True


def translateTag_to_sc(tag):  # srz 修改：从dict.json文件获取词典；机翻取得未收录tag的翻译, 并存入文件dict_MT.json
    translate_to_sc = config.Config().transalte_to_sc()
    if translate_to_sc:
        try:
            with open('dict.json', encoding='utf-8') as f:
                dict_gen.update(json.load(f))
        except:
            print("[!]字典文件 dict.json 不存在！新建文件...")
            with open('dict.json', 'w', encoding='utf-8') as f:
                json.dump({'原始词': '翻译结果'}, f)
        try:
            return dict_gen[tag]
        except:  # 未知tag
            x = convert(tag, 'zh-cn')
            if is_all_chinese(tag):
                return x
            else:
                print('未收录tag, Google翻译...')
                tag_cn = translate(tag)
                print(f'[*]Google翻译：{tag_cn}[{tag}]')
                with open('dict_MT.json', encoding='utf-8') as f:
                    s = json.load(f)
                    s.update({tag: tag_cn})
                with open('dict_MT.json', 'w', encoding='utf-8') as f:
                    json.dump(s, f, ensure_ascii=False)
                return tag_cn + '[' + tag + ']'
    else:
        return tag


def translate(
        src: str,
        target_language: str = "zh_cn",
        engine: str = "google-free",
        app_id: str = "",
        key: str = "",
        delay: int = 0,
):
    trans_result = ""
    if engine == "google-free":
        url = (
                "https://translate.google.cn/translate_a/single?client=gtx&dt=t&dj=1&ie=UTF-8&sl=auto&tl="
                + target_language
                + "&q="
                + src
        )
        result = get_html(url=url, return_type="object")

        translate_list = [i["trans"] for i in result.json()["sentences"]]
        trans_result = trans_result.join(translate_list)
    # elif engine == "baidu":
    #     url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    #     salt = random.randint(1, 1435660288)
    #     sign = app_id + src + str(salt) + key
    #     sign = hashlib.md5(sign.encode()).hexdigest()
    #     url += (
    #         "?appid="
    #         + app_id
    #         + "&q="
    #         + src
    #         + "&from=auto&to="
    #         + target_language
    #         + "&salt="
    #         + str(salt)
    #         + "&sign="
    #         + sign
    #     )
    #     result = get_html(url=url, return_type="object")
    #
    #     translate_list = [i["dst"] for i in result.json()["trans_result"]]
    #     trans_result = trans_result.join(translate_list)
    elif engine == "azure":
        url = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to=" + target_language
        headers = {
            'Ocp-Apim-Subscription-Key': key,
            'Ocp-Apim-Subscription-Region': "global",
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        body = json.dumps([{'text': src}])
        result = post_html(url=url, query=body, headers=headers)
        translate_list = [i["text"] for i in result.json()[0]["translations"]]
        trans_result = trans_result.join(translate_list)

    else:
        raise ValueError("Non-existent translation engine")

    time.sleep(delay)
    return trans_result


# ========================================================================是否为无码
def is_uncensored(number):
    if re.match('^\d{4,}', number) or re.match('n\d{4}', number) or 'HEYZO' in number.upper():
        return True
    configs = config.Config().get_uncensored()
    prefix_list = str(configs).split(',')
    for pre in prefix_list:
        if pre.upper() in number.upper():
            return True
    return False


# 从浏览器中导出网站登录验证信息的cookies，能够以会员方式打开游客无法访问到的页面
# 示例: FC2-755670 url https://javdb9.com/v/vO8Mn
# json 文件格式
# 文件名: 站点名.json，示例 javdb9.json
# 内容(文件编码:UTF-8)：
'''
{
    "over18":"1",
    "redirect_to":"%2Fv%2FvO8Mn",
    "remember_me_token":"cbJdeaFpbHMiOnsibWVzc2FnZSI6IklrNVJjbTAzZFVSRVlVaEtPWEpUVFhOVU0yNXhJZz09IiwiZXhwIjoiMjAyMS0wNS0xNVQxMzoyODoxNy4wMDBaIiwicHVyIjoiY29va2llLnJlbWVtYmVyX21lX3Rva2VuIn19--a7131611e844cf75f9db4cd411b635889bff3fe3",
    "_jdb_session":"asddefqfwfwwrfdsdaAmqKj1%2FvOrDQP4b7h%2BvGp7brvIShi2Y%2FHBUr%2BklApk06TfhBOK3g5gRImZzoi49GINH%2FK49o3W%2FX64ugBiUAcudN9b27Mg6Ohu%2Bx9Z7A4bbqmqCt7XR%2Bao8PRuOjMcdDG5czoYHJCPIPZQFU28Gd7Awc2jc5FM5CoIgSRyaYDy9ulTO7DlavxoNL%2F6OFEL%2FyaA6XUYTB2Gs1kpPiUDqwi854mo5%2FrNxMhTeBK%2BjXciazMtN5KlE5JIOfiWAjNrnx7SV3Hj%2FqPNxRxXFQyEwHr5TZa0Vk1%2FjbwWQ0wcIFfh%2FMLwwqKydAh%2FLndc%2Bmdv3e%2FJ%2BiL2--xhqYnMyVRlxJajdN--u7nl0M7Oe7tZtPd4kIaEbg%3D%3D",
    "locale":"zh",
    "__cfduid":"dee27116d98c432a5cabc1fe0e7c2f3c91620479752",
    "theme":"auto"
}
'''


# 从网站登录后，通过浏览器插件(CookieBro或EdittThisCookie)或者直接在地址栏网站链接信息处都可以复制或者导出cookie内容，
# 并填写到以上json文件的相应字段中
def load_cookies(filename):
    try:
        return json.load(open(filename))
    except:
        return None


# 文件修改时间距此时的天数
def file_modification_days(filename) -> int:
    mfile = pathlib.Path(filename)
    if not mfile.exists():
        return 9999
    mtime = int(mfile.stat().st_mtime)
    now = int(time.time())
    days = int((now - mtime) / (24 * 60 * 60))
    if days < 0:
        return 9999
    return days

# 检查文件是否是链接
def is_link(filename: str):
    if os.path.islink(filename):
        return True # symlink
    elif os.stat(filename).st_nlink > 1:
        return True # hard link Linux MAC OSX Windows NTFS
    return False

# URL相对路径转绝对路径
def abs_url(base_url: str, href: str) -> str:
    if href.startswith('http'):
        return href
    return urljoin(base_url, href)
