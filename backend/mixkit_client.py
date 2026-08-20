import urllib.request
import urllib.parse
import re
import ssl
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MixkitClient:
    BASE_URL = "https://mixkit.co/free-stock-video"

    def __init__(self):
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def search_videos(self, keywords: str, page: int = 1, num_results: int = 24, orientation: str = "") -> Dict[str, Any]:
        clean_query = re.sub(r'[^a-zA-Z0-9\s-]', '', keywords).strip()
        slug = urllib.parse.quote(clean_query.replace(' ', '-').lower())
        
        if not slug:
            slug = "nature"

        url = f"{self.BASE_URL}/{slug}/"
        if page > 1:
            url += f"?page={page}"

        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
        )

        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=12) as resp:
                html = resp.read().decode('utf-8')
                
                # Extract all video IDs and their thumbnails
                # Pattern: https://assets.mixkit.co/videos/(\d+)/\1-thumb-360-(\d+)\.jpg
                matches = re.findall(r'https://assets\.mixkit\.co/videos/(\d+)/\1-thumb-360-(\d+)\.jpg', html)
                
                results = []
                seen_ids = set()

                for vid, thumb_idx in matches:
                    if vid in seen_ids:
                        continue
                    seen_ids.add(vid)

                    thumb_url = f"https://assets.mixkit.co/videos/{vid}/{vid}-thumb-360-{thumb_idx}.jpg"
                    preview_video = f"https://assets.mixkit.co/videos/{vid}/{vid}-360.mp4"
                    download_1080p = f"https://assets.mixkit.co/videos/{vid}/{vid}-1080.mp4"
                    download_720p = f"https://assets.mixkit.co/videos/{vid}/{vid}-720.mp4"

                    clean_title = f"{clean_query.title()} Clip #{vid}"

                    resolutions = [
                        {
                            'resolution': '1080p',
                            'label': '1080p Full HD MP4',
                            'format': 'MP4',
                            'download_url': download_1080p
                        },
                        {
                            'resolution': '720p',
                            'label': '720p HD MP4',
                            'format': 'MP4',
                            'download_url': download_720p
                        }
                    ]

                    results.append({
                        'id': f"mixkit_{vid}",
                        'raw_id': vid,
                        'title': clean_title,
                        'thumbnail': thumb_url,
                        'preview_video': preview_video,
                        'duration': 15,
                        'provider': 'Mixkit',
                        'provider_type': 'mixkit',
                        'has_4k': False,
                        'has_hd': True,
                        'resolutions': resolutions
                    })

                    if len(results) >= num_results:
                        break

                return {
                    'success': True,
                    'total': len(results),
                    'page': page,
                    'results': results
                }
        except Exception as e:
            logger.error(f"Mixkit search error: {e}")
            return {'success': False, 'total': 0, 'results': [], 'error': str(e)}

    def get_download_urls(self, raw_id: str) -> Dict[str, Any]:
        return {
            'success': True,
            'downloads': [
                {
                    'resolution': '1080p',
                    'label': '1080p Full HD (MP4)',
                    'format': 'MP4',
                    'download_url': f"https://assets.mixkit.co/videos/{raw_id}/{raw_id}-1080.mp4"
                },
                {
                    'resolution': '720p',
                    'label': '720p HD (MP4)',
                    'format': 'MP4',
                    'download_url': f"https://assets.mixkit.co/videos/{raw_id}/{raw_id}-720.mp4"
                }
            ]
        }
