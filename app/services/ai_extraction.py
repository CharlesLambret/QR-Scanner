import os
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from flask import current_app

class AIDataExtractor:
    """
    Service for extracting unstructured data from PDF text using Google Generative AI
    """
    
    def __init__(self):
        # Configure the API key from environment variables
        api_key = os.getenv('GOOGLE_API_KEY') or current_app.config.get('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.enabled = True
        else:
            print("⚠️ AI_EXTRACTION: Google API key not found, AI extraction disabled")
            self.enabled = False
    
    def extract_data(self, pdf_text: str, user_query: str) -> Dict[str, Any]:
        """
        Extract unstructured data from PDF text based on user query
        
        Args:
            pdf_text: Full text content from the PDF
            user_query: What the user wants to extract
            
        Returns:
            Dictionary with extraction results
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "AI extraction not available - Google API key not configured",
                "extracted_data": []
            }
        
        if not user_query or not user_query.strip():
            return {
                "success": True,
                "extracted_data": [],
                "message": "No extraction query provided"
            }
        
        try:
            # Build the prompt with the specified format
            prompt = f"""Search the PDF for the requested recurring values or expressions. Always return your result in a comma-separated list format. If several values are associated, return them in the format {{value 1: value, value 2:value}}, {{}}, {{}}... Here is what you need to search for in the text: "{user_query}"

PDF TEXT:
{pdf_text[:50000]}  # Limit text to avoid token limits

Please extract the requested data and format it as specified."""

            print(f"🤖 AI_EXTRACTION: Sending request to Gemini API")
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                extracted_text = response.text.strip()
                print(f"🤖 AI_EXTRACTION: Received response: {extracted_text[:200]}...")
                
                # Parse the response into structured data
                parsed_data = self._parse_extraction_result(extracted_text)
                
                return {
                    "success": True,
                    "extracted_data": parsed_data,
                    "raw_response": extracted_text,
                    "query": user_query
                }
            else:
                return {
                    "success": False,
                    "error": "No response from AI model",
                    "extracted_data": []
                }
                
        except Exception as e:
            print(f"❌ AI_EXTRACTION: Error during extraction: {e}")
            return {
                "success": False,
                "error": f"AI extraction failed: {str(e)}",
                "extracted_data": []
            }
    
    def _parse_extraction_result(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Parse the raw AI response into structured data
        
        Args:
            raw_text: Raw response from the AI model
            
        Returns:
            List of extracted data items
        """
        try:
            # Clean the response
            cleaned_text = raw_text.strip()
            
            # Split by commas and clean each item
            items = []
            current_item = ""
            brace_count = 0
            
            for char in cleaned_text:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == ',' and brace_count == 0:
                    if current_item.strip():
                        items.append(current_item.strip())
                    current_item = ""
                    continue
                
                current_item += char
            
            # Add the last item
            if current_item.strip():
                items.append(current_item.strip())
            
            # Process each item
            parsed_items = []
            for i, item in enumerate(items):
                item = item.strip()
                if not item:
                    continue
                
                # Check if it's a structured format {key: value, key2: value2}
                if item.startswith('{') and item.endswith('}'):
                    try:
                        # Parse structured data
                        item_content = item[1:-1]  # Remove braces
                        pairs = [pair.strip() for pair in item_content.split(',')]
                        structured_data = {}
                        
                        for pair in pairs:
                            if ':' in pair:
                                key, value = pair.split(':', 1)
                                structured_data[key.strip()] = value.strip()
                        
                        parsed_items.append({
                            "id": i + 1,
                            "type": "structured",
                            "data": structured_data,
                            "raw": item
                        })
                    except Exception:
                        # Fallback to simple item
                        parsed_items.append({
                            "id": i + 1,
                            "type": "simple",
                            "value": item,
                            "raw": item
                        })
                else:
                    # Simple value
                    parsed_items.append({
                        "id": i + 1,
                        "type": "simple",
                        "value": item,
                        "raw": item
                    })
            
            return parsed_items
            
        except Exception as e:
            print(f"❌ AI_EXTRACTION: Error parsing result: {e}")
            # Fallback: return raw text as single item
            return [{
                "id": 1,
                "type": "simple",
                "value": raw_text,
                "raw": raw_text
            }]