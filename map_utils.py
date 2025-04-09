import os
import math
import time
import requests
from urllib.parse import urlencode

def download_map_tiles():
    """Download map tiles for offline use around a fixed coordinate"""
    # Fixed coordinates and zoom levels
    center_lat = 28.402236
    center_lon = 76.988318
    zoom_levels = range(12, 19)  # Zoom levels 12-18
    tile_radius = 2  # How many tiles around center to download
    
    # Create tiles directory structure
    os.makedirs("tiles", exist_ok=True)
    
    # User-Agent header to identify our requests
    headers = {
        'User-Agent': 'DroneControlApp/1.0 (https://example.com)'
    }
    
    for zoom in zoom_levels:
        # Calculate tile coordinates for center point
        n = 2 ** zoom
        xtile = int((center_lon + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(math.radians(center_lat)) + 
                   1.0 / math.cos(math.radians(center_lat))) / math.pi) / 2.0 * n)
        
        # Create zoom level directory
        zoom_dir = os.path.join("tiles", str(zoom))
        os.makedirs(zoom_dir, exist_ok=True)
        
        # Download tiles around center point
        for x in range(xtile - tile_radius, xtile + tile_radius + 1):
            for y in range(ytile - tile_radius, ytile + tile_radius + 1):
                # Skip invalid tile coordinates
                if x < 0 or y < 0 or x >= n or y >= n:
                    print(f"Skipping invalid tile {zoom}/{x}/{y}")
                    continue
                
                tile_url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
                tile_path = os.path.join(zoom_dir, f"{x}")
                os.makedirs(tile_path, exist_ok=True)
                tile_file = os.path.join(tile_path, f"{y}.png")
                
                if not os.path.exists(tile_file):
                    retries = 3
                    while retries > 0:
                        try:
                            response = requests.get(tile_url, headers=headers, stream=True, timeout=10)
                            if response.status_code == 200:
                                with open(tile_file, 'wb') as f:
                                    for chunk in response.iter_content(1024):
                                        f.write(chunk)
                                print(f"Downloaded tile {zoom}/{x}/{y}")
                                break  # Success, exit retry loop
                            elif response.status_code == 404:
                                print(f"Tile not found (404): {zoom}/{x}/{y}")
                                break  # Don't retry 404 errors
                            else:
                                print(f"Failed to download {zoom}/{x}/{y} (HTTP {response.status_code})")
                        except Exception as e:
                            print(f"Error downloading {zoom}/{x}/{y}: {str(e)}")
                        
                        retries -= 1
                        if retries > 0:
                            print(f"Retrying ({retries} attempts remaining)...")
                            time.sleep(2)  # Wait before retrying
                    
                    time.sleep(0.5)  # Be polite to the server between requests

if __name__ == "__main__":
    print("Starting tile download...")
    download_map_tiles()
    print("Tile download completed.")