# ComfyUI Vectorizer & Background Remover Pack

This repository contains a pack of two powerful nodes for ComfyUI designed to automate a professional vector-based image processing pipeline. Convert raster images to clean, scalable vectors using the [Vectorizer.AI API](https://vectorizer.ai/), and then perfectly remove the background for compositing and further creative work.

This pack is ideal for automating the creation of character sprites, icons, logos, and other graphic assets.

---

## ✨ Core Features

- **High-Quality Vectorization**: Integrates with the powerful Vectorizer.AI API to convert PNGs into clean, editable SVGs.
- **Infinite Scalability**: Includes a `scaled_png` option to render the resulting SVG at any resolution (e.g., 4x, 8x) for crisp, high-resolution raster images without quality loss.
- **Automatic Background Removal**: A smart "green screen" node that automatically detects and removes any solid color background. No AI guessing, just precise, controllable results.
- **Mask Output for Advanced Workflows**: The background remover provides a perfect black and white silhouette mask, ideal for inpainting, compositing, sticker effects, and driving ControlNets.
- **Secure & Convenient**: Supports API key management via an optional `config.json` file, so you don't have to enter your credentials in the workflow.

---

## 📦 Nodes Included

### 1. Vectorizer.ai API

This node is the bridge to the Vectorizer.AI service. It takes an image and sends it for vectorization.

- **Inputs**: `image`, API credentials, `output_format` (`svg`, `png`, `scaled_png`), `mode` (`production` or `test`), and other vectorization parameters.
- **Output**: Returns the original or processed `IMAGE` back into the workflow.
- **Functionality**: Saves the final vector (`.svg`) or raster (`.png`) file to your ComfyUI `output` directory, respecting your `filename_prefix` and numbering.

### 2. Background Remover (Color)

A fully automatic chroma keyer designed for images with a solid color background.

- **Inputs**: `image`, `threshold` (to control the edge softness/fuzziness).
- **Outputs**: `image_rgba` (the subject on a transparent background) and `mask` (the black and white silhouette).
- **Functionality**: Intelligently detects the background color by analyzing the image borders, making it perfect for automated pipelines where the background color might vary slightly between images.

---

## ⚙️ Installation

Activate your `venv` then proceed by following these instructions:

1.  **Clone the Repository**

    Navigate to your ComfyUI `custom_nodes` directory and clone this repository:
    ```bash
    cd ComfyUI/custom_nodes/
    git clone https://github.com/rickrender/ComfyUI-Vectorizer-API.git
    ```

2.  **Install Python Dependencies**

    Install the required Python packages using the included `requirements.txt` file.
    ```bash
    cd ComfyUI-Vectorizer-API
    pip install -r requirements.txt
    ```

3.  **Install System Dependencies (for CairoSVG)**

    The `scaled_png` feature relies on the Cairo graphics library. You must install it on your system.

    - **For Debian/Ubuntu:**
      ```bash
      sudo apt-get update && sudo apt-get install libcairo2-dev pkg-config
      ```
    - For other operating systems, please consult their package manager to install the "Cairo" library.

4.  **Set Up API Credentials (Recommended)**

    Create an account at [vectorizer.ai](https://vectorizer.ai/) and get your keys from [your account page](https://vectorizer.ai/account). For convenience, create a file named `config.json` inside the `ComfyUI-Vectorizer-Pack` folder. Add your API keys to this file:
    ```json
    {
      "api_id": "YOUR_REAL_API_ID",
      "api_secret": "YOUR_REAL_API_SECRET"
    }
    ```
    The node will automatically use these credentials if the fields in the UI are left blank. You can also enter them in the UI if you wish instead.

5.  **Restart ComfyUI**

    Completely restart your ComfyUI instance. The new nodes will appear in the "Conversion" category.

---

## Example Usage

Here is a simple, powerful pipeline to go from a generated character to a clean, transparent asset.

1.  **Generate Image**: Use your preferred method to generate a character on a solid color background.
2.  **Vectorize & Scale**: Connect the generated image to the `Vectorizer.ai API` node.
    - Set `output_format` to `scaled_png`.
    - Set `scale` to your desired multiplier (e.g., `4.0`).
3.  **Remove Background**: Connect the `IMAGE` output from the Vectorizer node to the `Background Remover (Color)` node.
    - Adjust the `threshold` slider (a value around `0.3` to `0.4` is often a good start) to get a clean edge with minimal color halo.
4.  **Save Final Image**: Connect the `image_rgba` output from the remover node to a `Save Image` node. Ensure you use a format that supports transparency, like PNG.
5.  **(Optional) Use the Mask**: Connect the `mask` output to other nodes to perform inpainting, create outlines, or for advanced compositing.

---

## Dependencies

- **Python**: `requests`, `CairoSVG`
- **System**: `libcairo2` or equivalent

## License

This project is licensed under the MIT License.

## Acknowledgements

This node pack utilizes the powerful [Vectorizer.AI](https://vectorizer.ai/) service.
