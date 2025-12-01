import os
import sys
import json
import numpy as np
import torch
from PIL import Image
from io import BytesIO
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import datetime
import random

class TencentCOSUploader:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "region": ("STRING", {"multiline": False, "default": "ap-guangzhou"}),
                "bucket": ("STRING", {"multiline": False, "default": ""}),
                "cos_path": ("STRING", {"multiline": False, "default": "comfyui_output/"}),
                "filename_prefix": ("STRING", {"multiline": False, "default": "comfy_"}),
                "compress_level": ("INT", {"default": 90, "min": 1, "max": 100, "step": 1}),
                "convert_to_jpg": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("uploaded_urls",)
    FUNCTION = "upload_image"
    CATEGORY = "TencentCOS"
    OUTPUT_NODE = True

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if not os.path.exists(config_path):
            print(f"Error: config.json not found at {config_path}")
            return None
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config.json: {e}")
            return None

    def upload_image(self, images, region, bucket, cos_path, filename_prefix, compress_level, convert_to_jpg):
        config_data = self._load_config()
        if not config_data:
            print("Error: Failed to load configuration. Please ensure config.json exists and is valid.")
            return ([],)

        secret_id = config_data.get("secret_id")
        secret_key = config_data.get("secret_key")

        if not secret_id or not secret_key:
            print("Error: Missing COS configuration in config.json (secret_id or secret_key)")
            return ([],)

        # Initialize COS Client
        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
        client = CosS3Client(config)

        uploaded_urls = []
        
        # Ensure cos_path ends with / if it's a directory
        if cos_path and not cos_path.endswith('/'):
            cos_path += '/'
        
        # Process batch
        for image in images:
            # Convert Tensor to PIL Image
            # ComfyUI images are [Batch, Height, Width, Channels] in range 0-1
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            output_buffer = BytesIO()
            file_extension = ".jpg"
            
            if convert_to_jpg:
                # Convert to RGB (in case of RGBA) to save as JPEG
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(output_buffer, format='JPEG', quality=compress_level)
            else:
                # Save as PNG
                img.save(output_buffer, format='PNG')
                file_extension = ".png"

            output_buffer.seek(0)
            
            # Generate filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            random_suffix = random.randint(1000, 9999)
            filename = f"{filename_prefix}{timestamp}_{random_suffix}{file_extension}"
            key = f"{cos_path}{filename}"

            try:
                # Upload to COS
                response = client.put_object(
                    Bucket=bucket,
                    Body=output_buffer,
                    Key=key,
                    StorageClass='STANDARD',
                    EnableMD5=False
                )
                
                # Construct URL
                url = f"https://{bucket}.cos.{region}.myqcloud.com/{key}"
                uploaded_urls.append(url)
                print(f"Successfully uploaded to {url}")
                
            except Exception as e:
                print(f"Failed to upload {key}: {str(e)}")
                continue

        # Return a dictionary containing the UI output and the result tuple
        # This ensures the uploaded_urls are available in the ComfyUI history/UI
        return {"ui": {"uploaded_urls": uploaded_urls}, "result": (uploaded_urls,)}

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "TencentCOSUploader": TencentCOSUploader
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "TencentCOSUploader": "Tencent COS Uploader"
}
