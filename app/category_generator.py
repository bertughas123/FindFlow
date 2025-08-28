"""
FindFlow Akıllı Kategori Üretici Modülü
=======================================

Bu modül, FindFlow uygulamasının akıllı kategori tespiti ve oluşturma işlevlerini içerir.SwipeStyle Akıllı Kategori Üretici Modülü
==========================================

Bu modül, SwipeStyle uygulamasının akıllı kategori tespiti ve oluşturma işlevlerini içerir.
Gemini AI kullanarak kullanıcı sorgularından kategori tespiti yapar ve gerekirse yeni kategoriler oluşturur.

Ana Sınıflar:
- CategoryGenerator: Akıllı kategori tespiti ve oluşturma ana sınıfı

Fonksiyonlar:
- add_dynamic_category_route: Flask uygulamasına dinamik kategori rotaları ekler

Özellikler:
- Akıllı kategori tespiti (exact, partial, AI recognition)
- Yeni kategori oluşturma
- Prompt-chained AI mimarisi
- Confidence scoring
- JSON dosya yönetimi
- Debug log'ları

Gereksinimler:
- Google Generative AI (Gemini)
- categories.json dosyası
- .env dosyasında GEMINI_API_KEY
"""

import json
import os
from .config import setup_gemini, get_gemini_model, generate_with_retry

