from sqlalchemy import create_engine, text
import requests
import os
from io import BytesIO
from PIL import Image
import logging
import urllib.parse
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use project API key for image generation
PROJECT_API_KEY = os.getenv('OPENAI_API_KEY')

# AI Image Generation API configuration
API_URL = "https://api.openai.com/v1/images/generations"

# Storage configuration
PERMANENT_STORAGE = "app/static/images/products"

# Image processing configuration
MAX_IMAGE_SIZE = (800, 800)  # Maximum dimensions
INITIAL_QUALITY = 60        # Initial JPEG compression quality (1-95)
MAX_FILE_SIZE = 65000      # Maximum file size in bytes

def ensure_directory():
    """Create storage directory if it doesn't exist"""
    if not os.path.exists(PERMANENT_STORAGE):
        os.makedirs(PERMANENT_STORAGE)
        logger.info(f"Created directory: {PERMANENT_STORAGE}")

def validate_api_key():
    """Validate that the API key is present and properly formatted"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
    if not api_key.startswith('sk-'):
        raise ValueError("Invalid OpenAI API key format. API key should start with 'sk-'")
    return api_key

def generate_image(category, brand_name):
    """Generate image using AI based on category and brand name"""
    if not PROJECT_API_KEY:
        logger.error("Project API key not found")
        raise ValueError("Project API key not found. Please set PROJECT_API_KEY in your .env file")
    
    headers = {
        "Authorization": f"Bearer {PROJECT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Create a more descriptive prompt using both category and brand name
    prompt = f"High quality product image of {brand_name} {category}"
    
    data = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        image_url = response.json()['data'][0]['url']
        
        # Download the generated image
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        return BytesIO(image_response.content)
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise

def optimize_image(image_data):
    """Optimize image size and quality"""
    try:
        img = Image.open(image_data)
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        if img.size[0] > MAX_IMAGE_SIZE[0] or img.size[1] > MAX_IMAGE_SIZE[1]:
            img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        
        current_quality = INITIAL_QUALITY
        output = BytesIO()
        img.save(output, format='JPEG', quality=current_quality, optimize=True)
        
        while output.tell() > MAX_FILE_SIZE and current_quality > 20:
            current_quality -= 10
            output = BytesIO()
            img.save(output, format='JPEG', quality=current_quality, optimize=True)
        
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error optimizing image: {str(e)}")
        raise

def save_image(category, brand_name, image_data):
    """Save the image to permanent storage and return the file path"""
    try:
        # Clean names for filename
        clean_category = ''.join(c for c in category if c.isalnum() or c in (' ', '_')).rstrip()
        clean_brand = ''.join(c for c in brand_name if c.isalnum() or c in (' ', '_')).rstrip()
        
        clean_name = f"{clean_category}_{clean_brand}".replace(' ', '_')[:50]

        print(clean_name,"======================================================================name is")
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{clean_name}_{timestamp}.jpg"
        filepath = os.path.join(PERMANENT_STORAGE, filename)
        
        # Save the image
        with open(filepath, 'wb') as f:
            f.write(image_data.getvalue())
        
        logger.info(f"Image saved at: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        raise

def download_image_with_category_brand(category, brand_name):
    """
    Main function to generate and save an image based on category and brand name
    
    Args:
        category (str): Product category
        brand_name (str): Brand name
    
    Returns:
        str: Path to the saved image file
    """
    try:
        # Ensure directory exists
        ensure_directory()
        
        # Generate image
        image_data = generate_image(category, brand_name)
        
        # Optimize image
        optimized_data = optimize_image(image_data)
        
        # Save image and return path
        return save_image(category, brand_name, optimized_data)
            
    except Exception as e:
        logger.error(f"Process failed: {str(e)}")
        raise

# if __name__ == "__main__":
#     # Example usage
#     category = "Shoes"
#     brand_name = "Nike"
#     image_path = download_image_with_category_brand(category, brand_name)
#     print(f"Image saved at: {image_path}")