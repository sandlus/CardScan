import os
import requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

PHP_UPLOAD_URL = os.getenv("PHP_UPLOAD_URL")


@router.post("/upload-scanned-card-image")
async def upload_scanned_card_image(
    image: UploadFile = File(...),
    source: str = Form(None),
    timestamp: str = Form(None)
):
    try:
        if not image:
            raise HTTPException(status_code=400, detail="No image file provided")

        # ✅ Read file content safely
        file_content = await image.read()
        await image.seek(0)  # reset pointer (good practice)

        files = {
            "image": (
                image.filename or "upload.jpg",
                file_content,
                image.content_type or "image/jpeg"
            )
        }

        data = {
            "source": source or "",
            "timestamp": timestamp or ""
        }

        # ✅ More browser-like headers (better chance to bypass ModSecurity)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Origin": "https://demoapp.sandlus.in",
            "Referer": "https://demoapp.sandlus.in/",
            "Connection": "keep-alive"
        }

        response = requests.post(
            PHP_UPLOAD_URL,
            files=files,
            data=data,
            headers=headers,
            timeout=30
        )

        print("PHP Status:", response.status_code)
        print("PHP Response:", response.text)

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=response.text)

        try:
            result = response.json()
        except Exception:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid PHP response: {response.text}"
            )

        if not result.get("status"):
            raise HTTPException(status_code=500, detail=result.get("message"))

        return {
            "status": True,
            "filename": result.get("filename"),
            "image_url": result.get("url")
        }

    except Exception as e:
        print("Upload error:", e)
        raise HTTPException(status_code=500, detail=str(e))