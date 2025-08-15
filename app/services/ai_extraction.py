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
    
    def extract_data(self, pdf_text: str, user_query: str) -> Dict[str, Any]:
        """
        Extract unstructured data from PDF text based on user query using LangExtract
        
        Args:
            pdf_text: Full text content from the PDF
            user_query: What the user wants to extract
            
        Returns:
            Dictionary with extraction results
        """
        if not self.enabled:
            print("⚠️ AI_EXTRACTION: LangExtract not configured, returning empty result")
            return {
                "success": True,
                "message": "AI extraction not available - LangExtract not configured properly",
                "extracted_data": [],
                "query": user_query
            }
        
        if not user_query or not user_query.strip():
            return {
                "success": True,
                "extracted_data": [],
                "message": "No extraction query provided"
            }
        
        try:
            print(f"🤖 AI_EXTRACTION: Starting LangExtract processing for query: {user_query[:100]}...")
            
            # Create a dynamic prompt based on user query
            prompt = self._create_extraction_prompt(user_query)
            examples = self._create_examples_from_query(user_query)
            
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
                parsed_data = self._parse_langextract_result(result, user_query)
                
                return {
                    "success": True,
                    "extracted_data": parsed_data,
                    "query": user_query,
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
    
    def _create_extraction_prompt(self, user_query: str) -> str:
        """
        Create a dynamic prompt based on the user's query
        """
        # Analyze the query to understand what type of extraction is needed
        query_lower = user_query.lower()
        
        # Determine extraction type and create appropriate prompt
        if any(keyword in query_lower for keyword in ['nom', 'prénom', 'name', 'client', 'personne']):
            prompt_template = textwrap.dedent("""\
            Extract names, personal information, and associated identifiers from the text.
            Focus on finding complete names (first name + last name) and any codes or identifiers associated with them.
            Use exact text for extractions. Do not paraphrase or invent information.
            Extract all relevant details as separate entities with clear relationships.
            """)
        elif any(keyword in query_lower for keyword in ['code', 'identifiant', 'référence', 'id']):
            prompt_template = textwrap.dedent("""\
            Extract codes, identifiers, and reference numbers from the text.
            Focus on alphanumeric codes, product codes, customer IDs, and similar identifiers.
            Use exact text for extractions. Maintain original formatting of codes.
            """)
        elif any(keyword in query_lower for keyword in ['email', 'mail', 'adresse', 'contact']):
            prompt_template = textwrap.dedent("""\
            Extract contact information including email addresses, postal addresses, phone numbers.
            Focus on finding complete contact details and associated information.
            Use exact text for extractions. Do not modify formatting.
            """)
        elif any(keyword in query_lower for keyword in ['téléphone', 'phone', 'numéro']):
            prompt_template = textwrap.dedent("""\
            Extract phone numbers and telecommunications information from the text.
            Focus on various phone number formats and associated contact details.
            Use exact text for extractions. Maintain original formatting.
            """)
        elif any(keyword in query_lower for keyword in ['date', 'temps', 'période']):
            prompt_template = textwrap.dedent("""\
            Extract dates, times, and temporal information from the text.
            Focus on finding specific dates, deadlines, and time-related information.
            Use exact text for extractions. Maintain date formatting.
            """)
        elif any(keyword in query_lower for keyword in ['montant', 'prix', 'coût', 'valeur', 'somme']):
            prompt_template = textwrap.dedent("""\
            Extract monetary amounts, prices, and financial information from the text.
            Focus on finding currency amounts, costs, and related financial data.
            Use exact text for extractions. Maintain currency formatting.
            """)
        else:
            # Generic extraction prompt
            prompt_template = textwrap.dedent(f"""\
            Extract the following information from the text: {user_query}
            Focus on finding exact matches and relevant information based on the user's request.
            Use exact text for extractions. Do not paraphrase or modify the extracted content.
            Provide meaningful attributes to add context to each extraction.
            """)
        
        return prompt_template
    
    def _create_examples_from_query(self, user_query: str) -> List:
        """
        Create relevant examples based on the user's query to guide LangExtract
        """
        query_lower = user_query.lower()
        
        # Example for names and client codes (most common use case based on user's example)
        if any(keyword in query_lower for keyword in ['nom', 'prénom', 'name', 'client', 'code']):
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
                            extraction_class="mailing_code",
                            extraction_text="XNBAI2024",
                            attributes={"type": "full_code", "extracted_part": "XNBA"}
                        )
                    ]
                )
            ]
        # Example for contact information
        elif any(keyword in query_lower for keyword in ['email', 'mail', 'contact']):
            examples = [
                lx.data.ExampleData(
                    text="Contact: jean.martin@example.com, Téléphone: 01 23 45 67 89",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="email",
                            extraction_text="jean.martin@example.com",
                            attributes={"type": "email_address"}
                        ),
                        lx.data.Extraction(
                            extraction_class="phone",
                            extraction_text="01 23 45 67 89",
                            attributes={"type": "phone_number", "format": "french"}
                        )
                    ]
                )
            ]
        # Example for dates
        elif any(keyword in query_lower for keyword in ['date', 'temps']):
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
        # Example for monetary amounts
        elif any(keyword in query_lower for keyword in ['montant', 'prix', 'coût']):
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
    
    def _parse_langextract_result(self, result, user_query: str) -> List[Dict[str, Any]]:
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
                
                # Add special processing for common patterns
                if extraction.extraction_class in ['mailing_code', 'code'] and extraction.extraction_text:
                    # Extract base code from formats like XNBAI -> XNBA
                    base_code = self._extract_base_code(extraction.extraction_text)
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
    
    def _extract_base_code(self, code_text: str) -> Optional[str]:
        """
        Extract base code from patterns like XNBAI -> XNBA
        """
        try:
            # Remove common suffixes and extract base part
            patterns = [
                r'^([A-Z]{4})[A-Z0-9]*$',  # XNBA from XNBAI2024
                r'^([A-Z]+\d+)[A-Z0-9]*$',  # Base pattern with numbers
                r'^([A-Z]{2,})[^A-Z]*$',    # Letters followed by non-letters
            ]
            
            for pattern in patterns:
                match = re.match(pattern, code_text.upper())
                if match:
                    return match.group(1)
            
            return None
        except Exception:
            return None