from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import requests
import aiofiles
import base64
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class ImageLabel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    x: float
    y: float
    width: float = 0.0
    height: float = 0.0
    label: str
    description: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "user"

class NASAImage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nasa_id: str
    title: str
    description: Optional[str] = None
    url: str
    thumbnail_url: Optional[str] = None
    date_created: Optional[str] = None
    media_type: str = "image"
    labels: List[ImageLabel] = []
    ai_analysis: Optional[str] = None
    keywords: List[str] = []

class SearchRequest(BaseModel):
    query: str
    media_type: str = "image"

class AIAnalysisRequest(BaseModel):
    image_url: str
    analysis_type: str = "general"  # general, features, patterns, anomalies

class LabelRequest(BaseModel):
    image_id: str
    label: ImageLabel

# NASA API Functions
async def search_nasa_images(query: str, media_type: str = "image") -> List[Dict]:
    """Search NASA's Image and Video Library"""
    try:
        nasa_api_key = os.environ.get('NASA_API_KEY', 'DEMO_KEY')
        url = "https://images-api.nasa.gov/search"
        params = {
            "q": query,
            "media_type": media_type,
            "page_size": 20
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        images = []
        
        for item in data.get("collection", {}).get("items", []):
            try:
                nasa_data = item.get("data", [{}])[0]
                links = item.get("links", [])
                
                # Get the largest image URL
                image_url = None
                thumbnail_url = None
                for link in links:
                    if link.get("render") == "image":
                        if "thumb" in link.get("href", ""):
                            thumbnail_url = link["href"]
                        else:
                            image_url = link["href"]
                
                if not image_url and thumbnail_url:
                    image_url = thumbnail_url
                
                if image_url:
                    images.append({
                        "nasa_id": nasa_data.get("nasa_id", ""),
                        "title": nasa_data.get("title", ""),
                        "description": nasa_data.get("description", ""),
                        "url": image_url,
                        "thumbnail_url": thumbnail_url,
                        "date_created": nasa_data.get("date_created", ""),
                        "media_type": nasa_data.get("media_type", "image"),
                        "keywords": nasa_data.get("keywords", [])
                    })
            except Exception as e:
                logging.error(f"Error processing NASA item: {e}")
                continue
                
        return images
    except Exception as e:
        logging.error(f"Error searching NASA images: {e}")
        return []

async def get_ai_analysis(image_url: str, analysis_type: str = "general") -> str:
    """Get AI analysis of NASA image"""
    try:
        # Initialize LLM chat
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=str(uuid.uuid4()),
            system_message="You are an expert space imagery analyst. Analyze NASA space images with scientific precision."
        ).with_model("openai", "gpt-4o")
        
        # Define prompts based on analysis type
        prompts = {
            "general": "Analyze this NASA space image. Describe what you see, identify celestial bodies, spacecraft, or Earth features. Provide scientific context.",
            "features": "Identify and describe specific features in this NASA image. Look for geological formations, atmospheric phenomena, spacecraft components, or astronomical objects.",
            "patterns": "Look for patterns, structures, or anomalies in this NASA image. Identify recurring features, formations, or unusual elements that might be of scientific interest.",
            "anomalies": "Examine this NASA image for any unusual features, anomalies, or unexpected elements. What stands out as potentially interesting or requiring further investigation?"
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        
        # Download image and convert to base64
        image_response = requests.get(image_url, timeout=30)
        image_response.raise_for_status()
        image_base64 = base64.b64encode(image_response.content).decode('utf-8')
        
        # Create image content from base64
        image_content = ImageContent(image_base64=image_base64)
        
        # Send message with image
        user_message = UserMessage(
            text=prompt,
            file_contents=[image_content]
        )
        
        response = await chat.send_message(user_message)
        return response
        
    except Exception as e:
        logging.error(f"Error in AI analysis: {e}")
        return f"AI analysis unavailable: {str(e)}"

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Zoomage NASA Image Explorer API"}

@api_router.post("/search", response_model=List[NASAImage])
async def search_images(request: SearchRequest):
    """Search NASA images"""
    try:
        nasa_results = await search_nasa_images(request.query, request.media_type)
        
        images = []
        for result in nasa_results:
            # Check if image already exists in DB
            existing = await db.nasa_images.find_one({"nasa_id": result["nasa_id"]})
            
            if existing:
                images.append(NASAImage(**existing))
            else:
                # Create new image entry
                nasa_image = NASAImage(**result)
                await db.nasa_images.insert_one(nasa_image.dict())
                images.append(nasa_image)
        
        return images
    except Exception as e:
        logging.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/images", response_model=List[NASAImage])
async def get_saved_images():
    """Get all saved NASA images"""
    try:
        images = await db.nasa_images.find().to_list(100)
        return [NASAImage(**img) for img in images]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/images/{image_id}", response_model=NASAImage)
async def get_image_details(image_id: str):
    """Get detailed information about a specific image"""
    try:
        image = await db.nasa_images.find_one({"id": image_id})
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        return NASAImage(**image)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/analyze")
async def analyze_image_with_ai(request: AIAnalysisRequest):
    """Analyze image with AI"""
    try:
        analysis = await get_ai_analysis(request.image_url, request.analysis_type)
        
        # Update image with AI analysis
        await db.nasa_images.update_one(
            {"url": request.image_url},
            {"$set": {"ai_analysis": analysis}}
        )
        
        return {"analysis": analysis}
    except Exception as e:
        logging.error(f"Error in AI analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/images/{image_id}/labels", response_model=ImageLabel)
async def add_label_to_image(image_id: str, label: ImageLabel):
    """Add a label to an image"""
    try:
        # Check if image exists
        image = await db.nasa_images.find_one({"id": image_id})
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Add label to image
        await db.nasa_images.update_one(
            {"id": image_id},
            {"$push": {"labels": label.dict()}}
        )
        
        return label
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/images/{image_id}/labels", response_model=List[ImageLabel])
async def get_image_labels(image_id: str):
    """Get all labels for an image"""
    try:
        image = await db.nasa_images.find_one({"id": image_id})
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        
        labels = image.get("labels", [])
        return [ImageLabel(**label) for label in labels]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/images/{image_id}/labels/{label_id}")
async def delete_label(image_id: str, label_id: str):
    """Delete a label from an image"""
    try:
        await db.nasa_images.update_one(
            {"id": image_id},
            {"$pull": {"labels": {"id": label_id}}}
        )
        return {"message": "Label deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/discover")
async def discover_patterns():
    """Discover patterns across multiple images using AI"""
    try:
        # Get images with labels
        images = await db.nasa_images.find({"labels": {"$ne": []}}).to_list(20)
        
        if not images:
            return {"patterns": "No labeled images found for pattern discovery"}
        
        # Prepare data for AI analysis
        pattern_data = []
        for img in images:
            labels = [f"{label['label']}: {label.get('description', '')}" for label in img.get('labels', [])]
            pattern_data.append({
                "title": img.get('title', ''),
                "labels": labels
            })
        
        # Use AI to discover patterns
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=str(uuid.uuid4()),
            system_message="You are a pattern discovery expert for space imagery. Analyze labeled features across multiple images to find patterns, correlations, and interesting discoveries."
        ).with_model("openai", "gpt-4o")
        
        prompt = f"Analyze these labeled NASA images and discover patterns:\n\n{json.dumps(pattern_data, indent=2)}\n\nIdentify recurring features, interesting correlations, and potential scientific discoveries."
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return {"patterns": response}
    except Exception as e:
        logging.error(f"Error in pattern discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()