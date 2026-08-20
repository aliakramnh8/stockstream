import urllib.request
import urllib.parse
import json
import ssl
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PixabayClient:
    API_KEY = "12927283-aecc7a9fd783264a86b2ab8ad"
    BASE_URL = "https://pixabay.com/api/videos"

    def __init__(self):
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def search_videos(self, keywords: str, page: int = 1, num_results: int = 24, orientation: str = "") -> Dict[str, Any]:
        params = {
            'key': self.API_KEY,
            'q': keywords,
            'page': page,
            'per_page': num_results,
            'safesearch': 'true',
            'order': 'popular'
        }
        # Pixabay video API orientation: "all", "horizontal", "vertical"
        if orientation in ['horizontal', 'vertical']:
            params['orientation'] = orientation
        elif orientation == 'portrait':
            params['orientation'] = 'vertical'
        elif orientation == 'landscape':
            params['orientation'] = 'horizontal'

        url = f"{self.BASE_URL}/?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                hits = data.get('hits', [])
                total = data.get('totalHits', len(hits))

                results = []
                for h in hits:
                    videos_map = h.get('videos', {}) or {}
                    # video quality order: large (1080p), medium (720p), small (540p), tiny (360p)
                    preview_video = (
                        videos_map.get('tiny', {}).get('url') or
                        videos_map.get('small', {}).get('url') or
                        videos_map.get('medium', {}).get('url') or
                        ''
                    )
                    # Extract real video thumbnail from videos map
                    thumb = (
                        videos_map.get('medium', {}).get('thumbnail') or
                        videos_map.get('large', {}).get('thumbnail') or
                        videos_map.get('small', {}).get('thumbnail') or
                        videos_map.get('tiny', {}).get('thumbnail') or
                        ''
                    )

                    # Clean professional title from tags
                    raw_tags = [t.strip().title() for t in h.get('tags', '').split(',') if t.strip()]
                    title = ', '.join(raw_tags[:3]) if raw_tags else f"Stock Video #{h.get('id')}"

                    has_4k = False
                    has_hd = 'large' in videos_map or 'medium' in videos_map

                    resolutions = []
                    for q_name in ['large', 'medium', 'small', 'tiny']:
                        v_info = videos_map.get(q_name)
                        if v_info and v_info.get('url'):
                            w = v_info.get('width', 0)
                            h_res = v_info.get('height', 0)
                            if w >= 3840:
                                label = "4K UHD"
                                has_4k = True
                            elif w >= 1920 or h_res >= 1080:
                                label = "1080p Full HD"
                            elif w >= 1280 or h_res >= 720:
                                label = "720p HD"
                            else:
                                label = f"{w}x{h_res} ({q_name})"

                            resolutions.append({
                                'resolution': f"{h_res}p" if h_res else q_name,
                                'label': label,
                                'format': 'MP4',
                                'width': w,
                                'height': h_res,
                                'download_url': v_info.get('url')
                            })

                    results.append({
                        'id': f"pixabay_{h.get('id')}",
                        'raw_id': str(h.get('id')),
                        'title': title,
                        'thumbnail': thumb,
                        'preview_video': preview_video,
                        'duration': h.get('duration', 0),
                        'provider': 'Pixabay',
                        'provider_type': 'pixabay',
                        'has_4k': has_4k,
                        'has_hd': has_hd,
                        'resolutions': resolutions,
                        'author': h.get('user', ''),
                        'views': h.get('views', 0),
                        'downloads_count': h.get('downloads', 0)
                    })

                return {
                    'success': True,
                    'total': total,
                    'page': page,
                    'results': results
                }
        except Exception as e:
            logger.error(f"Pixabay search error: {e}")
            return {'success': False, 'total': 0, 'results': [], 'error': str(e)}

    def get_download_urls(self, raw_id: str) -> Dict[str, Any]:
        params = {
            'key': self.API_KEY,
            'id': raw_id
        }
        url = f"{self.BASE_URL}/?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                hits = data.get('hits', [])
                if not hits:
                    return {'success': False, 'error': 'Video not found'}
                h = hits[0]
                videos_map = h.get('videos', {}) or {}
                downloads = []
                for q_name in ['large', 'medium', 'small', 'tiny']:
                    v_info = videos_map.get(q_name)
                    if v_info and v_info.get('url'):
                        w = v_info.get('width', 0)
                        h_res = v_info.get('height', 0)
                        if w >= 3840:
                            label = "4K UHD (2160p) MP4"
                        elif w >= 1920 or h_res >= 1080:
                            label = "1080p Full HD MP4"
                        elif w >= 1280 or h_res >= 720:
                            label = "720p HD MP4"
                        else:
                            label = f"{w}x{h_res} MP4 ({q_name})"

                        downloads.append({
                            'resolution': f"{h_res}p" if h_res else q_name,
                            'label': label,
                            'format': 'MP4',
                            'download_url': v_info.get('url')
                        })
                return {'success': True, 'downloads': downloads}
        except Exception as e:
            return {'success': False, 'error': str(e)}
