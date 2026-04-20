import os
import requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# ✅ From .env
PHP_UPLOAD_URL = os.getenv("PHP_UPLOAD_URL")


# @router.post("/upload-scanned-card-image")
# async def upload_scanned_card_image(
#     captured_image: UploadFile = File(...),
#     source: str = Form(None),
#     timestamp: str = Form(None)
# ):
#     try:
#         if not captured_image:
#             raise HTTPException(status_code=400, detail="No image file provided")

#         file_content = await captured_image.read()

#         files = {
#             "image": (
#                 captured_image.filename,
#                 file_content,
#                 captured_image.content_type or "image/jpeg"
#             )
#         }

#         data = {
#             "source": source,
#             "timestamp": timestamp
#         }

#         response = requests.post(PHP_UPLOAD_URL, files=files, data=data)

#         print("PHP Status:", response.status_code)
#         print("PHP Response:", response.text)

#         if response.status_code != 200:
#             raise HTTPException(status_code=500, detail="PHP server upload failed")

#         result = response.json()

#         if not result.get("status"):
#             raise HTTPException(status_code=500, detail=result.get("message"))

#         return {
#             "status": True,
#             "filename": result.get("filename"),
#             "image_url": result.get("url")
#         }

#     except Exception as e:
#         print("Upload error:", e)
#         raise HTTPException(status_code=500, detail=str(e)) 

@router.post("/upload-scanned-card-image")
async def upload_scanned_card_image(
    captured_image: UploadFile = File(...),
    source: str = Form(None),
    timestamp: str = Form(None)
):
    try:
        if not captured_image:
            raise HTTPException(status_code=400, detail="No image file provided")

        files = {
            "image": (
                captured_image.filename,
                captured_image.file,
                captured_image.content_type or "image/jpeg"
            )
        }

        data = {
            "source": source,
            "timestamp": timestamp
        }

        response = requests.post(PHP_UPLOAD_URL, files=files, data=data)

        print("PHP Status:", response.status_code)
        print("PHP Response:", response.text)

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="PHP server upload failed")

        try:
            result = response.json()
        except Exception:
            print("❌ RAW PHP RESPONSE:", response.text)
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