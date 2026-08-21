import os
import re
import urllib.parse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uvicorn

from backend.flexclip_client import FlexClipClient
from backend.pexels_client import PexelsClient
from backend.pixabay_client import PixabayClient
from backend.mixkit_client import MixkitClient
from backend.coverr_client import CoverrClient
from backend.license_manager import LicenseManager

app = FastAPI(title="StockStream", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

flexclip_client = FlexClipClient()
pexels_client = PexelsClient()
pixabay_client = PixabayClient()
mixkit_client = MixkitClient()
coverr_client = CoverrClient()
license_mgr = LicenseManager()

executor = ThreadPoolExecutor(max_workers=10)

# Request Models
class VerifyLicenseRequest(BaseModel):
    license_key: str
    device_id: Optional[str] = ""

class AdminLoginRequest(BaseModel):
    password: str

class CreateLicenseRequest(BaseModel):
    password: str
    client_name: Optional[str] = "Client"
    days: Optional[int] = 30

class RevokeLicenseRequest(BaseModel):
    password: str
    license_key: str

class DeleteLicenseRequest(BaseModel):
    password: str
    license_id: int

class CreateApiKeyRequest(BaseModel):
    password: str
    client_name: Optional[str] = "Developer"
    days: Optional[int] = 30
    daily_limit: Optional[int] = 100

class UpdateApiKeyLimitRequest(BaseModel):
    password: str
    api_key: str
    daily_limit: int

class RevokeApiKeyRequest(BaseModel):
    password: str
    api_key: str

class DeleteApiKeyRequest(BaseModel):
    password: str
    api_key_id: int

# --- LICENSE & ADMIN APIS ---

@app.post("/api/license/verify")
async def verify_license(req: VerifyLicenseRequest):
    res = license_mgr.verify_license(req.license_key, req.device_id)
    return res

@app.post("/api/admin/login")
async def admin_login(req: AdminLoginRequest):
    if license_mgr.check_admin_password(req.password):
        return {"success": True, "message": "Admin authenticated"}
    raise HTTPException(status_code=401, detail="Invalid admin password")

@app.get("/api/admin/licenses")
async def get_licenses(password: str = Query(...)):
    if not license_mgr.check_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    return {"success": True, "licenses": license_mgr.list_all_licenses()}

@app.post("/api/admin/create-license")
async def create_license(req: CreateLicenseRequest):
    if not license_mgr.check_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    res = license_mgr.create_license(client_name=req.client_name, days=req.days)
    return res

@app.post("/api/admin/revoke-license")
async def revoke_license(req: RevokeLicenseRequest):
    if not license_mgr.check_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    changed = license_mgr.revoke_license(req.license_key)
    return {"success": changed}

@app.post("/api/admin/delete-license")
async def delete_license(req: DeleteLicenseRequest):
    if not license_mgr.check_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    changed = license_mgr.delete_license(req.license_id)
    return {"success": changed}

# --- DEVELOPER API KEY ADMIN APIS ---

@app.get("/api/admin/api-keys")
async def get_admin_api_keys(password: str = Query(...)):
    if not license_mgr.check_admin_password(password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    return {"success": True, "api_keys": license_mgr.list_all_api_keys()}

@app.post("/api/admin/create-api-key")
async def admin_create_api_key(req: CreateApiKeyRequest):
    if not license_mgr.check_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    res = license_mgr.create_api_key(client_name=req.client_name, days=req.days, daily_limit=req.daily_limit)
    return res

@app.post("/api/admin/update-api-key-limit")
async def admin_update_api_key_limit(req: UpdateApiKeyLimitRequest):
    if not license_mgr.check_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    changed = license_mgr.update_api_key_limit(req.api_key, req.daily_limit)
    return {"success": changed}

@app.post("/api/admin/revoke-api-key")
async def admin_revoke_api_key(req: RevokeApiKeyRequest):
    if not license_mgr.check_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    changed = license_mgr.revoke_api_key(req.api_key)
    return {"success": changed}

@app.post("/api/admin/delete-api-key")
async def admin_delete_api_key(req: DeleteApiKeyRequest):
    if not license_mgr.check_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    changed = license_mgr.delete_api_key(req.api_key_id)
    return {"success": changed}

# ===================================================
# STORYBLOCKS DEVELOPER REST API (STORYBLOCKS ONLY)
# ===================================================

@app.get("/api/v1/storyblocks/search")
async def storyblocks_api_search(
    api_key: str = Query(..., description="Storyblocks API Key (SS-SB-XXXX-XXXX-XXXX)"),
    q: str = Query(..., description="Search keyword query (e.g. nature, drone, business)"),
    page: int = Query(1, ge=1, description="Page number (default: 1)"),
    num_results: int = Query(20, ge=1, le=100, description="Results per page (default: 20)"),
    sort: str = Query("most_relevant", description="most_relevant | latest")
):
    loop = asyncio.get_event_loop()
    # Authenticate and consume 1 quota unit
    auth = license_mgr.verify_and_consume_api_key(api_key, consume=True)
    if not auth.get("valid"):
        raise HTTPException(status_code=403, detail=auth.get("message"))

    clean_q = q.strip()
    if not clean_q:
        return {
            "success": True,
            "provider": "Storyblocks",
            "query": q,
            "page": page,
            "total_results": 0,
            "quota": {
                "daily_limit": auth.get("daily_limit"),
                "requests_used_today": auth.get("requests_used_today"),
                "requests_remaining_today": auth.get("requests_remaining_today")
            },
            "results": []
        }

    # Fetch Storyblocks results via flexclip_client
    res = await loop.run_in_executor(
        executor, flexclip_client.search_videos, clean_q, page, num_results, sort
    )

    if not res.get("success"):
        return {
            "success": False,
            "provider": "Storyblocks",
            "error": res.get("error", "Failed to fetch Storyblocks footage"),
            "quota": {
                "daily_limit": auth.get("daily_limit"),
                "requests_used_today": auth.get("requests_used_today"),
                "requests_remaining_today": auth.get("requests_remaining_today")
            }
        }

    formatted_results = []
    for item in res.get("results", []):
        video_id = item.get("raw_id") or item.get("id")
        formatted_results.append({
            "id": video_id,
            "title": item.get("title"),
            "thumbnail_url": item.get("thumbnail"),
            "preview_video_url": item.get("preview_video"),
            "duration_seconds": item.get("duration", 0),
            "has_4k": item.get("has_4k", False),
            "has_hd": item.get("has_hd", True),
            "resolutions": item.get("resolutions", []),
            "download_endpoint": f"/api/v1/storyblocks/download?api_key={api_key}&video_id={video_id}"
        })

    return {
        "success": True,
        "provider": "Storyblocks",
        "query": clean_q,
        "page": page,
        "total_results": res.get("total", len(formatted_results)),
        "quota": {
            "daily_limit": auth.get("daily_limit"),
            "requests_used_today": auth.get("requests_used_today"),
            "requests_remaining_today": auth.get("requests_remaining_today"),
            "total_requests": auth.get("total_requests"),
            "expires_at": auth.get("expires_at")
        },
        "results": formatted_results
    }

@app.get("/api/v1/storyblocks/download")
async def storyblocks_api_download(
    api_key: str = Query(..., description="Storyblocks API Key"),
    video_id: str = Query(..., description="Storyblocks Video ID (e.g. 12345 or flexclip_12345)")
):
    loop = asyncio.get_event_loop()
    auth = license_mgr.verify_and_consume_api_key(api_key, consume=False)
    if not auth.get("valid"):
        raise HTTPException(status_code=403, detail=auth.get("message"))

    clean_id = str(video_id).replace("flexclip_", "")
    res = await loop.run_in_executor(executor, flexclip_client.get_download_urls, clean_id)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail="Storyblocks video download links not found or expired.")

    return {
        "success": True,
        "provider": "Storyblocks",
        "video_id": clean_id,
        "downloads": res.get("downloads", [])
    }

@app.get("/api/v1/storyblocks/usage")
async def storyblocks_api_usage(
    api_key: str = Query(..., description="Storyblocks API Key")
):
    auth = license_mgr.verify_and_consume_api_key(api_key, consume=False)
    if not auth.get("valid"):
        raise HTTPException(status_code=403, detail=auth.get("message"))
    return {
        "success": True,
        "client_name": auth.get("client_name"),
        "daily_limit": auth.get("daily_limit"),
        "requests_used_today": auth.get("requests_used_today"),
        "requests_remaining_today": auth.get("requests_remaining_today"),
        "total_requests": auth.get("total_requests"),
        "expires_at": auth.get("expires_at")
    }

# --- SEARCH & MEDIA APIS ---

@app.get("/api/search")
async def search_stock_videos(
    keywords: str = Query(..., description="Keywords to search"),
    provider: str = Query("all", description="all | flexclip | pexels | pixabay"),
    page: int = Query(1, ge=1),
    num_results: int = Query(24, ge=1, le=100),
    orientation: str = Query("", description="landscape | portrait | square"),
    sort: str = Query("most_relevant")
):
    loop = asyncio.get_event_loop()
    clean_keywords = keywords.strip()
    if not clean_keywords:
        return {"success": True, "total": 0, "page": page, "results": []}

    results = []
    total = 0

    if provider == "flexclip":
        res = await loop.run_in_executor(
            executor, flexclip_client.search_videos, clean_keywords, page, num_results, sort
        )
        if res.get("success"):
            return res
        return {"success": False, "total": 0, "page": page, "results": [], "error": res.get("error")}

    elif provider == "pexels":
        res = await loop.run_in_executor(
            executor, pexels_client.search_videos, clean_keywords, page, num_results, orientation
        )
        return res

    elif provider == "pixabay":
        res = await loop.run_in_executor(
            executor, pixabay_client.search_videos, clean_keywords, page, num_results, orientation
        )
        return res

    elif provider == "mixkit":
        res = await loop.run_in_executor(
            executor, mixkit_client.search_videos, clean_keywords, page, num_results, orientation
        )
        return res

    elif provider == "coverr":
        res = await loop.run_in_executor(
            executor, coverr_client.search_videos, clean_keywords, page, num_results, orientation
        )
        return res

    else:
        # provider == "all": search Storyblocks, Pexels, Pixabay, Mixkit, and Coverr concurrently
        sub_results_count = max(5, num_results // 5)
        tasks = [
            loop.run_in_executor(executor, flexclip_client.search_videos, clean_keywords, page, sub_results_count, sort),
            loop.run_in_executor(executor, pexels_client.search_videos, clean_keywords, page, sub_results_count, orientation),
            loop.run_in_executor(executor, pixabay_client.search_videos, clean_keywords, page, sub_results_count, orientation),
            loop.run_in_executor(executor, mixkit_client.search_videos, clean_keywords, page, sub_results_count, orientation),
            loop.run_in_executor(executor, coverr_client.search_videos, clean_keywords, page, sub_results_count, orientation),
        ]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        fc_list = completed[0].get("results", []) if isinstance(completed[0], dict) and completed[0].get("success") else []
        pex_list = completed[1].get("results", []) if isinstance(completed[1], dict) and completed[1].get("success") else []
        pix_list = completed[2].get("results", []) if isinstance(completed[2], dict) and completed[2].get("success") else []
        mix_list = completed[3].get("results", []) if isinstance(completed[3], dict) and completed[3].get("success") else []
        cov_list = completed[4].get("results", []) if isinstance(completed[4], dict) and completed[4].get("success") else []

        max_len = max(len(fc_list), len(pex_list), len(pix_list), len(mix_list), len(cov_list))
        combined = []
        for i in range(max_len):
            if i < len(fc_list):
                combined.append(fc_list[i])
            if i < len(pex_list):
                combined.append(pex_list[i])
            if i < len(pix_list):
                combined.append(pix_list[i])
            if i < len(mix_list):
                combined.append(mix_list[i])
            if i < len(cov_list):
                combined.append(cov_list[i])

        total_est = sum([
            completed[0].get("total", 0) if isinstance(completed[0], dict) else 0,
            completed[1].get("total", 0) if isinstance(completed[1], dict) else 0,
            completed[2].get("total", 0) if isinstance(completed[2], dict) else 0,
            completed[3].get("total", 0) if isinstance(completed[3], dict) else 0,
            completed[4].get("total", 0) if isinstance(completed[4], dict) else 0,
        ])

        return {
            "success": True,
            "total": total_est,
            "page": page,
            "results": combined,
            "counts": {
                "storyblocks": len(fc_list),
                "pexels": len(pex_list),
                "pixabay": len(pix_list),
                "mixkit": len(mix_list),
                "coverr": len(cov_list)
            }
        }

@app.get("/api/video-details")
async def get_video_details(
    id: str = Query(...),
    provider: str = Query(...)
):
    loop = asyncio.get_event_loop()
    if provider == "flexclip":
        res = await loop.run_in_executor(executor, flexclip_client.get_download_urls, id)
        return res
    elif provider == "pexels":
        raw_id = id.replace("pexels_", "")
        res = await loop.run_in_executor(executor, pexels_client.get_download_urls, raw_id)
        return res
    elif provider == "pixabay":
        raw_id = id.replace("pixabay_", "")
        res = await loop.run_in_executor(executor, pixabay_client.get_download_urls, raw_id)
        return res
    elif provider == "mixkit":
        raw_id = id.replace("mixkit_", "")
        res = await loop.run_in_executor(executor, mixkit_client.get_download_urls, raw_id)
        return res
    elif provider == "coverr":
        raw_id = id.replace("coverr_", "")
        res = await loop.run_in_executor(executor, coverr_client.get_download_urls, raw_id)
        return res
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")

@app.get("/api/download")
async def proxy_download(
    url: str = Query(..., description="Video stream URL"),
    filename: Optional[str] = Query("stock-video.mp4")
):
    clean_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename or 'stock-video.mp4')
    if not clean_filename.endswith(('.mp4', '.mov')):
        clean_filename += '.mp4'

    async def stream_video():
        async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
            async with client.stream("GET", url, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    raise HTTPException(status_code=resp.status_code, detail="Failed to fetch video stream")
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{clean_filename}"',
        "Content-Type": "video/mp4" if clean_filename.endswith(".mp4") else "video/quicktime"
    }
    return StreamingResponse(stream_video(), headers=headers)

# Mount frontend static files
possible_frontend_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend")),
    os.path.abspath(os.path.join(os.getcwd(), "frontend")),
    os.path.abspath(os.getcwd())
]
found_path = None
for p in possible_frontend_paths:
    if os.path.exists(os.path.join(p, "index.html")):
        found_path = p
        break

if found_path:
    app.mount("/", StaticFiles(directory=found_path, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
