import torch
import numpy as np
import requests
import os
import io
import json
from PIL import Image
import folder_paths

try:
    from lxml import etree
except ImportError:
    print("Warning: lxml is not installed. The 'Background Remover (Shape)' node will not work.")
    print("Please install it by running: pip install lxml")
    etree = None

try:
    import cairosvg
except ImportError:
    print("Warning: cairosvg is not installed. The 'scaled_png' output format will not work.")
    print("Please install it by running: pip install cairosvg")
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
                "save_svg": ("BOOLEAN", {"default": True}),
                "filename_prefix": ("STRING", {"default": "SVG/vector"}),
                "max_colors": ("INT", {"default": 0, "min": 0, "max": 256, "step": 1, "display": "slider"}),
                "min_shape_area": ("FLOAT", {"default": 0.125, "min": 0.0, "max": 100.0, "step": 0.001}),
                "adobe_compatibility": ("BOOLEAN", {"default": False}),
                "disable_gap_filler": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING",)
    RETURN_NAMES = ("image", "svg_data",)
    FUNCTION = "process_vectorization"
    CATEGORY = "Conversion"

    def process_vectorization(self, image, api_id, api_secret, output_format, mode, scale, save_svg=True, filename_prefix="vectorized/vector", max_colors=0, min_shape_area=0.125, adobe_compatibility=False, disable_gap_filler=True):
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
            return (image, "",)
            
        pil_image = Image.fromarray((255. * image[0].cpu().numpy()).astype(np.uint8))
        img_buffer = io.BytesIO()
        pil_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        api_output_format = 'png' if output_format == 'png' else 'svg'
        
        data = {"mode": mode, "output.file_format": api_output_format}
        if max_colors > 0: data["processing.max_colors"] = max_colors
        if min_shape_area > 0: data["processing.shapes.min_area_px"] = min_shape_area
        if adobe_compatibility: data["output.svg.adobe_compatibility_mode"] = "true"
        if disable_gap_filler: data["output.gap_filler.enabled"] = "false"

        print(f"Requesting '{api_output_format}' from Vectorizer.AI...")
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
            return (image, "",)
        print("Processing complete.")

        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(filename_prefix, self.output_dir)
        
        image_out = image
        svg_data_string = ""
        
        if api_output_format == 'svg':
            svg_data_string = response.content.decode('utf-8')
            if save_svg:
                svg_path = os.path.join(full_output_folder, f"{filename}_{counter:05}.svg")
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(svg_data_string)
                print(f"Saved original SVG to: {svg_path}")

            if output_format == 'scaled_png':
                if cairosvg is None: return (image, svg_data_string)
                try:
                    print(f"Scaling SVG to {scale}x PNG...")
                    png_bytes = cairosvg.svg2png(bytestring=response.content, scale=scale)
                    png_filename = f"{filename}_{counter:05}_scaled_{scale}x.png"
                    png_path = os.path.join(full_output_folder, png_filename)
                    with open(png_path, 'wb') as f: f.write(png_bytes)
                    print(f"Saved scaled PNG to: {png_path}")
                    processed_pil_image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
                    processed_np_image = np.array(processed_pil_image).astype(np.float32) / 255.0
                    image_out = torch.from_numpy(processed_np_image)[None,]
                except Exception as e:
                    print(f"ERROR during SVG to PNG conversion: {e}")

        elif api_output_format == 'png':
            png_path = os.path.join(full_output_folder, f"{filename}_{counter:05}.png")
            with open(png_path, 'wb') as f: f.write(response.content)
            print(f"Saved API-generated PNG to: {png_path}")
            processed_pil_image = Image.open(io.BytesIO(response.content)).convert("RGB")
            processed_np_image = np.array(processed_pil_image).astype(np.float32) / 255.0
            image_out = torch.from_numpy(processed_np_image)[None,]

        return (image_out, svg_data_string,)

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
        if invert_mask: mask_bool = ~mask_bool
        mask_float = mask_bool.astype(np.float32)
        alpha_channel = (mask_float * 255).astype(np.uint8)
        rgba_np = np.dstack((img_np, alpha_channel))
        image_rgba_tensor = torch.from_numpy(rgba_np.astype(np.float32) / 255.0)[None,]
        mask_tensor = torch.from_numpy(mask_float)[None,]
        return (image_rgba_tensor, mask_tensor)

