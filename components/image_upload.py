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
    timestamp: str = Form(None),
    name: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    company: str = Form(None)
):
    try:
        if not image:
            raise HTTPException(status_code=400, detail="No image file provided")

        if not PHP_UPLOAD_URL:
            raise HTTPException(status_code=500, detail="PHP_UPLOAD_URL is missing in .env")

        file_content = await image.read()

        if not file_content:
            raise HTTPException(status_code=400, detail="Empty image file")

        print("===== FASTAPI IMAGE DEBUG =====")
        print("Filename:", image.filename)
        print("Content-Type:", image.content_type)
        print("Size:", len(file_content))
        print("Source:", source)
        print("Timestamp:", timestamp)
        print("PHP_UPLOAD_URL:", PHP_UPLOAD_URL)
        print("================================")

        files = {
            "image": (
                image.filename or "upload.jpg",
                file_content,
                image.content_type or "image/jpeg"
            )
        }

        data = {
            "source": source or "",
            "timestamp": timestamp or "",
            "name": name or "",
            "phone": phone or "",
            "email": email or "",
            "company": company or ""
        }

        response = requests.post(
            PHP_UPLOAD_URL,
            files=files,
            data=data,
            timeout=30
        )

        print("PHP Status:", response.status_code)
        print("PHP Response:", response.text)

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"PHP returned {response.status_code}: {response.text}"
            )

        try:
            result = response.json()
        except Exception:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid PHP response: {response.text}"
            )

        if not result.get("status"):
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Image upload failed on PHP")
            )

        return {
            "status": True,
            "filename": result.get("filename"),
            "image_url": result.get("url", ""),
            "message": "Image uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print("Upload error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))