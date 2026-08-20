import urllib.request
import urllib.parse
import json
import ssl
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class CoverrClient:
    BASE_URL = "https://coverr.co/api/videos"

    def __init__(self):
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def search_videos(self, keywords: str, page: int = 1, num_results: int = 24, orientation: str = "") -> Dict[str, Any]:
        clean_query = keywords.strip()
        if not clean_query:
            clean_query = "nature"

        params = {
            'query': clean_query,
            'page': page,
            'page_size': num_results
        }
        
        if orientation == 'portrait':
            params['is_vertical'] = 'true'
        elif orientation == 'landscape':
            params['is_vertical'] = 'false'

        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            }
        )

        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                hits = data.get('hits', []) if isinstance(data, dict) else []
                total = data.get('total', len(hits)) if isinstance(data, dict) else len(hits)

                results = []
                for h in hits:
                    base_filename = h.get('base_filename') or h.get('slug')
                    if not base_filename:
                        continue

                    # Direct CDN video links
                    video_1080p = f"https://cdn.coverr.co/videos/{base_filename}/1080p.mp4"
                    video_720p = f"https://cdn.coverr.co/videos/{base_filename}/720p.mp4"
                    thumb = h.get('thumbnail') or f"https://cdn.coverr.co/videos/{base_filename}/thumbnail?width=640"
                    
                    max_w = h.get('max_width', 1920)
                    has_4k = max_w >= 3840

                    resolutions = []
                    if has_4k:
                        resolutions.append({
                            'resolution': '4k',
                            'label': '4K UHD (2160p) MP4',
                            'format': 'MP4',
                            'download_url': f"https://cdn.coverr.co/videos/{base_filename}/4k.mp4"
                        })
                    
                    resolutions.append({
                        'resolution': '1080p',
                        'label': '1080p Full HD MP4',
                        'format': 'MP4',
                        'download_url': video_1080p
                    })
                    resolutions.append({
                        'resolution': '720p',
                        'label': '720p HD MP4',
                        'format': 'MP4',
                        'download_url': video_720p
                    })

                    results.append({
                        'id': f"coverr_{h.get('id') or base_filename}",
                        'raw_id': base_filename,
                        'title': h.get('title') or f"Coverr Video ({clean_query.title()})",
                        'thumbnail': thumb,
                        'preview_video': video_720p,
                        'duration': h.get('duration', 15),
                        'provider': 'Coverr',
                        'provider_type': 'coverr',
                        'has_4k': has_4k,
                        'has_hd': True,
                        'resolutions': resolutions,
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
            logger.error(f"Coverr search error: {e}")
            return {'success': False, 'total': 0, 'results': [], 'error': str(e)}

    def get_download_urls(self, raw_id: str) -> Dict[str, Any]:
        return {
            'success': True,
            'downloads': [
                {
                    'resolution': '1080p',
                    'label': '1080p Full HD (MP4)',
                    'format': 'MP4',
                    'download_url': f"https://cdn.coverr.co/videos/{raw_id}/1080p.mp4"
                },
                {
                    'resolution': '720p',
                    'label': '720p HD (MP4)',
                    'format': 'MP4',
                    'download_url': f"https://cdn.coverr.co/videos/{raw_id}/720p.mp4"
                }
            ]
        }
