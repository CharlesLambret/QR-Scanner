import os
import re
import textwrap
from typing import List, Dict, Any, Optional
from flask import current_app

# Import LangExtract
try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False
    print("⚠️ AI_EXTRACTION: LangExtract not available - AI extraction disabled")

class AIDataExtractor:
    """
    Service for extracting unstructured data from PDF text using Google LangExtract
    """
    
    def __init__(self):
        if not LANGEXTRACT_AVAILABLE:
            print("⚠️ AI_EXTRACTION: LangExtract not installed, AI extraction disabled")
            self.enabled = False
            return
            
        # Configure the API key from environment variables
        api_key = (
            os.getenv('LANGEXTRACT_API_KEY') or 
            os.getenv('GOOGLE_API_KEY') or 
            getattr(current_app.config, 'LANGEXTRACT_API_KEY', None) or 
            getattr(current_app.config, 'GOOGLE_API_KEY', None)
        )
        
        print(f"🔍 AI_EXTRACTION: Recherche de clé API...")
        print(f"🔍 AI_EXTRACTION: LANGEXTRACT_API_KEY dans env: {'✅' if os.getenv('LANGEXTRACT_API_KEY') else '❌'}")
        print(f"🔍 AI_EXTRACTION: GOOGLE_API_KEY dans env: {'✅' if os.getenv('GOOGLE_API_KEY') else '❌'}")
        
        if api_key:
            # Set the environment variable for LangExtract
            os.environ['LANGEXTRACT_API_KEY'] = api_key
            self.enabled = True
            print("✅ AI_EXTRACTION: LangExtract configured successfully")
        else:
            print("⚠️ AI_EXTRACTION: No API key found (LANGEXTRACT_API_KEY or GOOGLE_API_KEY), AI extraction disabled")
            self.enabled = False
    
    def extract_data(self, pdf_text: str, extraction_options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract unstructured data from PDF text based on extraction options
        
        Args:
            pdf_text: Full text content from the PDF
            extraction_options: Dictionary containing extraction options including:
                - keywords: List of keywords to extract
                - search_code_length: Input code length for code extraction
                - result_code_length: Output code length for code extraction
                
        Returns:
            Dictionary with extraction results
        """
        if not self.enabled:
            print("⚠️ AI_EXTRACTION: LangExtract not configured, returning empty result")
            return {
                "success": True,
                "message": "AI extraction not available - LangExtract not configured properly",
                "extracted_data": [],
                "options": extraction_options
            }
        
        keywords = extraction_options.get('keywords', [])
        if not keywords:
            return {
                "success": True,
                "extracted_data": [],
                "message": "No keywords provided for extraction"
            }
        
        # Build query from keywords
        user_query = self._build_query_from_keywords(keywords, extraction_options)
        
        try:
            print(f"🤖 AI_EXTRACTION: Starting LangExtract processing for keywords: {keywords}...")
            
            # Create a dynamic prompt based on keywords
            prompt = self._create_extraction_prompt_from_keywords(keywords, extraction_options)
            examples = self._create_examples_from_keywords(keywords, extraction_options)
            
            print(f"🤖 AI_EXTRACTION: Sending request to LangExtract")
            
            # Use LangExtract to extract data
            result = lx.extract(
                text_or_documents=pdf_text[:500000],  # Limit text to avoid token limits
                prompt_description=prompt,
                examples=examples,
                model_id="gemini-2.5-flash",
                extraction_passes=1,  # Single pass for speed with lighter model
                max_workers=2  # Reduced workers for lighter processing
            )
            
            if result and hasattr(result, 'extractions') and result.extractions:
                print(f"🤖 AI_EXTRACTION: LangExtract found {len(result.extractions)} extractions")
                
                # Parse the LangExtract results into our format
                parsed_data = self._parse_langextract_result(result, extraction_options)
                
                return {
                    "success": True,
                    "extracted_data": parsed_data,
                    "keywords": keywords,
                    "options": extraction_options,
                    "total_extractions": len(result.extractions),
                    "model_used": "gemini-2.5-flash via LangExtract"
                }
            else:
                return {
                    "success": False,
                    "error": "No extractions found by LangExtract",
                    "extracted_data": []
                }
                
        except Exception as e:
            print(f"❌ AI_EXTRACTION: Error during LangExtract extraction: {e}")
            return {
                "success": False,
                "error": f"LangExtract extraction failed: {str(e)}",
                "extracted_data": []
            }
    
    def _build_query_from_keywords(self, keywords: List[str], options: Dict[str, Any]) -> str:
        """
        Build a human-readable query from keywords for logging/display purposes
        """
        query_parts = []
        for keyword in keywords:
            if keyword == 'code' and options.get('search_code_length') and options.get('result_code_length'):
                query_parts.append(f"codes (longueur recherche: {options['search_code_length']}, longueur résultat: {options['result_code_length']})")
            else:
                query_parts.append(keyword)
        return f"Extraire: {', '.join(query_parts)}"
    
    def _create_extraction_prompt_from_keywords(self, keywords: List[str], options: Dict[str, Any]) -> str:
        """
        Create extraction prompt based on selected keywords
        """
        prompt_parts = []
        
        if 'nom' in keywords or 'prénom' in keywords or 'name' in keywords:
            prompt_parts.append("Extract names, personal information (first names, last names)")
            
        if 'civilité' in keywords:
            prompt_parts.append("Extract titles and civilities (MR, MME, MR ET MME, M., Mme, Monsieur, Madame, etc.)")
            
        if 'code' in keywords:
            search_length = options.get('search_code_length', 4)
            result_length = options.get('result_code_length', 4)
            prompt_parts.append(f"Extract codes and identifiers. For codes, search for patterns of {search_length} characters and extract exactly {result_length} characters from the beginning")
            
        if 'email' in keywords or 'mail' in keywords:
            prompt_parts.append("Extract email addresses and related contact information")
            
        if 'téléphone' in keywords or 'phone' in keywords:
            prompt_parts.append("Extract phone numbers in various formats")
            
        if 'date' in keywords:
            prompt_parts.append("Extract dates, times, and temporal information")
            
        if 'montant' in keywords or 'prix' in keywords:
            prompt_parts.append("Extract monetary amounts, prices, and financial values")
            
        if 'adresse' in keywords:
            prompt_parts.append("Extract postal addresses and location information")
            
        prompt = textwrap.dedent(f"""\
        {' and '.join(prompt_parts) if prompt_parts else 'Extract relevant information based on the specified keywords'}.
        Use exact text for extractions. Do not paraphrase or invent information.
        Extract all relevant details as separate entities with clear relationships.
        """)
        
        return prompt
    
    def _create_examples_from_keywords(self, keywords: List[str], options: Dict[str, Any]) -> List:
        """
        Create relevant examples based on selected keywords
        """
        examples = []
        
        # Example for names and codes (most common combination)
        if ('nom' in keywords or 'prénom' in keywords) and 'code' in keywords:
            search_length = options.get('search_code_length', 5)
            result_length = options.get('result_code_length', 4)
            
            examples = [
                lx.data.ExampleData(
                    text="Client: Jean MARTIN, Code Mailing: XNBAI2024",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="client_name",
                            extraction_text="Jean MARTIN",
                            attributes={"type": "full_name", "first_name": "Jean", "last_name": "MARTIN"}
                        ),
                        lx.data.Extraction(
                            extraction_class="code",
                            extraction_text="XNBAI2024",
                            attributes={"type": "full_code", "extracted_part": "XNBA"}
                        )
                    ]
                )
            ]
        # Example for civility with names
        elif 'civilité' in keywords and ('nom' in keywords or 'prénom' in keywords):
            examples = [
                lx.data.ExampleData(
                    text="MR Jean MARTIN, MME Marie DUPONT, MR ET MME Pierre et Anne BERNARD",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="civilité",
                            extraction_text="MR",
                            attributes={"type": "civility", "gender": "male"}
                        ),
                        lx.data.Extraction(
                            extraction_class="client_name",
                            extraction_text="Jean MARTIN",
                            attributes={"type": "full_name", "first_name": "Jean", "last_name": "MARTIN"}
                        ),
                        lx.data.Extraction(
                            extraction_class="civilité",
                            extraction_text="MME",
                            attributes={"type": "civility", "gender": "female"}
                        ),
                        lx.data.Extraction(
                            extraction_class="civilité",
                            extraction_text="MR ET MME",
                            attributes={"type": "civility", "gender": "couple"}
                        )
                    ]
                )
            ]
        # Example for civility only
        elif 'civilité' in keywords:
            examples = [
                lx.data.ExampleData(
                    text="Destinataire: MR Jean MARTIN - Facture adressée à MME Marie DUPONT - Courrier pour MR ET MME BERNARD",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="civilité",
                            extraction_text="MR",
                            attributes={"type": "civility", "gender": "male"}
                        ),
                        lx.data.Extraction(
                            extraction_class="civilité",
                            extraction_text="MME",
                            attributes={"type": "civility", "gender": "female"}
                        ),
                        lx.data.Extraction(
                            extraction_class="civilité",
                            extraction_text="MR ET MME",
                            attributes={"type": "civility", "gender": "couple"}
                        )
                    ]
                )
            ]
        elif 'code' in keywords:
            search_length = options.get('search_code_length', 5)
            result_length = options.get('result_code_length', 4)
            
            examples = [
                lx.data.ExampleData(
                    text="Code de référence: ABC123XY, Identifiant: DEF456ZW",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="code",
                            extraction_text="ABC123XY",
                            attributes={"type": "reference_code"}
                        ),
                        lx.data.Extraction(
                            extraction_class="code",
                            extraction_text="DEF456ZW",
                            attributes={"type": "identifier"}
                        )
                    ]
                )
            ]
        elif 'email' in keywords or 'mail' in keywords:
            examples = [
                lx.data.ExampleData(
                    text="Contact: jean.martin@example.com, Téléphone: 01 23 45 67 89",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="email",
                            extraction_text="jean.martin@example.com",
                            attributes={"type": "email_address"}
                        )
                    ]
                )
            ]
        elif 'téléphone' in keywords or 'phone' in keywords:
            examples = [
                lx.data.ExampleData(
                    text="Téléphone: 01 23 45 67 89, Mobile: +33 6 78 90 12 34",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="phone",
                            extraction_text="01 23 45 67 89",
                            attributes={"type": "landline", "format": "french"}
                        ),
                        lx.data.Extraction(
                            extraction_class="phone",
                            extraction_text="+33 6 78 90 12 34",
                            attributes={"type": "mobile", "format": "international"}
                        )
                    ]
                )
            ]
        elif 'date' in keywords:
            examples = [
                lx.data.ExampleData(
                    text="Date de commande: 15/08/2025, Livraison prévue: 20 août 2025",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="date",
                            extraction_text="15/08/2025",
                            attributes={"type": "order_date", "format": "dd/mm/yyyy"}
                        ),
                        lx.data.Extraction(
                            extraction_class="date",
                            extraction_text="20 août 2025",
                            attributes={"type": "delivery_date", "format": "text"}
                        )
                    ]
                )
            ]
        elif any(k in keywords for k in ['montant', 'prix']):
            examples = [
                lx.data.ExampleData(
                    text="Prix total: 150,00 €, TVA: 30,00 €",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="amount",
                            extraction_text="150,00 €",
                            attributes={"type": "total_price", "currency": "EUR"}
                        ),
                        lx.data.Extraction(
                            extraction_class="amount",
                            extraction_text="30,00 €",
                            attributes={"type": "tax", "currency": "EUR"}
                        )
                    ]
                )
            ]
        else:
            # Generic example
            examples = [
                lx.data.ExampleData(
                    text="Exemple de texte avec des informations importantes à extraire.",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="information",
                            extraction_text="informations importantes",
                            attributes={"type": "relevant_info"}
                        )
                    ]
                )
            ]
        
        return examples
    
    def _parse_langextract_result(self, result, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse LangExtract results into our expected format
        """
        try:
            parsed_items = []
            
            for i, extraction in enumerate(result.extractions):
                item = {
                    "id": i + 1,
                    "type": "langextract",
                    "extraction_class": extraction.extraction_class,
                    "text": extraction.extraction_text,
                    "attributes": extraction.attributes if hasattr(extraction, 'attributes') else {},
                    "source_location": {
                        "start": extraction.start_char if hasattr(extraction, 'start_char') else None,
                        "end": extraction.end_char if hasattr(extraction, 'end_char') else None
                    },
                    "confidence": getattr(extraction, 'confidence', None),
                    "raw": extraction.extraction_text
                }
                
                # Add special processing for code extraction
                if extraction.extraction_class in ['code'] and extraction.extraction_text:
                    # Extract base code using specified lengths
                    base_code = self._extract_base_code(extraction.extraction_text, options)
                    if base_code:
                        item["attributes"]["extracted_base"] = base_code
                
                parsed_items.append(item)
            
            return parsed_items
            
        except Exception as e:
            print(f"❌ AI_EXTRACTION: Error parsing LangExtract result: {e}")
            # Fallback: return simple format
            return [{
                "id": 1,
                "type": "error",
                "text": f"Error parsing results: {str(e)}",
                "raw": str(result)
            }]
    
    def _extract_base_code(self, code_text: str, options: Dict[str, Any]) -> Optional[str]:
        """
        Extract base code using specified input and output lengths
        """
        try:
            search_length = options.get('search_code_length', 4)
            result_length = options.get('result_code_length', 4)
            
            # Clean the code text
            clean_code = code_text.strip().upper()
            
            # If result length is specified, just take the first N characters
            if result_length and len(clean_code) >= result_length:
                return clean_code[:result_length]
            
            # Fallback to original logic for backward compatibility
            patterns = [
                r'^([A-Z]{4})[A-Z0-9]*$',  # XNBA from XNBAI2024
                r'^([A-Z]+\d+)[A-Z0-9]*$',  # Base pattern with numbers
                r'^([A-Z]{2,})[^A-Z]*$',    # Letters followed by non-letters
            ]
            
            for pattern in patterns:
                match = re.match(pattern, clean_code)
                if match:
                    base = match.group(1)
                    # Truncate to result length if specified
                    if result_length and len(base) > result_length:
                        return base[:result_length]
                    return base
            
            return None
        except Exception:
            return None