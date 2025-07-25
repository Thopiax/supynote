"""LLaVA-based OCR service using Ollama for superior handwriting recognition."""

import base64
import io
import requests
import time
from pathlib import Path
from PIL import Image
from typing import Optional, Dict, Any

from .entities import OCRResult, TextBlock


class LLaVAOCRService:
    """LLaVA OCR service using Ollama for handwritten text recognition."""
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 model: str = "llava:13b",
                 fallback_model: str = "llava:7b"):
        self.base_url = base_url
        self.model = model
        self.fallback_model = fallback_model
        self._verify_ollama_connection()
    
    def _verify_ollama_connection(self):
        """Verify Ollama is available and model is installed."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json()
            
            available_models = [m['name'] for m in models.get('models', [])]
            
            if self.model not in available_models and self.fallback_model not in available_models:
                print(f"⚠️ Neither {self.model} nor {self.fallback_model} found in Ollama")
                print(f"📥 Available models: {available_models}")
                print(f"💡 Install with: ollama pull {self.fallback_model}")
                raise RuntimeError(f"No suitable LLaVA model available")
            
            # Use the best available model
            if self.model not in available_models:
                print(f"⚠️ {self.model} not found, using {self.fallback_model}")
                self.model = self.fallback_model
            
            print(f"✅ Using LLaVA model: {self.model}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to Ollama at {self.base_url}")
            print(f"💡 Make sure Ollama is running: ollama serve")
            raise RuntimeError(f"Ollama connection failed: {e}")
    
    def _encode_image(self, image: Image.Image) -> str:
        """Encode PIL Image to base64 string."""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        image_bytes = buffer.getvalue()
        
        # Encode to base64
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def _call_llava(self, image: Image.Image, prompt: str) -> Optional[str]:
        """Call LLaVA model via Ollama API."""
        try:
            image_b64 = self._encode_image(image)
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent OCR
                    "top_p": 0.9,
                    "num_predict": 1000,  # Allow longer text output
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60  # Give more time for OCR processing
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ LLaVA API call failed: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Error processing with LLaVA: {e}")
            return None
    
    def extract_text(self, image_path: Path, page_width: float, page_height: float) -> OCRResult:
        """Extract text from image using LLaVA."""
        start_time = time.time()
        
        # Load image
        image = Image.open(image_path).convert('RGB')
        original_size = image.size
        
        print(f"🔍 Processing with LLaVA ({original_size[0]}x{original_size[1]})...")
        
        # Craft a specific prompt for handwriting OCR with note structure
        prompt = """Please carefully read all the handwritten text in this image and transcribe it exactly as written. 

These are personal notes with a specific structure:
- Notes are divided into "moments" marked as either "m. X," or "(m. X)" where X is an increasing number
- Use "-" for bullet points and "⤷" for sub bullet points  
- Maintain the original text structure, line breaks, and indentation
- Include all visible text, even if partially unclear
- Be as accurate as possible with spelling and punctuation
- Pay special attention to moment markers and bullet point symbols

Please provide only the transcribed text, without any commentary or explanation:"""
        
        # Call LLaVA
        recognized_text = self._call_llava(image, prompt)
        
        text_blocks = []
        
        if recognized_text and len(recognized_text.strip()) > 2:
            # Clean up the response (remove any meta-commentary)
            lines = recognized_text.split('\n')
            clean_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip lines that look like LLaVA commentary
                if (line and 
                    not line.startswith('I can see') and
                    not line.startswith('The image shows') and
                    not line.startswith('This appears to be') and
                    not line.startswith('Looking at')):
                    clean_lines.append(line)
            
            if clean_lines:
                final_text = '\n'.join(clean_lines)
                
                # Create a single text block covering the full page
                # LLaVA doesn't provide positioning info, so we cover the whole page
                text_block = TextBlock(
                    text=final_text,
                    confidence=self._estimate_confidence(final_text),
                    bbox=(0, 0, page_width, page_height),
                    normalized_bbox=(0, 0, 1, 1)
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
    
    def _estimate_confidence(self, text: str) -> float:
        """
        Estimate confidence for LLaVA output.
        LLaVA tends to be more reliable than TrOCR for handwriting.
        """
        if not text or len(text.strip()) < 2:
            return 0.0
        
        # Base confidence is higher for LLaVA
        score = 0.7
        
        # Longer, structured text gets higher confidence
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) > 1:
            score += 0.1
        
        # Bonus for recognizing note structure patterns
        import re
        
        # Look for moment markers: "m. X," or "(m. X)"
        moment_pattern = r'(?:^|\s)(?:\()?m\.\s*\d+(?:\)|,)'
        if re.search(moment_pattern, text, re.IGNORECASE | re.MULTILINE):
            score += 0.15
        
        # Look for bullet points
        if '- ' in text:
            score += 0.1
        
        # Look for sub-bullet points
        if '⤷' in text:
            score += 0.1
        
        # Text with proper punctuation and capitalization
        if any(c in text for c in '.!?'):
            score += 0.05
        
        # Penalize if it looks like the model is being uncertain
        uncertainty_words = ['unclear', 'difficult to read', 'appears to be', 'might be', 'possibly']
        if any(word in text.lower() for word in uncertainty_words):
            score -= 0.2
        
        return max(0.1, min(1.0, score))
    
    @property
    def name(self) -> str:
        return f"LLaVA ({self.model})"