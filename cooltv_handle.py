from collections import OrderedDict
import requests, json, re
from flask import Response
from support import d, default_headers, logger
from tool import ToolUtil

from .setup import P


class Cooltv:

    headers = {'referer':'https://reystream.tv/'}
    _stream_url = 'https://scdn.reystream.tv/fadostream'

    @classmethod
    def ch_list(cls):
        ret = []
        data = requests.get('https://reystream.tv/tv/cooltv/index.php').text
        tmps = data.split('not_onair_channels.png')[0].split("<tr class='cate_")
        regex  = [re.compile(r'<td>(?P<leauge>[\w\s]+)</td>', re.MULTILINE), re.compile(r"load_video\((?P<data>\d+,'1',.*?)\);", re.MULTILINE)]
        for tmp in tmps[1:]:
            if tmp.find('문자중계') != -1: continue
            if tmp.find('방송전') != -1: continue
            item = {'cate' : tmp.split("'")[0], 'leauge' : regex[0].search(tmp).group('leauge')}
            item['id'], d, item['name'], t = regex[1].search(tmp).group('data').split(',')
            item['name'] = re.sub('\(\d+\)', '', item['name'].replace("'", '').replace('	', ' ')).strip()
            if item['cate'] == 'tv' and item['leauge'] == 'KM': continue
            ret.append(item)
        return ret
        

    @classmethod
    def get_m3u8(cls, ch_id):
        url = f'{cls._stream_url}{ch_id}/chunklist.m3u8'
        res = requests.get(url, headers=cls.headers)
        if res.status_code != 200:
            url = f'https://lcdn.reystream.tv/fadostream{ch_id}/chunklist.m3u8'
            res = requests.get(url, headers=cls.headers)
            if res.status_code == 200:
                cls._stream_url = 'https://lcdn.reystream.tv/fadostream'
        new_data = []
        for line in res.text.splitlines():
            line = line.strip()
            if line.endswith('.ts'):
                new = ToolUtil.make_apikey_url(f"/{P.package_name}/api/segment.ts?ch_id={ch_id}&ts={line}")
                new_data.append(new)
            else:
                new_data.append(line)
        data = '\n'.join(new_data)
        return 'text', data


    @classmethod
    def segment(cls, req):
        url = f"{cls._stream_url}{req.args.get('ch_id')}/{req.args.get('ts')}"
        res = requests.get(url, headers=cls.headers, stream=True, verify=False)
        ret = Response(res.iter_content(chunk_size=1048576), res.status_code, content_type='video/MP2T', direct_passthrough=True)
        return ret
    

    @classmethod
    def make_m3u(cls):
        M3U_FORMAT = '#EXTINF:-1 tvg-id=\"{id}\" tvg-name=\"{title}\" tvg-logo=\"{logo}\" group-title=\"{group}\" tvg-chno=\"{ch_no}\" tvh-chnum=\"{ch_no}\",{title}\n{url}\n' 
        m3u = '#EXTM3U\n'
        for idx, item in enumerate(cls.ch_list()):
            m3u += M3U_FORMAT.format(
                id=item['id'],
                title=item['name'],
                group="sports",
                ch_no=str(idx+1),
                url=ToolUtil.make_apikey_url(f"/{P.package_name}/api/url.m3u8?ch_id={item['id']}"),
                logo= f"https://reystream.tv/tv/cooltv/assets/icons/tv/{item['cate']}.png",
            )
        return m3u
    