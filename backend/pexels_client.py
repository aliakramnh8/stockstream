import urllib.request
import urllib.parse
import json
import ssl
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PexelsClient:
    API_KEY = "563492ad6f9170000100000149c69c5d5a414c008c172cdd3bc8d407"
    BASE_URL = "https://api.pexels.com"

    def __init__(self):
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def search_videos(self, keywords: str, page: int = 1, num_results: int = 24, orientation: str = "") -> Dict[str, Any]:
        params = {
            'query': keywords,
            'page': page,
            'per_page': num_results,
            'size': 'small'
        }
        if orientation in ['landscape', 'portrait', 'square']:
            params['orientation'] = orientation

        url = f"{self.BASE_URL}/videos/search?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={
            'Authorization': self.API_KEY,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })

        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                videos = data.get('videos', [])
                total = data.get('total_results', len(videos))

                results = []
                for v in videos:
                    video_files = v.get('video_files', [])
                    # Sort files by width descending
                    video_files.sort(key=lambda x: (x.get('width') or 0), reverse=True)

                    # Find preview (medium/sd quality)
                    preview_video = ""
                    for vf in reversed(video_files):
                        if vf.get('link') and (vf.get('width', 0) <= 960 or vf.get('quality') == 'sd'):
                            preview_video = vf.get('link')
                            break
                    if not preview_video and video_files:
                        preview_video = video_files[-1].get('link')

                    has_4k = any((vf.get('width') or 0) >= 3840 or vf.get('quality') == 'uhd' for vf in video_files)
                    has_hd = any((vf.get('width') or 0) >= 1280 or vf.get('quality') == 'hd' for vf in video_files)

                    resolutions = []
                    for vf in video_files:
                        w = vf.get('width') or 0
                        h = vf.get('height') or 0
                        quality = vf.get('quality', '')
                        res_name = f"{h}p" if h > 0 else quality
                        if w >= 3840:
                            label = "4K UHD (2160p)"
                        elif w >= 1920 or h >= 1080:
                            label = "1080p Full HD"
                        elif w >= 1280 or h >= 720:
                            label = "720p HD"
                        else:
                            label = f"{w}x{h} ({quality})"

                        resolutions.append({
                            'resolution': res_name,
                            'label': label,
                            'format': 'MP4',
                            'width': w,
                            'height': h,
                            'download_url': vf.get('link')
                        })

                    results.append({
                        'id': f"pexels_{v.get('id')}",
                        'raw_id': str(v.get('id')),
                        'title': f"Pexels Video #{v.get('id')}",
                        'thumbnail': v.get('image'),
                        'preview_video': preview_video,
                        'duration': v.get('duration', 0),
                        'provider': 'Pexels',
                        'provider_type': 'pexels',
                        'has_4k': has_4k,
                        'has_hd': has_hd,
                        'resolutions': resolutions,
                        'author': v.get('user', {}).get('name', ''),
                        'url': v.get('url')
                    })

                return {
                    'success': True,
                    'total': total,
                    'page': page,
                    'results': results
                }
        except Exception as e:
            logger.error(f"Pexels search error: {e}")
            return {'success': False, 'total': 0, 'results': [], 'error': str(e)}

    def get_download_urls(self, raw_id: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/videos/videos/{raw_id}"
        req = urllib.request.Request(url, headers={
            'Authorization': self.API_KEY,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=12) as resp:
                v = json.loads(resp.read().decode('utf-8'))
                video_files = v.get('video_files', [])
                video_files.sort(key=lambda x: (x.get('width') or 0), reverse=True)

                downloads = []
                for vf in video_files:
                    w = vf.get('width') or 0
                    h = vf.get('height') or 0
                    quality = vf.get('quality', '')
                    if w >= 3840:
                        label = "4K UHD (2160p) MP4"
                    elif w >= 1920 or h >= 1080:
                        label = "1080p Full HD MP4"
                    elif w >= 1280 or h >= 720:
                        label = "720p HD MP4"
                    else:
                        label = f"{w}x{h} SD MP4"

                    downloads.append({
                        'resolution': f"{h}p" if h else quality,
                        'label': label,
                        'format': 'MP4',
                        'download_url': vf.get('link')
                    })

                return {'success': True, 'downloads': downloads}
        except Exception as e:
            return {'success': False, 'error': str(e)}
