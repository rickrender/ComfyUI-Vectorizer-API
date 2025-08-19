import torch
import numpy as np
import requests
import os
import io
import json
from PIL import Image
import folder_paths

try:
    import cairosvg
except ImportError:
    print("Warning: cairosvg is not installed. The 'scaled_png' output format will not work.")
    print("Please install it by running: pip install cairosvg")
    print("On Debian/Ubuntu, you may also need to run: sudo apt-get install libcairo2-dev pkg-config")
    cairosvg = None

class VectorizerAINode:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.config_id = None
        self.config_secret = None
        
        try:
            node_dir = os.path.dirname(__file__)
            config_path = os.path.join(node_dir, 'config.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.config_id = config.get('api_id')
                self.config_secret = config.get('api_secret')
                if self.config_id and self.config_secret:
                    print("Vectorizer.ai API: Found and loaded credentials from config.json.")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Vectorizer.ai API: Error loading config.json: {e}")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "api_id": ("STRING", {"default": "YOUR_API_ID_HERE"}),
                "api_secret": ("STRING", {"default": "YOUR_API_SECRET_HERE", "multiline": True}),
                "output_format": (["svg", "png", "scaled_png"], {"default": "svg"}),
                "mode": (["production", "test"], {"default": "production"}),
                "scale": ("FLOAT", {"default": 4.0, "min": 1.0, "max": 16.0, "step": 0.5}),
            },
            "optional": {
                "filename_prefix": ("STRING", {"default": "vectorized/vector"}),
                "max_colors": ("INT", {"default": 0, "min": 0, "max": 256, "step": 1, "display": "slider"}),
                "min_shape_area": ("FLOAT", {"default": 0.125, "min": 0.0, "max": 100.0, "step": 0.001}),
                "adobe_compatibility": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process_vectorization"
    CATEGORY = "Conversion"

    def process_vectorization(self, image, api_id, api_secret, output_format, mode, scale, filename_prefix="vectorized/vector", max_colors=0, min_shape_area=0.125, adobe_compatibility=False):
        final_api_id = api_id
        final_api_secret = api_secret
        
        is_id_empty = (final_api_id == "YOUR_API_ID_HERE" or not final_api_id.strip())
        is_secret_empty = (final_api_secret == "YOUR_API_SECRET_HERE" or not final_api_secret.strip())
        
        if is_id_empty and is_secret_empty:
            if self.config_id and self.config_secret:
                print("Using credentials from config.json.")
                final_api_id = self.config_id
                final_api_secret = self.config_secret
        
        if not final_api_id or final_api_id == "YOUR_API_ID_HERE":
            print("Vectorizer.AI Error: API ID is missing. Please provide it in the UI or in config.json.")
            return (image,)
            
        pil_image = Image.fromarray((255. * image[0].cpu().numpy()).astype(np.uint8))
        img_buffer = io.BytesIO()
        pil_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        api_output_format = 'svg' if output_format == 'scaled_png' else output_format
        data = {"mode": mode, "output.file_format": api_output_format}
        if max_colors > 0: data["processing.max_colors"] = max_colors
        if min_shape_area > 0: data["processing.shapes.min_area_px"] = min_shape_area
        if api_output_format == 'svg' and adobe_compatibility: data["output.svg.adobe_compatibility_mode"] = "true"

        print("Sending image to Vectorizer.AI for processing...")
        try:
            response = requests.post(
                'https://vectorizer.ai/api/v1/vectorize',
                files={'image': img_buffer}, data=data, 
                auth=(final_api_id, final_api_secret),
                timeout=60
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Vectorizer.AI API Error: {e}")
            return (image,)
        print("Processing complete.")

        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(filename_prefix, self.output_dir)
        
        if output_format == 'scaled_png':
            if cairosvg is None: return (image,)
            svg_filename = f"{filename}_{counter:05}.svg"
            svg_path = os.path.join(full_output_folder, svg_filename)
            with open(svg_path, 'wb') as f: f.write(response.content)
            print(f"Saved vector file to: {svg_path}")
            try:
                print(f"Scaling SVG to {scale}x PNG...")
                png_bytes = cairosvg.svg2png(bytestring=response.content, scale=scale)
                png_filename = f"{filename}_{counter:05}_scaled_{scale}x.png"
                png_path = os.path.join(full_output_folder, png_filename)
                with open(png_path, 'wb') as f: f.write(png_bytes)
                print(f"Saved scaled PNG to: {png_path}")
                processed_pil_image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
                processed_np_image = np.array(processed_pil_image).astype(np.float32) / 255.0
                return (torch.from_numpy(processed_np_image)[None,],)
            except Exception as e:
                print(f"ERROR during SVG to PNG conversion: {e}")
                return (image,)
        
        elif output_format == 'png':
            file = f"{filename}_{counter:05}.png"
            path = os.path.join(full_output_folder, file)
            with open(path, 'wb') as f: f.write(response.content)
            print(f"Saved API-generated PNG to: {path}")
            processed_pil_image = Image.open(io.BytesIO(response.content)).convert("RGB")
            processed_np_image = np.array(processed_pil_image).astype(np.float32) / 255.0
            return (torch.from_numpy(processed_np_image)[None,],)
        else:
            file = f"{filename}_{counter:05}.svg"
            path = os.path.join(full_output_folder, file)
            with open(path, 'wb') as f: f.write(response.content)
            print(f"Saved vector file to: {path}")
            return (image,)

class BackgroundRemoverNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "threshold": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
                "invert_mask": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK",)
    RETURN_NAMES = ("image_rgba", "mask",)
    FUNCTION = "remove_background"
    CATEGORY = "Conversion"

    def remove_background(self, image, threshold, invert_mask):
        img_np = np.clip(255. * image[0].cpu().numpy(), 0, 255).astype(np.uint8)
        
        top_border = img_np[0, :, :]
        bottom_border = img_np[-1, :, :]
        left_border = img_np[:, 0, :]
        right_border = img_np[:, -1, :]
        border_pixels = np.concatenate([top_border, bottom_border, left_border, right_border], axis=0)
        key_color = np.mean(border_pixels, axis=0)
        
        print(f"Automatically detected background color: R={int(key_color[0])}, G={int(key_color[1])}, B={int(key_color[2])}")

        distances = np.linalg.norm(img_np.astype(np.float32) - key_color.astype(np.float32), axis=2)
        threshold_value = threshold * 255.0
        
        mask_bool = distances > threshold_value
        if invert_mask:
            mask_bool = ~mask_bool
        
        mask_float = mask_bool.astype(np.float32)
        
        alpha_channel = (mask_float * 255).astype(np.uint8)
        rgba_np = np.dstack((img_np, alpha_channel))
        
        image_rgba_tensor = torch.from_numpy(rgba_np.astype(np.float32) / 255.0)[None,]
        mask_tensor = torch.from_numpy(mask_float)[None,]
        
        return (image_rgba_tensor, mask_tensor)

NODE_CLASS_MAPPINGS = {
    "VectorizerAINode": VectorizerAINode,
    "BackgroundRemoverNode": BackgroundRemoverNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VectorizerAINode": "Vectorizer.ai API",
    "BackgroundRemoverNode": "Background Remover (Color)"
}
