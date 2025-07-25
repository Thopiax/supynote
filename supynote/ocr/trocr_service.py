"""TrOCR-based OCR service optimized for handwritten text recognition."""

import os
import tempfile
import torch
import numpy as np
import cv2
from typing import List, Tuple, Optional
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import time

from .entities import OCRResult, TextBlock

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    TROCR_AVAILABLE = True
except ImportError:
    TROCR_AVAILABLE = False


class TrOCRService:
    """TrOCR service optimized for Apple Silicon and handwritten text."""
    
    def __init__(self, model_name: str = "microsoft/trocr-large-handwritten"):
        if not TROCR_AVAILABLE:
            raise ImportError("TrOCR dependencies not available. Run: uv add transformers torch")
        
        self.model_name = model_name
        self.device = self._setup_device()
        self.processor = None
        self.model = None
        self._load_model()
    
    def _setup_device(self) -> torch.device:
        """Setup optimal device for Apple Silicon."""
        if torch.backends.mps.is_available():
            # Enable MPS fallback for unsupported operations
            os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
            print(f"🔥 Using Apple Silicon MPS acceleration")
            return torch.device("mps")
        elif torch.cuda.is_available():
            print(f"🔥 Using CUDA acceleration")
            return torch.device("cuda")
        else:
            print(f"⚡ Using CPU (consider upgrading for better performance)")
            return torch.device("cpu")
    
    def _load_model(self):
        """Load TrOCR model with proper device placement."""
        print(f"📥 Loading {self.model_name} model...")
        start_time = time.time()
        
        self.processor = TrOCRProcessor.from_pretrained(self.model_name)
        self.model = VisionEncoderDecoderModel.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()
        
        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.1f}s on {self.device}")
    
    def create_overlapping_regions(self, 
                                 image: Image.Image, 
                                 region_size: Tuple[int, int] = (384, 384),
                                 overlap_ratio: float = 0.2) -> List[Tuple[Image.Image, Tuple[int, int, int, int]]]:
        """
        Split large images into overlapping regions optimized for TrOCR.
        
        Args:
            image: Input PIL Image
            region_size: Size of each region (width, height)
            overlap_ratio: Overlap between regions (0.0 to 0.5)
            
        Returns:
            List of (region_image, (x, y, width, height)) tuples
        """
        width, height = image.size
        region_width, region_height = region_size
        
        # Calculate step size with overlap
        step_x = int(region_width * (1 - overlap_ratio))
        step_y = int(region_height * (1 - overlap_ratio))
        
        regions = []
        
        for y in range(0, height, step_y):
            for x in range(0, width, step_x):
                # Ensure we don't go beyond image boundaries
                x_end = min(x + region_width, width)
                y_end = min(y + region_height, height)
                
                # Skip regions that are too small
                if (x_end - x) < region_width // 2 or (y_end - y) < region_height // 2:
                    continue
                
                # Extract region
                region = image.crop((x, y, x_end, y_end))
                
                # Pad region to exact size if needed
                if region.size != region_size:
                    padded = Image.new('RGB', region_size, (255, 255, 255))
                    padded.paste(region, (0, 0))
                    region = padded
                
                regions.append((region, (x, y, x_end - x, y_end - y)))
        
        return regions
    
    def extract_text_from_region(self, region_image: Image.Image) -> Optional[str]:
        """Extract text from a single image region using TrOCR."""
        try:
            # Preprocess image
            pixel_values = self.processor(region_image, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(self.device)
            
            # Generate text
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    max_length=384,
                    num_beams=4,
                    early_stopping=True
                )
            
            # Decode text
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # Filter out very short or nonsensical results
            if len(generated_text.strip()) < 2:
                return None
            
            return generated_text.strip()
            
        except Exception as e:
            print(f"⚠️ Error processing region: {e}")
            return None
    
    def detect_text_lines(self, image: Image.Image) -> List[Tuple[int, int, int, int]]:
        """
        Detect text lines in the image using computer vision.
        Returns list of bounding boxes (x, y, width, height).
        """
        # Convert PIL to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Enhance contrast for better line detection
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Apply morphological operations to connect text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
        morph = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter and sort contours by area and position
        text_regions = []
        min_area = 500  # Minimum area for text region
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                # Filter by aspect ratio (text lines are wider than tall)
                if w > h and w > 50 and h > 15:
                    text_regions.append((x, y, w, h))
        
        # Sort by y-coordinate (top to bottom)
        text_regions.sort(key=lambda box: box[1])
        
        return text_regions

    def extract_text(self, image_path: Path, page_width: float, page_height: float) -> OCRResult:
        """Extract text using line detection + TrOCR for better accuracy."""
        start_time = time.time()
        
        # Load image
        image = Image.open(image_path).convert('RGB')
        original_size = image.size
        
        # Detect text lines first  
        text_regions = self.detect_text_lines(image)
        
        print(f"🔍 Detected {len(text_regions)} text regions in {original_size[0]}x{original_size[1]} image")
        
        text_blocks = []
        
        for i, (x, y, w, h) in enumerate(text_regions):
            # Extract text line region
            line_image = image.crop((x, y, x + w, y + h))
            
            # Resize to optimal size for TrOCR (maintain aspect ratio)
            aspect_ratio = line_image.width / line_image.height
            if aspect_ratio > 1:
                # Wide image - fit to width
                new_width = 384
                new_height = int(384 / aspect_ratio)
            else:
                # Tall image - fit to height  
                new_height = 384
                new_width = int(384 * aspect_ratio)
            
            # Ensure minimum dimensions
            new_width = max(new_width, 64)
            new_height = max(new_height, 32)
            
            line_image = line_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Enhance the line image for better OCR
            line_image = self._enhance_image_for_ocr(line_image)
            
            # Extract text from this line
            text = self.extract_text_from_region(line_image)
            
            if text and len(text.strip()) > 1:
                # Convert coordinates to PDF space
                pdf_x = (x / original_size[0]) * page_width
                pdf_y = (y / original_size[1]) * page_height
                pdf_w = (w / original_size[0]) * page_width
                pdf_h = (h / original_size[1]) * page_height
                
                text_block = TextBlock(
                    text=text,
                    confidence=self._estimate_confidence(text),
                    bbox=(pdf_x, pdf_y, pdf_w, pdf_h),
                    normalized_bbox=(x / original_size[0], y / original_size[1], 
                                   w / original_size[0], h / original_size[1])
                )
                text_blocks.append(text_block)
        
        processing_time = time.time() - start_time
        
        return OCRResult(
            page_number=0,  # Will be set by caller
            text_blocks=text_blocks,
            page_width=page_width,
            page_height=page_height,
            processing_time=processing_time
        )
    
    def _enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Enhance image quality for better OCR results."""
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # Apply slight blur to smooth pixelation
        image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        return image
    
    def _estimate_confidence(self, text: str) -> float:
        """
        Estimate confidence based on text quality heuristics.
        TrOCR doesn't provide confidence scores directly.
        """
        if not text or len(text.strip()) < 2:
            return 0.0
        
        # Basic heuristics for text quality
        score = 0.5  # Base confidence
        
        # Longer text tends to be more reliable
        if len(text) > 10:
            score += 0.2
        
        # Text with common words gets bonus
        common_words = {'the', 'and', 'is', 'to', 'in', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are', 'as', 'with', 'his', 'they', 'at', 'be', 'this', 'have', 'from', 'or', 'one', 'had', 'by', 'word', 'but', 'not', 'what', 'all', 'were', 'we', 'when', 'your', 'can', 'said', 'there', 'each', 'which', 'she', 'do', 'how', 'their', 'if', 'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her', 'would', 'make', 'like', 'into', 'him', 'time', 'has', 'two', 'more', 'very', 'after', 'words', 'here', 'just', 'first', 'any', 'new', 'some', 'could', 'good', 'than', 'also', 'around', 'another', 'came', 'come', 'work', 'three', 'must', 'because', 'does', 'part'}
        
        words = text.lower().split()
        common_count = sum(1 for word in words if word in common_words)
        if len(words) > 0 and common_count / len(words) > 0.3:
            score += 0.2
        
        # Penalize text with too many special characters
        special_ratio = sum(1 for c in text if not c.isalnum() and c not in ' .,!?-') / len(text)
        if special_ratio > 0.3:
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    @property
    def name(self) -> str:
        return f"TrOCR ({self.model_name})"