class CategoryGenerator:
    """
    Akıllı kategori tespiti ve oluşturma sınıfı - FindFlow için.
    
    Bu sınıf, kullanıcı sorgularını analiz ederek mevcut kategorilerle eşleştirir
    veya gerekirse yeni kategoriler oluşturur. Prompt-chained AI mimarisi kullanır.
    
    Özellikler:
    - model: Gemini AI modeli
    - categories_file: Kategori dosyası yolu
    - category_cache: Kategori önbelleği
    
    Ana Metodlar:
    - intelligent_category_detection(): Ana kategori tespit metodu
    - _ai_category_recognition(): AI ile kategori tanıma
    - _ai_category_creation(): AI ile yeni kategori oluşturma
    
    Kullanım:
        >>> generator = CategoryGenerator()
        >>> result = generator.intelligent_category_detection("kablosuz kulaklık")
        >>> print(result['category'])
        "Headphones"
    """
    
    def __init__(self):
        """
        CategoryGenerator'ı başlatır ve AI modelini yapılandırır.
        
        Gemini API'yi yapılandırır, kategori dosyası yolunu belirler
        ve kategori önbelleğini başlatır.
        """
        self.model = None
        self.setup_ai()
        self.categories_file = 'categories.json'
        self.category_cache = {}
        
    def setup_ai(self):
        """
        AI modelini başlatır ve yapılandırır.
        
        Gemini API'yi yapılandırır ve model nesnesini oluşturur.
        Hata durumunda model None olarak kalır.
        """
        try:
            setup_gemini()
            self.model = get_gemini_model()
        except Exception as e:
            print(f"AI model setup error: {e}")
            self.model = None
    
    def intelligent_category_detection(self, query):
        """
        Akıllı kategori tespiti ve oluşturma ana metodu.
        
        Bu metod, kullanıcı sorgusunu analiz ederek en uygun kategoriyi tespit eder.
        Önce mevcut kategorilerde eşleşme arar, bulamazsa yeni kategori oluşturur.
        
        Args:
            query (str): Kullanıcı sorgusu (örn: "kablosuz kulaklık")
            
        Returns:
            dict: Tespit sonucu
                - match_type: Eşleşme türü (exact, partial, ai_recognition, ai_created)
                - category: Kategori adı
                - confidence: Güven skoru (0.0-1.0)
                - data: Kategori verileri
                - message: Bilgi mesajı
                
        Örnek:
            >>> result = generator.intelligent_category_detection("apple telefon")
            >>> print(result['category'])
            "Phone"
        """
        query = query.strip().lower()
        print(f"🔍 Starting intelligent category detection for: '{query}'")
        
        # 🛡️ Check cache first to prevent duplicate API calls
        if query in self.category_cache:
            print(f"⚡ Cache hit for query: '{query}' → '{self.category_cache[query]}'")
            return self.category_cache[query]
        
        # Load existing categories
        categories = self._load_categories()
        
        # Step 1: Direct exact match
        exact_match = self._check_exact_match(query, categories)
        if exact_match:
            # 🛡️ Cache the result
            self.category_cache[query] = exact_match
            return exact_match
            
        # Step 2: DISABLED - Partial matching causes too many false positives
        # Skip partial matching to avoid "headphones" -> "Phone" issues
        # partial_match = self._check_partial_match(query, categories)
        # if partial_match:
        #     # 🛡️ Cache the result
        #     self.category_cache[query] = partial_match
        #     return partial_match
            
        # Step 3: AI-powered category recognition (existing categories)
        ai_recognition = self._ai_category_recognition(query, categories)
        if ai_recognition['match_type'] != 'no_match':
            # 🛡️ Cache the result
            self.category_cache[query] = ai_recognition
            return ai_recognition
            
        # Step 4: AI-powered category creation (new categories)
        ai_creation = self._ai_category_creation(query)
        # 🛡️ Cache the result
        self.category_cache[query] = ai_creation
        return ai_creation
    
    def _check_exact_match(self, query, categories):
        """
        Mevcut kategorilerde tam eşleşme kontrol eder.
        
        Args:
            query (str): Kullanıcı sorgusu
            categories (dict): Mevcut kategoriler
            
        Returns:
            dict or None: Eşleşme bulunursa sonuç, yoksa None
        """
        if query in categories:
            print(f"✅ Exact match found: '{query}'")
            return {
                "match_type": "exact",
                "category": query,
                "confidence": 1.0,
                "data": categories[query]
            }
        return None
    
    def _check_partial_match(self, query, categories):
        """
        Mevcut kategorilerde kısmi eşleşme kontrol eder.
        
        Args:
            query (str): Kullanıcı sorgusu
            categories (dict): Mevcut kategoriler
            
        Returns:
            dict or None: Eşleşme bulunursa sonuç, yoksa None
        """
        for cat_name in categories:
            query_lower = query.lower()
            cat_lower = cat_name.lower()
            
            # Smart partial matching with semantic validation
            # Avoid false positives like "headphones" -> "Phone"
            
            # Case 1: Query is a clear subset of category (like "tv" in "television")
            if len(query_lower) >= 3 and query_lower in cat_lower:
                # Additional check: query should start at word boundary or be substantial part
                if cat_lower.startswith(query_lower) or len(query_lower) >= len(cat_lower) * 0.7:
                    print(f"🔍 Partial match found: '{query}' maps to '{cat_name}'")
                    return {
                        "match_type": "partial",
                        "category": cat_name,
                        "original_query": query,
                        "confidence": 0.8,
                        "data": categories[cat_name]
                    }
            
            # Case 2: Category is a clear subset of query (like "phone" in "smartphone")
            if len(cat_lower) >= 4 and cat_lower in query_lower:
                # Additional check: category should start at word boundary or be substantial part
                if query_lower.startswith(cat_lower) or query_lower.endswith(cat_lower):
                    print(f"🔍 Partial match found: '{cat_name}' found in '{query}'")
                    return {
                        "match_type": "partial",
                        "category": cat_name,
                        "original_query": query,
                        "confidence": 0.8,
                        "data": categories[cat_name]
                    }
        
        print(f"🚫 No partial matches found for '{query}'")
        return None
    
    def _ai_category_recognition(self, query, categories):
        """
        AI ile mevcut kategorilerde akıllı eşleştirme yapar.
        
        Gemini AI kullanarak kullanıcı sorgusunu mevcut kategorilerle
        semantik olarak eşleştirir.
        
        Args:
            query (str): Kullanıcı sorgusu
            categories (dict): Mevcut kategoriler
            
        Returns:
            dict: AI tanıma sonucu
        """
        if not self.model:
            return {"match_type": "no_match", "category": None, "original": query}
            
        try:
            print(f"🤖 AI category recognition for: '{query}'")
            
            # Create detailed category context
            category_context = self._build_category_context(categories)
            
            # Recognition prompt
            recognition_prompt = f"""
            You are an intelligent category recognition agent. Your task is to map user queries to existing product categories.
            
            USER QUERY: "{query}"
            
            EXISTING CATEGORIES WITH DETAILS:
            {category_context}
            
            RECOGNITION RULES:
            1. Look for semantic similarity between the query and existing categories
            2. Consider synonyms, abbreviations, and alternative names
            3. Consider language variations (English/Turkish)
            4. Examples:
               - "pc" should map to "bilgisayar" or "computer"
               - "apple telefon" should map to "phone" or "telefon"
               - "ac" should map to "klima" (air conditioner)
               - "şarj aleti" should map to relevant charging category
            
            RESPONSE FORMAT:
            If you find a match, respond with ONLY the exact category name from the list.
            If no match exists, respond with "NO_MATCH".
            
            CATEGORY NAME OR NO_MATCH:
            """
            
            response = generate_with_retry(self.model, recognition_prompt, max_retries=2, delay=2)
            suggested_category = response.text.strip()
            
            print(f"🤖 AI recognition result: '{query}' → '{suggested_category}'")
            
            # Validate the suggestion
            if suggested_category != "NO_MATCH" and suggested_category in categories:
                # Confidence validation
                confidence = self._validate_recognition_confidence(query, suggested_category)
                
                if confidence >= 0.6:  # Minimum confidence threshold
                    return {
                        "match_type": "ai_recognition",
                        "category": suggested_category,
                        "original_query": query,
                        "confidence": confidence,
                        "data": categories[suggested_category]
                    }
                else:
                    print(f"⚠️ Low confidence score: {confidence}, proceeding to creation")
            
        except Exception as e:
            print(f"❌ AI recognition error: {e}")
            
        return {"match_type": "no_match", "category": None, "original": query}
    
    def _validate_recognition_confidence(self, query, suggested_category):
        """
        AI tanıma sonucunun güven skorunu doğrular.
        
        Args:
            query (str): Orijinal kullanıcı sorgusu
            suggested_category (str): AI'nın önerdiği kategori
            
        Returns:
            float: Güven skoru (0.0-1.0)
        """
        try:
            validation_prompt = f"""
            Rate the accuracy of this category mapping on a scale of 0.0 to 1.0:
            
            User searched for: "{query}"
            Mapped to category: "{suggested_category}"
            
            Consider:
            - Semantic similarity
            - Language appropriateness
            - Logical connection
            
            Respond with ONLY a decimal number between 0.0 and 1.0:
            """
            
            response = generate_with_retry(self.model, validation_prompt, max_retries=2, delay=1)
            confidence = float(response.text.strip())
            return min(max(confidence, 0.0), 1.0)  # Clamp between 0-1
            
        except:
            return 0.5  # Default confidence if validation fails
    
    def _ai_category_creation(self, query):
        """
        AI ile yeni kategori oluşturur.
        
        Mevcut kategorilerde eşleşme bulunamadığında, Gemini AI
        kullanarak yeni kategori oluşturur ve categories.json'a kaydeder.
        
        Args:
            query (str): Kullanıcı sorgusu
            
        Returns:
            dict: Kategori oluşturma sonucu
        """
        if not self.model:
            return {"match_type": "error", "message": "AI model not available"}
            
        try:
            print(f"🆕 AI category creation for: '{query}'")
            
            # Determine the appropriate category name
            category_name = self._determine_category_name(query)
            
            # Generate category specifications
            category_data = self._generate_category_specs(category_name)
            
            if category_data:
                # Save the new category
                self._save_new_category(category_name, category_data)
                
                return {
                    "match_type": "ai_created",
                    "category": category_name,
                    "original_query": query,
                    "confidence": 0.9,
                    "data": category_data,
                    "message": f"New category '{category_name}' created successfully with detailed specifications"
                }
            else:
                return {"match_type": "creation_failed", "message": "Failed to create category"}
                
        except Exception as e:
            print(f"❌ AI category creation error: {e}")
            return {"match_type": "error", "message": f"Category creation failed: {str(e)}"}
    
    def _determine_category_name(self, query):
        """
        Sorgu için uygun kategori adını belirler.
        
        Args:
            query (str): Kullanıcı sorgusu
            
        Returns:
            str: Belirlenen kategori adı
        """
        try:
            naming_prompt = f"""
            You are a category naming expert. Given a user query, determine the best category name.
            
            USER QUERY: "{query}"
            
            NAMING RULES:
            1. Use clear, general category names (not specific product names)
            2. Prefer English names for consistency
            3. Use singular form
            4. Examples:
               - "apple telefon" → "Phone"
               - "samsung laptop" → "Laptop"
               - "gaming mouse" → "Mouse"
               - "bluetooth kulaklık" → "Headphones"
               - "klima" → "Klima" (keep Turkish for local products)
            
            Respond with ONLY the category name (1-2 words maximum):
            """
            
            response = generate_with_retry(self.model, naming_prompt, max_retries=2, delay=1)
            category_name = response.text.strip().title()
            
            # Sanitize the name
            category_name = ''.join(c for c in category_name if c.isalnum() or c.isspace()).strip()
            
            return category_name if category_name else query.title()
            
        except:
            return query.title()
    
    def _generate_category_specs(self, category_name):
        """
        AI kullanarak kategori özelliklerini oluşturur.
        Türkiye pazarı araştırması ile uygun fiyat bantları belirler.
        
        Args:
            category_name (str): Kategori adı
            
        Returns:
            dict or None: Oluşturulan kategori özellikleri
        """
        try:
            # Load existing categories for examples
            categories = self._load_categories()
            examples = self._get_category_examples(categories)
            
            # Get Turkish market price research
            price_research = self._research_turkish_market_prices(category_name)
            
            generation_prompt = f"""
            Generate a complete category specification for "{category_name}" following the exact format of existing categories.
            
            TURKISH MARKET PRICE RESEARCH:
            {price_research}
            
            EXISTING CATEGORY EXAMPLES:
            {examples}
            
            REQUIREMENTS:
            1. Create "budget_bands" with 5 realistic price ranges based on Turkish market research
               - Use actual Turkish prices (₺) that make sense for {category_name}
               - Example ranges should reflect real market segments
               - For phones: 3-8k₺, 8-15k₺, 15-25k₺, 25-40k₺, 40k₺+
               - For air conditioners: 8-15k₺, 15-25k₺, 25-35k₺, 35-50k₺, 50k₺+
               - For headphones: 200-500₺, 500-1k₺, 1-2k₺, 2-4k₺, 4k₺+
               
            2. Create "specs" array with 4-7 most relevant specifications for {category_name}
            3. Each spec must have: id, type, label (tr/en), emoji, tooltip (tr/en), weight
            4. Types: "single_choice" (for options), "boolean" (for yes/no), "range" (for numeric ranges)
            5. For single_choice, include "options" array with id and label (tr/en)
            6. Make questions specific and relevant to {category_name} buying decisions
            7. Use appropriate Turkish and English translations
            8. Include important technical specifications that matter for purchase decisions
            9. Add helpful tooltips that guide user decisions (min 30 words each)
            10. Tooltips should include: why this feature matters, usage scenarios, cost implications, technical details that help decision making
            11. Weight specs by importance: 1.0 (most important) → 0.9 → 0.8 → 0.7 → 0.6 → 0.5 (least important)
            12. Follow up order must match weight order (highest weight first)
            
            TOOLTIP REQUIREMENTS (CRITICAL):
            - Each tooltip must be at least 30 words long and educational
            - Include WHY this feature/specification matters
            - Mention real-world usage scenarios and examples
            - Explain cost/benefit trade-offs when relevant
            - Use technical details that help users make informed decisions
            - Provide context about industry standards or typical ranges
            - Help users understand consequences of their choices
            
            TOOLTIP EXAMPLES:
            - Camera: "Kamera kalitesi sosyal medya paylaşımları, aile fotoğrafları ve video görüşmeleri için kritiktir. Profesyonel fotoğrafçılık yapacaksanız yüksek megapiksel ve gece modu önemlidir. Günlük kullanım için orta seviye yeterli olabilir ve daha uygun fiyatlıdır."
            - Battery: "Pil ömrü günlük kullanım alışkanlıklarınızı doğrudan etkiler. Yoğun kullanıcılar için tüm gün dayanan pil şarttır. Hafif kullanıcılar için daha küçük pil yeterli olup cihazı daha hafif ve ucuz yapar."
            - Storage: "Depolama alanı fotoğraf, video, uygulama ve müzik koleksiyonunuzu belirler. 128GB ortalama kullanıcı için yeterli, 256GB+ profesyonel kullanım için önerilir. Daha fazla depolama fiyatı artırır ancak gelecekte genişletme ihtiyacını azaltır."
            
            DETAILED SPEC REQUIREMENTS:
            - Create comprehensive questions that help users make informed decisions
            - Each single_choice should have 3-6 meaningful options
            - Always include "Fark etmez" or "No preference" option for single_choice specs
            - Use specific ranges, sizes, or technical details in options (e.g., "64-128GB", "6.0-6.5 inch")
            - Questions should be practical and relate to real usage scenarios
            - Avoid generic questions like "quality" - be specific about what quality means
            
            CATEGORY-SPECIFIC DETAILED GUIDANCE:
            - For phones: camera quality, battery life, performance level, storage, screen size, OS, brand, special features
            - For laptops: primary use, processor type, RAM, storage type, screen size, portability, battery life, brand
            - For headphones: form factor, wireless, ANC, sound quality, comfort, use case, brand
            - For appliances: capacity/size, energy efficiency, smart features, installation type, brand
            - For vehicles/parts: compatibility, usage type, brand, size/specifications, special features
            - For electronics: performance level, connectivity, compatibility, brand, warranty, special features
            
            EMOJI REQUIREMENTS:
            - Use only simple, widely supported emojis (avoid complex or rare emojis)
            - Test emoji compatibility: 📱💻🎧📺🖱️⌨️🖥️📷🔋⚡🌐🏢📏🎯🛡️🚗
            - Avoid emojis with skin tone modifiers or complex combinations
            - Each spec must have exactly one relevant emoji
            
            QUALITY VALIDATION:
            - Ensure all questions are clear and unambiguous
            - Avoid complex technical terms that may confuse users
            - Questions should lead to actionable purchase decisions
            - Include "Bilmiyorum/Fark etmez" or "No preference" options where appropriate
            - Test question flow to prevent infinite loops
            
            EXAMPLE HIGH-QUALITY SPEC (for reference):
            {{
                "id": "camera_quality",
                "type": "single_choice",
                "label": {{
                    "tr": "Kamera kalitesi ne kadar önemli?",
                    "en": "How important is camera quality?"
                }},
                "emoji": "📸",
                "tooltip": {{
                    "tr": "Kamera kalitesi sosyal medya paylaşımları, aile fotoğrafları ve video görüşmeleri için kritiktir. Profesyonel fotoğrafçılık yapacaksanız yüksek megapiksel, gece modu ve optik zoom önemlidir. Günlük kullanım için orta seviye yeterli olabilir ve daha uygun fiyatlıdır. Instagram, TikTok kullanıyorsanız iyi kamera önemlidir.",
                    "en": "Camera quality is critical for social media sharing, family photos, and video calls. If you do professional photography, high megapixels, night mode, and optical zoom are important. For daily use, mid-level may be sufficient and more affordable. If you use Instagram, TikTok, good camera is important."
                }},
                "options": [
                    {{"id": "professional", "label": {{"tr": "Çok önemli (Profesyonel kalite)", "en": "Very important (Professional quality)"}}}},
                    {{"id": "good", "label": {{"tr": "Önemli (İyi kalite)", "en": "Important (Good quality)"}}}},
                    {{"id": "basic", "label": {{"tr": "Temel yeterli", "en": "Basic is sufficient"}}}},
                    {{"id": "no_preference", "label": {{"tr": "Fark etmez", "en": "No preference"}}}}
                ],
                "weight": 1.0
            }}
            
            OUTPUT ONLY VALID JSON (no markdown, no explanations):
            """
            
            print(f"🤖 Yeni kategori oluşturuluyor: {category_name} (Detaylı specler ve Türkiye pazarı araştırması ile)")
            response = generate_with_retry(self.model, generation_prompt, max_retries=3, delay=3)
            return self._parse_ai_response(response.text, category_name)
            
        except Exception as e:
            print(f"❌ Category spec generation error: {e}")
            return None
    
    def _research_turkish_market_prices(self, category_name):
        """
        Türkiye pazarı için kategori fiyat araştırması yapar.
        
        Args:
            category_name (str): Kategori adı
            
        Returns:
            str: Fiyat araştırması sonuçları
        """
        try:
            if not self.model:
                return self._get_default_price_ranges(category_name)
                
            research_prompt = f"""
            Research Turkish market prices for "{category_name}" products in 2024-2025.
            
            Provide realistic price ranges for different market segments:
            - Entry level / Budget segment
            - Mid-range / Popular segment  
            - Premium / High-end segment
            - Luxury / Professional segment
            
            Consider:
            - Turkish Lira (₺) pricing
            - Local market conditions
            - Popular brands available in Turkey
            - Import taxes and VAT (18%)
            - Typical price distribution
            
            Format your response as realistic price bands that make sense for the category.
            
            Examples for context:
            - Basic phones: 3-8k₺
            - Gaming laptops: 15-50k₺
            - Air conditioners: 8-35k₺
            - Bluetooth headphones: 200-2k₺
            - Washing machines: 5-20k₺
            
            For {category_name}, provide 5 realistic price bands:
            """
            
            response = generate_with_retry(self.model, research_prompt, max_retries=2, delay=2)
            return response.text.strip()
            
        except Exception as e:
            print(f"❌ Price research error: {e}")
            return self._get_default_price_ranges(category_name)
    
    def _get_default_price_ranges(self, category_name):
        """
        Kategori için varsayılan fiyat aralıkları sağlar.
        
        Args:
            category_name (str): Kategori adı
            
        Returns:
            str: Varsayılan fiyat bilgileri
        """
        category_lower = category_name.lower()
        
        # Kategori bazlı varsayılan fiyat aralıkları
        if any(word in category_lower for word in ['phone', 'telefon', 'smartphone']):
            return "Turkish phone market: Entry 3-8k₺, Mid 8-15k₺, Premium 15-25k₺, Flagship 25-40k₺, Ultra 40k₺+"
        elif any(word in category_lower for word in ['laptop', 'computer', 'bilgisayar']):
            return "Turkish laptop market: Basic 8-15k₺, Performance 15-30k₺, Gaming 30-60k₺, Professional 60k₺+"
        elif any(word in category_lower for word in ['klima', 'klimalar', 'air']):
            return "Turkish AC market: Basic 8-15k₺, Inverter 15-25k₺, Smart 25-35k₺, Premium 35k₺+"
        elif any(word in category_lower for word in ['headphone', 'kulaklık', 'earphone']):
            return "Turkish headphone market: Basic 200-500₺, Good 500-1.5k₺, Premium 1.5-4k₺, Professional 4k₺+"
        elif any(word in category_lower for word in ['tv', 'televizyon']):
            return "Turkish TV market: Basic 5-12k₺, Smart 12-25k₺, 4K Premium 25-50k₺, OLED 50k₺+"
        elif any(word in category_lower for word in ['watch', 'saat', 'smart']):
            return "Turkish smartwatch market: Basic 500-1.5k₺, Fitness 1.5-3k₺, Premium 3-8k₺, Luxury 8k₺+"
        else:
            return f"General Turkish market for {category_name}: Budget 500-2k₺, Mid 2-5k₺, Premium 5-15k₺, Luxury 15k₺+"
    
    def _build_category_context(self, categories):
        """
        Mevcut kategoriler için detaylı bağlam oluşturur.
        
        Args:
            categories (dict): Mevcut kategoriler
            
        Returns:
            str: Kategori bağlam metni
        """
        context_parts = []
        
        for cat_name, cat_data in categories.items():
            # Extract key characteristics
            specs_summary = []
            if "specs" in cat_data:
                for spec in cat_data["specs"][:3]:  # First 3 specs
                    if "label" in spec and "tr" in spec["label"]:
                        specs_summary.append(spec["label"]["tr"])
            
            # Build context entry
            context_entry = f"- {cat_name}: {', '.join(specs_summary) if specs_summary else 'General product'}"
            context_parts.append(context_entry)
        
        return '\n'.join(context_parts)
    
    def _get_category_examples(self, categories):
        """
        AI oluşturma için kategori örnekleri alır.
        
        Args:
            categories (dict): Mevcut kategoriler
            
        Returns:
            str: Kategori örnekleri JSON formatında
        """
        examples = []
        for cat_name, cat_data in list(categories.items())[:2]:  # First 2 categories
            examples.append(f'"{cat_name}": {json.dumps(cat_data, indent=2, ensure_ascii=False)}')
        
        return '\n\n'.join(examples)
    
    def _parse_ai_response(self, text, category_name):
        """
        AI yanıtını kategori verilerine dönüştürür.
        
        Args:
            text (str): AI'dan gelen ham yanıt
            category_name (str): Kategori adı
            
        Returns:
            dict or None: Ayrıştırılmış kategori verileri
        """
        try:
            print(f"🔍 Parsing AI response for category: {category_name}")
            print(f"📄 Raw response length: {len(text)} characters")
            
            # Clean the response - multiple attempts
            json_content = text.strip()
            
            # Remove markdown code blocks
            if '```json' in json_content:
                start_idx = json_content.find('```json') + 7
                end_idx = json_content.find('```', start_idx)
                if end_idx > start_idx:
                    json_content = json_content[start_idx:end_idx]
            elif '```' in json_content:
                start_idx = json_content.find('```') + 3
                end_idx = json_content.rfind('```')
                if end_idx > start_idx:
                    json_content = json_content[start_idx:end_idx]
            
            # Remove common prefixes/suffixes
            json_content = json_content.strip()
            
            # Try to find JSON object boundaries
            if '{' in json_content and '}' in json_content:
                start_brace = json_content.find('{')
                # Find the matching closing brace
                brace_count = 0
                end_brace = -1
                for i in range(start_brace, len(json_content)):
                    if json_content[i] == '{':
                        brace_count += 1
                    elif json_content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_brace = i
                            break
                
                if end_brace > start_brace:
                    json_content = json_content[start_brace:end_brace + 1]
            
            print(f"🧹 Cleaned JSON content (first 200 chars): {json_content[:200]}...")
            
            # Try to parse JSON
            parsed = json.loads(json_content)
            
            # Validate structure
            if isinstance(parsed, dict) and "budget_bands" in parsed and "specs" in parsed:
                print(f"✅ Valid category structure found")
                return parsed
            elif isinstance(parsed, dict) and category_name in parsed:
                print(f"✅ Category found in nested structure")
                return parsed[category_name]
            
            print(f"❌ Unexpected AI response format - missing required fields")
            print(f"📊 Response keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'Not a dict'}")
            return None
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            print(f"📄 Problematic content (first 500 chars): {json_content[:500] if 'json_content' in locals() else text[:500]}")
            
            # Fallback template kaldırıldı - artık None döner
            print(f"❌ JSON parse başarısız, kategori oluşturulamadı: {category_name}")
            return None
            
        except Exception as e:
            print(f"❌ Unexpected parsing error: {e}")
            return None
    
    def _fallback_category_creation(self, category_name):
        """
        AI parsing başarısız olduğunda fallback kategori oluşturur.
        
        Args:
            category_name (str): Kategori adı
            
        Returns:
            None: Fallback template kaldırıldı
        """
        print(f"❌ AI kategori oluşturma başarısız oldu: {category_name}")
        return None
    
    def _load_categories(self):
        """
        Mevcut kategorileri yükler.
        
        Returns:
            dict: Yüklenen kategoriler
        """
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            categories_path = os.path.join(root_dir, self.categories_file)
            
            with open(categories_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_new_category(self, category_name, category_data):
        """
        Yeni kategoriyi categories.json dosyasına kaydeder.
        
        Args:
            category_name (str): Kategori adı
            category_data (dict): Kategori verileri
            
        Returns:
            bool: Kaydetme başarılı mı?
        """
        try:
            categories = self._load_categories()
            categories[category_name] = category_data
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            categories_path = os.path.join(root_dir, self.categories_file)
            
            with open(categories_path, 'w', encoding='utf-8') as f:
                json.dump(categories, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Category '{category_name}' saved successfully with detailed specifications")
            return True
        except Exception as e:
            print(f"❌ Save error: {e}")
            return False
    
# Flask route integration
def add_dynamic_category_route(app):
    """
    Flask uygulamasına dinamik kategori rotaları ekler.
    
    Bu fonksiyon, Flask uygulamasına akıllı kategori tespiti
    için gerekli endpoint'leri ekler.
    
    Args:
        app: Flask uygulama nesnesi
        
    Returns:
        None: Rota'lar uygulamaya eklenir
        
    Örnek:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> add_dynamic_category_route(app)
        >>> # /search/<query> endpoint'i artık mevcut
    """
    category_generator = CategoryGenerator()
    
    @app.route('/search/<query>', methods=['GET'])
    def search_category(query):
        """
        Akıllı kategori tespiti için ana arama endpoint'i.
        
        Bu endpoint, kullanıcı sorgusunu alır ve akıllı kategori
        tespiti yapar. Mevcut kategorilerde eşleşme arar veya
        yeni kategori oluşturur.
        
        Args:
            query (str): Kullanıcı arama sorgusu
            
        Returns:
            dict: Tespit sonucu JSON formatında
        """
        try:
            print(f"🔍 Search request for: '{query}'")
            
            # Use intelligent category detection
            result = category_generator.intelligent_category_detection(query)
            
            # Format response based on match type
            if result['match_type'] in ['exact', 'partial', 'ai_recognition']:
                return {
                    "status": "found",
                    "match_type": result['match_type'],
                    "category": result['category'],
                    "original_query": result.get('original_query', query),
                    "confidence": result.get('confidence', 1.0),
                    "message": f"'{query}' mapped to '{result['category']}'",
                    "data": result['data']
                }
            elif result['match_type'] == 'ai_created':
                return {
                    "status": "created",
                    "category": result['category'],
                    "original_query": result.get('original_query', query),
                    "confidence": result.get('confidence', 0.9),
                    "message": result.get('message', f"New category '{result['category']}' created"),
                    "data": result['data']
                }
            else:
                return {
                    "status": "error",
                    "message": result.get('message', 'Category detection failed')
                }, 500
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return {"status": "error", "message": str(e)}, 500