class BackgroundRemoverSVGNode:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "svg_data": ("STRING", {"forceInput": True}),
                "scale": ("FLOAT", {"default": 4.0, "min": 1.0, "max": 16.0, "step": 0.5}),
            },
            "optional": {
                "save_svg": ("BOOLEAN", {"default": True}),
                "filename_prefix": ("STRING", {"default": "SVG/vector_edited"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING",)
    RETURN_NAMES = ("image_rgba", "mask", "modified_svg_data",)
    FUNCTION = "remove_background_shape"
    CATEGORY = "Conversion"

    def remove_background_shape(self, svg_data, scale, save_svg=False, filename_prefix="SVG/vector_edited"):
        blank_image = torch.zeros((1, 128, 128, 4), dtype=torch.float32)
        blank_mask = torch.zeros((1, 128, 128), dtype=torch.float32)
        blank_svg = ""

        if not svg_data or etree is None or cairosvg is None:
            return (blank_image, blank_mask, blank_svg)
        
        try:
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(svg_data.encode('utf-8'), parser=parser)
            
            paths = root.xpath('//svg:path', namespaces={'svg': 'http://www.w3.org/2000/svg'})
            
            largest_path = None
            largest_area = -1

            for path in paths:
                d = path.get('d')
                if not d: continue
                
                try:
                    coords = [float(c) for c in d.replace('M', ' ').replace('L', ' ').replace('C', ' ').replace('Z', ' ').replace('z', ' ').replace(',', ' ').split() if c]
                    if len(coords) < 2: continue
                    x_coords, y_coords = coords[0::2], coords[1::2]
                    min_x, max_x = min(x_coords), max(x_coords)
                    min_y, max_y = min(y_coords), max(y_coords)
                    area = (max_x - min_x) * (max_y - min_y)
                    if area > largest_area:
                        largest_area = area
                        largest_path = path
                except ValueError:
                    continue

            if largest_path is not None:
                print(f"Found and removed largest shape with area: {largest_area}")
                largest_path.getparent().remove(largest_path)
            else:
                print("Warning: Could not identify a largest shape to remove.")

            modified_svg_data = etree.tostring(root, pretty_print=True).decode('utf-8')

            if save_svg:
                full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(filename_prefix, self.output_dir)
                file = f"{filename}_{counter:05}.svg"
                path = os.path.join(full_output_folder, file)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(modified_svg_data)
                print(f"Saved cleaned SVG file to: {path}")

            print(f"Rendering modified SVG to {scale}x PNG...")
            png_bytes = cairosvg.svg2png(bytestring=modified_svg_data.encode('utf-8'), scale=scale)
            
            pil_image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
            rgba_np = np.array(pil_image).astype(np.float32) / 255.0
            
            mask_float = rgba_np[..., 3]
            
            image_rgba_tensor = torch.from_numpy(rgba_np)[None,]
            mask_tensor = torch.from_numpy(mask_float)[None,]
            
            return (image_rgba_tensor, mask_tensor, modified_svg_data)

        except Exception as e:
            print(f"ERROR during SVG background removal: {e}")
            return (blank_image, blank_mask, blank_svg)

NODE_CLASS_MAPPINGS = {
    "VectorizerAINode": VectorizerAINode,
    "BackgroundRemoverNode": BackgroundRemoverNode,
    "BackgroundRemoverSVGNode": BackgroundRemoverSVGNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VectorizerAINode": "Vectorizer.ai API",
    "BackgroundRemoverNode": "Background Remover (Color)",
    "BackgroundRemoverSVGNode": "Background Remover (Shape)",
}
