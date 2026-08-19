import urllib.request
import urllib.parse
import http.cookiejar
import json
import ssl
import re
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class FlexClipClient:
    def __init__(self):
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPSHandler(context=self.ctx)
        )
        self.csrf_token: Optional[str] = None
        self.last_init_time: float = 0
        self.session_duration: float = 1800  # 30 minutes

    def _ensure_session(self):
        now = time.time()
        if not self.csrf_token or (now - self.last_init_time > self.session_duration):
            self._init_session()

    def _init_session(self):
        try:
            logger.info("Initializing new FlexClip session...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            req = urllib.request.Request('https://www.flexclip.com/editor/app?ratio=landscape', headers=headers)
            with self.opener.open(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                csrf_match = re.search(r'window\.csrf_token\s*=\s*[\'"]([^\'"]+)[\'"]', html)
                if csrf_match:
                    self.csrf_token = csrf_match.group(1)
                    self.last_init_time = time.time()
                    logger.info(f"FlexClip session initialized. CSRF: {self.csrf_token}")
                else:
                    self.csrf_token = "guest_csrf_" + str(int(time.time()))
        except Exception as e:
            logger.error(f"Error initializing FlexClip session: {e}")
            if not self.csrf_token:
                self.csrf_token = "default_csrf"

    def search_videos(self, keywords: str, page: int = 1, num_results: int = 24, sort: str = 'most_relevant') -> Dict[str, Any]:
        self._ensure_session()
        post_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://www.flexclip.com',
            'Referer': 'https://www.flexclip.com/editor/app?ratio=landscape',
        }

        post_data = {
            'option': 'com_fj_stock',
            'task': 'stock.searchVideo',
            'keywords': keywords,
            'page': str(page),
            'numResults': str(num_results),
            'sort': sort,
            'minDuration': '1',
            'maxDuration': '1000',
            'contentType': 'footage,motionbackgrounds',
            'user_id': 'guest_user_' + str(int(self.last_init_time or time.time())),
            'project_id': 'proj_' + str(int(self.last_init_time or time.time())),
        }
        if self.csrf_token:
            post_data[self.csrf_token] = '1'

        encoded = urllib.parse.urlencode(post_data).encode('utf-8')
        req = urllib.request.Request('https://www.flexclip.com/', data=encoded, headers=post_headers, method='POST')

        try:
            with self.opener.open(req, timeout=15) as resp:
                raw = resp.read().decode('utf-8')
                data = json.loads(raw)
                if data.get('code') == 200:
                    raw_results = data.get('data', {}).get('results', [])
                    total = data.get('data', {}).get('total_results', len(raw_results))
                    formatted_list = []
                    for item in raw_results:
                        if not item:
                            continue
                        
                        preview_urls = item.get('preview_urls', {}) or {}
                        preview_video = (
                            preview_urls.get('_720p') or
                            preview_urls.get('_480p') or
                            preview_urls.get('_360p') or
                            preview_urls.get('_180p') or
                            ''
                        )

                        download_formats = item.get('download_formats', {}) or {}
                        mp4_formats = download_formats.get('MP4', {}) or {}
                        mov_formats = download_formats.get('MOV', {}) or {}

                        available_resolutions = []
                        for res in ['_2160p', '_1080p', '_720p']:
                            if res in mp4_formats:
                                res_label = '4K UHD (2160p)' if res == '_2160p' else ('1080p Full HD' if res == '_1080p' else '720p HD')
                                available_resolutions.append({
                                    'resolution': res.replace('_', ''),
                                    'label': res_label,
                                    'format': 'MP4',
                                    'width': mp4_formats[res].get('width'),
                                    'height': mp4_formats[res].get('height'),
                                    'size_bytes': mp4_formats[res].get('file_size_bytes')
                                })

                        formatted_list.append({
                            'id': str(item.get('id')),
                            'title': item.get('title') or 'Stock Video',
                            'thumbnail': item.get('thumbnail_url'),
                            'preview_video': preview_video,
                            'duration': item.get('duration', 0),
                            'provider': 'Storyblocks',
                            'provider_type': 'flexclip',
                            'has_4k': '_2160p' in mp4_formats or '_2160p' in mov_formats,
                            'has_hd': '_1080p' in mp4_formats or '_720p' in mp4_formats,
                            'resolutions': available_resolutions
                        })

                    return {
                        'success': True,
                        'total': total,
                        'page': page,
                        'results': formatted_list
                    }
                else:
                    logger.warning(f"FlexClip search returned non-200 code: {data}")
                    return {'success': False, 'total': 0, 'results': [], 'error': data.get('msg', 'API Error')}
        except Exception as e:
            logger.error(f"Error executing FlexClip search: {e}")
            self.csrf_token = None
            return {'success': False, 'total': 0, 'results': [], 'error': str(e)}

    def get_download_urls(self, video_id: int | str) -> Dict[str, Any]:
        self._ensure_session()
        post_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://www.flexclip.com',
            'Referer': 'https://www.flexclip.com/editor/app?ratio=landscape',
        }

        post_data = {
            'option': 'com_fj_stock',
            'task': 'stock.downloadVideo',
            'id': str(video_id),
            'user_id': 'guest_user_' + str(int(self.last_init_time or time.time())),
            'project_id': 'proj_' + str(int(self.last_init_time or time.time())),
        }
        if self.csrf_token:
            post_data[self.csrf_token] = '1'

        encoded = urllib.parse.urlencode(post_data).encode('utf-8')
        req = urllib.request.Request('https://www.flexclip.com/', data=encoded, headers=post_headers, method='POST')

        try:
            with self.opener.open(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('code') == 200:
                    raw_data = data.get('data', {})
                    downloads = []
                    mp4_data = raw_data.get('MP4', {})
                    for res_key, direct_url in mp4_data.items():
                        label = '4K UHD (2160p) MP4' if res_key == '_2160p' else ('1080p Full HD MP4' if res_key == '_1080p' else f'{res_key.replace("_", "")} MP4')
                        downloads.append({
                            'resolution': res_key.replace('_', ''),
                            'label': label,
                            'format': 'MP4',
                            'download_url': direct_url
                        })

                    mov_data = raw_data.get('MOV', {})
                    for res_key, direct_url in mov_data.items():
                        label = f'{res_key.replace("_", "")} ProRes MOV'
                        downloads.append({
                            'resolution': res_key.replace('_', ''),
                            'label': label,
                            'format': 'MOV',
                            'download_url': direct_url
                        })

                    return {
                        'success': True,
                        'downloads': downloads
                    }
                else:
                    return {'success': False, 'error': data.get('msg', 'Could not get download URLs')}
        except Exception as e:
            return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    client = FlexClipClient()
    print("Searching for 'nature'...")
    res = client.search_videos('nature', page=1, num_results=5)
    print(f"Results count: {len(res.get('results', []))}")
    if res.get('results'):
        first_id = res['results'][0]['id']
        print(f"Testing download links for video ID: {first_id}")
        dl = client.get_download_urls(first_id)
        print("Download options:", len(dl.get('downloads', [])))
        for d in dl.get('downloads', []):
            print(" -", d['label'], ":", d['download_url'][:80] + "...")
