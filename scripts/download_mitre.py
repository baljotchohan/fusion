# scripts/download_mitre.py
"""
Script to download the MITRE ATT&CK Enterprise STIX JSON dataset (~50MB)
and save it locally to the data/ folder.
"""
import os
import urllib.request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_mitre")

MITRE_URL = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "enterprise-attack.json")

def main():
    if not os.path.exists(OUTPUT_DIR):
        logger.info(f"Creating directory {OUTPUT_DIR}...")
        os.makedirs(OUTPUT_DIR)
        
    if os.path.exists(OUTPUT_FILE):
        logger.info(f"File already exists at {OUTPUT_FILE}. Skipping download.")
        return

    logger.info(f"Downloading MITRE ATT&CK data from {MITRE_URL}...")
    try:
        # Show download progress
        def progress(block_num, block_size, total_size):
            read_so_far = block_num * block_size
            if total_size > 0:
                percent = read_so_far * 100 / total_size
                print(f"Downloaded {read_so_far / (1024*1024):.2f}MB / {total_size / (1024*1024):.2f}MB ({percent:.1f}%)", end="\r")
            else:
                print(f"Downloaded {read_so_far / (1024*1024):.2f}MB", end="\r")

        urllib.request.urlretrieve(MITRE_URL, OUTPUT_FILE, reporthook=progress)
        print()  # Newline after progress ends
        logger.info(f"Successfully saved MITRE ATT&CK data to {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Failed to download MITRE ATT&CK data: {e}")
        # Clean up partial file if any
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)

if __name__ == "__main__":
    main()
