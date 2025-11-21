import os
import sys
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
                "secret_id": ("STRING", {"multiline": False, "default": ""}),
                "secret_key": ("STRING", {"multiline": False, "default": ""}),
                "region": ("STRING", {"multiline": False, "default": "ap-guangzhou"}),
                "bucket": ("STRING", {"multiline": False, "default": ""}),
                "cos_path": ("STRING", {"multiline": False, "default": "comfyui_output/"}),
                "filename_prefix": ("STRING", {"multiline": False, "default": "comfy_"}),
                "compress_level": ("INT", {"default": 90, "min": 1, "max": 100, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("uploaded_urls",)
    FUNCTION = "upload_image"
    CATEGORY = "TencentCOS"
    OUTPUT_NODE = True

    def upload_image(self, images, secret_id, secret_key, region, bucket, cos_path, filename_prefix, compress_level):
        if not secret_id or not secret_key or not bucket:
            print("Error: Missing COS configuration (SecretId, SecretKey, or Bucket)")
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
            
            # Convert to RGB (in case of RGBA) to save as JPEG
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Save to buffer as JPEG
            output_buffer = BytesIO()
            img.save(output_buffer, format='JPEG', quality=compress_level)
            output_buffer.seek(0)
            
            # Generate filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            random_suffix = random.randint(1000, 9999)
            filename = f"{filename_prefix}{timestamp}_{random_suffix}.jpg"
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
                # Default format: https://<BucketName-APPID>.cos.<Region>.myqcloud.com/<Key>
                # We assume the user provided bucket name might or might not include APPID, 
                # but usually the SDK handles the bucket name as provided.
                # If the user provides "example-1250000000", that's the bucket name.
                url = f"https://{bucket}.cos.{region}.myqcloud.com/{key}"
                uploaded_urls.append(url)
                print(f"Successfully uploaded to {url}")
                
            except Exception as e:
                print(f"Failed to upload {key}: {str(e)}")
                # Continue with other images or raise? 
                # For a batch, we probably want to try all.
                continue

        return (uploaded_urls,)

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "TencentCOSUploader": TencentCOSUploader
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "TencentCOSUploader": "Tencent COS Uploader"
}
