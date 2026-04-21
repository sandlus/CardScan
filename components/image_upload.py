import os
import time
import base64
import requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

CI_QR_SAVE_URL = os.getenv("CI_QR_SAVE_URL")


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

        if not CI_QR_SAVE_URL:
            raise HTTPException(status_code=500, detail="CI_QR_SAVE_URL is missing in .env")

        file_content = await image.read()

        if not file_content:
            raise HTTPException(status_code=400, detail="Empty image file")

        # safe extension detect
        extension = "jpg"
        if image.filename and "." in image.filename:
            extension = image.filename.rsplit(".", 1)[-1].lower()

        # timestamp-based filename
        safe_filename = f"img_{int(time.time() * 1000)}.{extension}"

        print("===== FASTAPI IMAGE DEBUG =====")
        print("Original Filename:", image.filename)
        print("Generated Filename:", safe_filename)
        print("Content-Type:", image.content_type)
        print("Size:", len(file_content))
        print("Name:", name)
        print("Phone:", phone)
        print("Email:", email)
        print("Company:", company)
        print("Source:", source)
        print("Timestamp:", timestamp)
        print("CI_QR_SAVE_URL:", CI_QR_SAVE_URL)
        print("================================")

        # convert image to base64
        image_base64 = base64.b64encode(file_content).decode("utf-8")

        # send JSON to CI controller
        payload = {
            "name": name or "",
            "phone": phone or "",
            "email": email or "",
            "company": company or "",
            "source": source or "",
            "timestamp": timestamp or "",
            "filename": safe_filename,
            "qr_image": image_base64
        }

        response = requests.post(
            CI_QR_SAVE_URL,
            json=payload,
            timeout=30
        )

        print("CI Status:", response.status_code)
        print("CI Response:", response.text)

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"CI returned {response.status_code}: {response.text}"
            )

        try:
            result = response.json()
        except Exception:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid CI response: {response.text}"
            )

        if not result.get("status"):
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Image save failed on CI")
            )

        return {
            "status": True,
            "filename": result.get("file") or safe_filename,
            "image_url": result.get("image_url", ""),
            "message": "Image uploaded and saved successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print("Upload error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))