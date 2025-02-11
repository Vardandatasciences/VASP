import os
import time
import requests
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote
from datetime import datetime
from app.auth.utils import connection_pool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Storage configuration
PERMANENT_STORAGE = "app/static/images/products"

def setup_driver():
    """Set up and return a configured Chrome WebDriver"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def ensure_directory():
    """Create storage directory if it doesn't exist"""
    if not os.path.exists(PERMANENT_STORAGE):
        os.makedirs(PERMANENT_STORAGE)
        logger.info(f"Created directory: {PERMANENT_STORAGE}")

def save_to_database(product_name, image_path, category):
    """Save image information to database"""
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()

        # Insert into product_images table
        cursor.execute("""
            INSERT INTO product_images(product_name, product_image, category) 
            VALUES (%s, %s, %s)
        """, (product_name, image_path, category))

        connection.commit()
        logger.info(f"Saved image info to database: {product_name}")
        
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def download_image_with_category_brand(category, brand_name, save_folder=PERMANENT_STORAGE):
    """
    Search for a product on Amazon and download its main image
    
    Args:
        category (str): Product category
        brand_name (str): Brand name
        save_folder (str): Path to save the downloaded image
        
    Returns:
        str: Path to the downloaded image or None if failed
    """
    try:
        # Ensure directory exists
        ensure_directory()

        # Clean names for filename
        clean_category = ''.join(c for c in category if c.isalnum() or c in (' ', '_')).rstrip()
        clean_brand = ''.join(c for c in brand_name if c.isalnum() or c in (' ', '_')).rstrip()
        
        product_name = f"{clean_category}_{clean_brand}".replace(' ', '_')[:50]
        
        # Initialize driver
        driver = setup_driver()
        
        # Construct Amazon search URL
        search_query = quote(f"{brand_name} {category}")
        amazon_url = f"https://www.amazon.in/s?k={search_query}"
        
        # Load the search page
        driver.get(amazon_url)
        time.sleep(2)
        
        try:
            # Wait for and find the first product image
            wait = WebDriverWait(driver, 10)
            image_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img.s-image"))
            )
            image_url = image_element.get_attribute('src')
            
            if image_url:
                # Create filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{product_name}_{timestamp}.jpg"
                filepath = os.path.join(save_folder, filename)
                
                # Download the image
                response = requests.get(image_url, stream=True)
                if response.status_code == 200:
                    with open(filepath, 'wb') as file:
                        for chunk in response.iter_content(1024):
                            file.write(chunk)
                    
                    # Save to database
                    save_to_database(brand_name, filepath, category)
                    
                    logger.info(f"Successfully downloaded image for {product_name} to {filepath}")
                    return filepath
                else:
                    logger.error(f"Failed to download image: HTTP {response.status_code}")
            else:
                logger.error("No image URL found")
                
        except Exception as e:
            logger.error(f"Error finding product image: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in download_product_image: {str(e)}")
    
    finally:
        try:
            driver.quit()
        except:
            pass
            
    return None

# Example usage:
if __name__ == "__main__":
    category = "Washing Machine"
    brand_name = "Samsung"
    
    image_path = download_image_with_category_brand(category, brand_name)
    if image_path:
        print(f"Downloaded image for {brand_name} {category} to {image_path}")
    else:
        print(f"Failed to download image for {brand_name} {category}")
