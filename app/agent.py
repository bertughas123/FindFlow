"""
FindFlow Agent Modülü

Bu modül, kullanıcı etkileşimlerini yöneten, dinamik soru-cevap akışını kontrol eden
ve AI destekli ürün önerileri oluşturan ana agent sınıfını içerir.

Ana Özellikler:
- Akıllı kategori tespiti (prompt-chained agent mimarisi)
- Dinamik soru-cevap akışı
- Tercih analizi ve güven skoru hesaplama
- AI destekli ürün önerileri (Gemini entegrasyonu)
- Çok dilli destek (Türkçe/İngilizce)
- Bütçe yönetimi
- Bağımlılık tabanlı akış kontrolü

Ana Sınıflar:
- Agent: Ana agent sınıfı, kullanıcı etkileşimlerini yönetir

Ana Fonksiyonlar:
- detect_category_from_query(): Gelişmiş kategori tespiti
- Agent.handle(): Ana işlem fonksiyonu
- Agent._generate_recommendations(): AI öneri oluşturma

Gereksinimler:
- categories.json dosyası
- Gemini API anahtarı
- Flask framework

Kullanım:
    from app.agent import Agent, detect_category_from_query
    
    # Kategori tespiti
    category = detect_category_from_query("telefon")
    
    # Agent kullanımı
    agent = Agent()
    response = agent.handle({
        'step': 0,
        'category': 'Phone',
        'answers': ['Yes', 'No'],
        'language': 'tr'
    })
"""

import json
import os
from .config import setup_gemini, get_gemini_model, generate_with_retry
import json

def detect_category_from_query(query):
    """
    Gelişmiş kategori tespiti - FindFlow prompt-chained agent mimarisi kullanarak
    
    Bu fonksiyon, kullanıcı sorgusunu analiz ederek en uygun ürün kategorisini
    tespit eder. Hem yerel eşleştirme hem de AI destekli tanıma kullanır.
    
    Args:
        query (str): Kullanıcının arama sorgusu (örn: "telefon", "kulaklık")
        
    Returns:
        str or None: Tespit edilen kategori adı veya None (bulunamazsa)
        
    Özellikler:
        - Yerel Türkçe-İngilizce eşleştirme
        - AI destekli kategori tanıma
        - Yeni kategori oluşturma
        - Hata yönetimi ve loglama
        
    Örnek:
        >>> detect_category_from_query("telefon")
        'Phone'
        >>> detect_category_from_query("kulaklık")
        'Headphones'
        >>> detect_category_from_query("bilinmeyen ürün")
        'NewCategory'  # AI tarafından oluşturulur
    """
    try:
        print(f"🔍 Detecting category for query: '{query}'")
        
        # Quick local mapping for common Turkish terms
        # Only include categories that actually exist in categories.json
        local_mappings = {
            'kulaklık': 'Headphones',
            'kulaklik': 'Headphones',
            'headphones': 'Headphones',
            'klima': 'Klima',
            'airconditioner': 'Klima',
            'lastik': 'Tire',
            'tire': 'Tire',
            'televizyon': 'Television',
            'tv': 'Television',
            'television': 'Television',
            # Removed non-existing categories: Phone, Laptop, Mouse, Charger, Drill, Hair Dryer
            # These will be handled by CategoryGenerator AI creation
        }
        
        query_lower = query.strip().lower()
        
        # Check local mappings first
        if query_lower in local_mappings:
            mapped_category = local_mappings[query_lower]
            print(f"✅ Local mapping found: '{query}' → '{mapped_category}'")
            return mapped_category
        
        from .category_generator import CategoryGenerator
        
        # Use the new intelligent category detection system
        category_generator = CategoryGenerator()
        result = category_generator.intelligent_category_detection(query)
        
        # Handle different match types
        if result['match_type'] in ['exact', 'partial', 'ai_recognition']:
            print(f"✅ Category found: {result['match_type']} - '{result['category']}'")
            return result['category']
            
        elif result['match_type'] == 'ai_created':
            print(f"🆕 New category created: '{result['category']}'")
            return result['category']
            
        else:
            print(f"❌ Category detection failed: {result.get('message', 'Unknown error')}")
            # Return None instead of defaulting to prevent confusion
            return None
            
    except Exception as e:
        print(f"❌ Category detection error: {e}")
        import traceback
        print(traceback.format_exc())
        return None

class Agent:
    """
    Ana Agent Sınıfı - Dinamik Soru-Cevap ve AI Öneri Sistemi
    
    Bu sınıf, kullanıcı etkileşimlerini yöneten, dinamik soru-cevap akışını
    kontrol eden ve AI destekli ürün önerileri oluşturan ana agent'tır.
    
    Ana Özellikler:
        - Dinamik soru-cevap akışı
        - Tercih analizi ve güven skoru hesaplama
        - AI destekli ürün önerileri (Gemini entegrasyonu)
        - Çok dilli destek (Türkçe/İngilizce)
        - Bütçe yönetimi ve kategori-spesifik aralıklar
        - Bağımlılık tabanlı akış kontrolü
        - Akıllı follow-up soru belirleme
        
    Ana Metodlar:
        - handle(): Ana işlem fonksiyonu
        - _generate_recommendations(): AI öneri oluşturma
        - _determine_next_followup(): Sonraki soru belirleme
        - _analyze_current_preferences(): Tercih analizi
        
    Kullanım:
        agent = Agent()
        response = agent.handle({
            'step': 0,
            'category': 'Phone',
            'answers': ['Yes', 'No'],
            'language': 'tr'
        })
    """
    
    def __init__(self):
        self.categories = self.load_categories()

    def load_categories(self):
        try:
            with open('categories.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ categories.json dosyası bulunamadı!")
            return {}

    def handle(self, data):
        # Auto-reload categories to pick up manual edits
        self.categories = self.load_categories()
        step = data.get('step', 0)
        category = data.get('category', '')
        answers = data.get('answers', [])
        language = data.get('language', 'en')
        
        print(f"🔄 Agent.handle çağrıldı - Step: {step}, Category: {category}, Answers: {answers}")
        print(f"📊 Raw data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if step == 0:
            # İlk adım: Kategori seçimi
            return {
                'question': 'What tech are you shopping for?' if language == 'en' else 'Hangi teknoloji ürününü arıyorsunuz?',
                'categories': list(self.categories.keys())
            }
        
        elif category:
            # Check if category exists, if not try to create it with CategoryGenerator
            if category not in self.categories:
                print(f"🔍 Category '{category}' not found, attempting to create with AI...")
                from .category_generator import CategoryGenerator
                
                category_generator = CategoryGenerator()
                result = category_generator.intelligent_category_detection(category)
                
                if result['match_type'] == 'ai_created':
                    print(f"🆕 New category '{result['category']}' created successfully!")
                    # Reload categories to include the new one
                    self.categories = self.load_categories()
                    category = result['category']  # Use the AI-determined category name
                elif result['match_type'] in ['exact', 'partial', 'ai_recognition']:
                    print(f"✅ Category mapped to existing: '{result['category']}'")
                    category = result['category']
                else:
                    print(f"❌ Failed to create category: {result.get('message', 'Unknown error')}")
                    return {'error': f"Category '{category}' could not be created or found"}
            
            # Now we should have a valid category
            if category in self.categories:
                specs = self.categories[category]['specs']
                
                # Kullanıcının mevcut tercihlerini analiz et
                preferences = self._analyze_current_preferences(answers, specs)
                
                # Frontend'den gelen özel alanları ekle (budget_band gibi)
                if 'budget_band' in data:
                    preferences['budget_band'] = data['budget_band']
                
                # Hangi sorular soruldu hesapla (step sayısı kadar spec sorulmuş)
                asked_specs = [specs[i]['id'] for i in range(min(step-1, len(specs)))]
                
                confidence_score = self._calculate_confidence_score(preferences, specs)
                
                print(f"🎯 Preferences: {json.dumps(preferences, indent=2, ensure_ascii=False)}")
                print(f"📈 Confidence Score: {confidence_score}")
                print(f"📋 Asked specs so far: {asked_specs}")
                
                # Akıllı follow-up soru belirleme
                next_question = self._determine_next_followup(specs, preferences, confidence_score, language, category, asked_specs)
                
                if next_question:
                    # Progress bilgisi ekle
                    progress = self._calculate_progress(preferences, specs)
                    next_question['progress'] = progress
                    return next_question
                else:
                    # Tüm gerekli bilgiler toplandı, öneri ver
                    return self._generate_recommendations(category, preferences, specs, language)
            else:
                return {'error': f"Category '{category}' could not be processed"}
        
        else:
            print(f"❌ Invalid category or step!")
            print(f"   Step: {step}")
            print(f"   Category: '{category}'")
            print(f"   Category exists in self.categories: {category in self.categories if category else 'N/A'}")
            print(f"   Available categories: {list(self.categories.keys())}")
            return {'error': 'Invalid category or step'}

    def _analyze_current_preferences(self, answers, specs):
        """FindFlow kullanıcı tercihlerini analiz etme"""
        preferences = {}
        
        print(f"🔍 _analyze_current_preferences:")
        print(f"  📊 answers_count={len(answers)}")
        print(f"  📋 specs_count={len(specs)}")
        print(f"  📝 answers={answers}")
        # Fix the budge t_band issue by ensuring proper formatting of spec IDs
        print(f"  🏷️ spec_ids=[{', '.join([spec['id'].strip() for spec in specs])}]")
        
        # answered_specs - sadece cevaplanan spec'leri işle
        for i, answer in enumerate(answers):
            if i < len(specs) and answer is not None:
                spec = specs[i]
                spec_id = spec['id']
                
                print(f"  📋 Processing spec {i}: {spec_id} = '{answer}' (type: {spec['type']})")
                
                if spec['type'] == 'boolean':
                    normalized_answer = answer.lower().strip()
                    if normalized_answer in ['yes', 'evet', 'true', 'evet önemli', 'önemli']:
                        preferences[spec_id] = True
                        print(f"    ✅ Boolean value: True")
                    elif normalized_answer in ['no', 'hayır', 'false', 'önemli değil', 'değil']:
                        preferences[spec_id] = False
                        print(f"    ✅ Boolean value: False")
                    elif normalized_answer in ['no preference', 'fark etmez', 'bilmiyorum', 'farketmez', 'i don\'t know', 'unknown']:
                        preferences[spec_id] = None  # No preference
                        print(f"    ✅ Boolean value: No preference (None)")
                    else:
                        print(f"    ❌ Invalid boolean answer: '{normalized_answer}' - treating as no preference")
                        preferences[spec_id] = None
                elif spec['type'] == 'single_choice':
                    # Seçilen option'ın ID'sini bul
                    option_found = False
                    for opt in spec['options']:
                        if opt['label']['en'] == answer or opt['label']['tr'] == answer:
                            preferences[spec_id] = opt['id']
                            option_found = True
                            print(f"    ✅ Mapped to option_id: {opt['id']}")
                            break
                    
                    # Eğer eşleşme bulunamadıysa, "Bilmiyorum" veya "Fark etmez" benzeri cevapları kontrol et
                    if not option_found:
                        normalized_answer = answer.lower().strip()
                        if normalized_answer in ['bilmiyorum', 'i don\'t know', 'unknown', 'dont know']:
                            # "unknown" veya "no_preference" option_id'si varsa kullan
                            for opt in spec['options']:
                                if opt['id'] in ['unknown', 'no_preference']:
                                    preferences[spec_id] = opt['id']
                                    option_found = True
                                    print(f"    ✅ Mapped 'Bilmiyorum' to option_id: {opt['id']}")
                                    break
                            # Eğer hiçbir option bulunmadıysa, null olarak set et (cevaplandı ama bilmiyor)
                            if not option_found:
                                preferences[spec_id] = None
                                option_found = True
                                print(f"    ✅ Mapped 'Bilmiyorum' to null (answered but unknown)")
                        elif normalized_answer in ['fark etmez', 'farketmez', 'no preference', 'doesnt matter']:
                            # "no_preference" option_id'si varsa kullan
                            for opt in spec['options']:
                                if opt['id'] == 'no_preference':
                                    preferences[spec_id] = opt['id']
                                    option_found = True
                                    print(f"    ✅ Mapped 'Fark etmez' to option_id: {opt['id']}")
                                    break
                            # Eğer no_preference option'ı yoksa, null olarak set et
                            if not option_found:
                                preferences[spec_id] = None
                                option_found = True
                                print(f"    ✅ Mapped 'Fark etmez' to null (answered but no preference)")
                    
                    if not option_found:
                        print(f"    ❌ No option found for answer: '{answer}'")
                elif spec['type'] == 'number':
                    try:
                        preferences[spec_id] = int(answer)
                        print(f"    ✅ Converted to number: {int(answer)}")
                    except ValueError:
                        preferences[spec_id] = None
                        print(f"    ❌ Could not convert to number: '{answer}'")
        
        # Özel bütçe kontrolü - Para birimi sembolü içeren yanıtları bütçe olarak tanı
        for i, answer in enumerate(answers):
            if answer and ('$' in answer or '₺' in answer):
                preferences['budget_band'] = answer
                print(f"  💰 Special budget detection: '{answer}' added as budget_band")
                
                # Bu bir spec cevabı olarak işlendiyse, bu spec'i null olarak işaretle
                if i < len(specs):
                    spec_id = specs[i]['id']
                    if spec_id in preferences and spec_id != 'budget_band':
                        preferences[spec_id] = None
                        print(f"  ⚠️ Clearing {spec_id} since this was actually a budget answer")
        
        print(f"  🎯 Final preferences: {json.dumps(preferences, indent=2, ensure_ascii=False)}")
        return preferences

    def _has_unsatisfied_dependencies(self, spec, preferences):
        """Spec'in dependency'leri sağlanmıyor mu kontrol et"""
        if 'depends_on' not in spec:
            print(f"  👍 No dependencies for {spec['id']}")
            return False
            
        print(f"  🔍 Checking dependencies for {spec['id']}: {spec.get('depends_on')}")
        
        for dep in spec['depends_on']:
            dep_id = dep['id']
            expected_value = dep['eq']
            
            if dep_id not in preferences:
                print(f"  ❌ Dependency {dep_id} not answered")
                return True  # Dependency cevaplanmamış
                
            actual_value = preferences[dep_id]
            print(f"  ⚙️ Dependency check: {dep_id}={actual_value}, expected={expected_value}")
            
            # No preference varsa dependency sağlanmıyor
            if actual_value == "no_preference" or actual_value is None:
                print(f"  ❌ Dependency value is 'no_preference' or None")
                return True
                
            # String/bool karşılaştırma için fix
            if isinstance(expected_value, bool) and isinstance(actual_value, str):
                # String to boolean conversion
                if actual_value.lower() in ['true', 'yes', 'evet']:
                    actual_value = True
                elif actual_value.lower() in ['false', 'no', 'hayır']:
                    actual_value = False
            
            if actual_value != expected_value:
                print(f"  ❌ Dependency value doesn't match: {actual_value} != {expected_value}")
                return True  # Dependency sağlanmıyor
        
        print(f"  ✅ All dependencies satisfied for {spec['id']}")
        return False  # Tüm dependency'ler sağlanıyor

    def _calculate_confidence_score(self, preferences, specs):
        """Toplam güven skorunu hesapla (weight'lere göre)"""
        total_weight = sum(spec.get('weight', 1.0) for spec in specs)
        answered_weight = sum(
            spec.get('weight', 1.0) 
            for spec in specs 
            if spec['id'] in preferences  # None da valid bir cevap sayılır
        )
        
        return answered_weight / total_weight if total_weight > 0 else 0

    def _calculate_progress(self, preferences, specs):
        """İlerleme yüzdesini hesapla"""
        answered_count = len([spec_id for spec_id in [spec['id'] for spec in specs] if spec_id in preferences])
        total_count = len(specs)
        return int((answered_count / total_count) * 100) if total_count > 0 else 0

    def _determine_next_followup(self, specs, preferences, confidence_score, language, category=None, asked_specs=None):
        """FindFlow akıllı follow-up soru belirleme algoritması"""
        
        if asked_specs is None:
            asked_specs = []
        
        print(f"🔍 Next question logic: confidence={confidence_score:.2f}, asked_specs={asked_specs}")
        
        # 1) Çelişki var mı kontrol et
        conflict_question = self._check_conflicts(specs, preferences, language)
        if conflict_question:
            return conflict_question
        
        # 2) Zorunlu/önemli eksikler (mandatory veya weight ≥ 0.9)
        mandatory_question = self._check_mandatory_missing(specs, preferences, language, asked_specs)
        if mandatory_question:
            return mandatory_question
        
        # 3) depends_on tetiklenen alt sorular
        dependency_question = self._check_dependency_triggers(specs, preferences, language, asked_specs)
        if dependency_question:
            return dependency_question
        
        # 4) Skor düşükse (bilgi yetersiz), yüksek weight'li eksikler
        # ANCAK budget sorulduysa bu adımı atla (yeteri kadar bilgi var demektir)
        if confidence_score < 0.7 and 'budget_band' not in preferences:
            high_weight_question = self._check_high_weight_missing(specs, preferences, language, asked_specs)
            if high_weight_question:
                return high_weight_question
        
        # 5) Sayısal detay gereken sorular
        numeric_question = self._check_numeric_needed(specs, preferences, language, asked_specs)
        if numeric_question:
            return numeric_question
        
        # 6) Bütçe sor (eğer yoksa) - kategori bilgisi ile
        budget_question = self._check_budget_needed(preferences, language, category)
        if budget_question:
            return budget_question
        
        return None  # Artık öneriye geç
    """
    BURAYA TEKRAR BAKALIM
    """
    def _check_conflicts(self, specs, preferences, language):
        """Çelişki kontrolü"""
        # Örnek: aynı kategoride farklı seçimler
        # Bu basit örnek, daha karmaşık çelişki mantığı eklenebilir
        return None

    def _check_mandatory_missing(self, specs, preferences, language, asked_specs=None):
        """Zorunlu veya çok önemli (weight≥0.9) eksik sorular"""
        if asked_specs is None:
            asked_specs = []
            
        missing = [
            spec for spec in specs 
            if (spec.get('weight', 1.0) >= 0.9 or spec.get('mandatory', False)) 
            and spec['id'] not in preferences
            and spec['id'] not in asked_specs  # Bu satır eklendi - zaten sorulmuş soruları atla
            and not self._has_unsatisfied_dependencies(spec, preferences)  # Dependency'si olmayan veya sağlanan sorular
        ]
        
        print(f"  🎯 Mandatory check: found {len(missing)} missing mandatory specs")
        
        if missing:
            return self._format_question(missing[0], language, reason="mandatory")
        return None

    def _check_dependency_triggers(self, specs, preferences, language, asked_specs=None):
        """Bağımlılık tetikleyen sorular"""
        if asked_specs is None:
            asked_specs = []
            
        for spec in specs:
            if spec['id'] not in preferences and spec['id'] not in asked_specs and 'depends_on' in spec:
                # Dependency koşulları sağlanıyor mu?
                should_ask = True
                for dep in spec['depends_on']:
                    dep_id = dep['id']
                    expected_value = dep['eq']
                    
                    if dep_id not in preferences:
                        should_ask = False
                        break
                    
                    actual_value = preferences[dep_id]
                    
                    # No preference varsa dependency'yi atla
                    if actual_value == "no_preference" or actual_value is None:
                        should_ask = False
                        break
                        
                    if actual_value != expected_value:
                        should_ask = False
                        break
                
                if should_ask:
                    print(f"  🔗 Dependency triggered for {spec['id']}: {spec['depends_on']}")
                    return self._format_question(spec, language, reason="dependency")
        
        return None

    def _check_high_weight_missing(self, specs, preferences, language, asked_specs=None):
        """Yüksek önemde ama henüz cevaplanmamış sorular"""
        if asked_specs is None:
            asked_specs = []
        
        # Budget sorulduysa weight threshold'u daha yüksek yap (sadece çok kritik olanlar)
        threshold = 0.9 if 'budget_band' in preferences else 0.6
        
        missing = [
            spec for spec in specs 
            if spec.get('weight', 1.0) >= threshold 
            and spec['id'] not in preferences
            and spec['id'] not in asked_specs  # Bu satır eklendi - zaten sorulmuş soruları atla
            and not self._has_unsatisfied_dependencies(spec, preferences)  # Dependency'si sağlanan sorular
        ]
        
        print(f"  📈 High weight check: threshold={threshold}, missing_count={len(missing)}")
        
        # En yüksek weight'li olanı seç
        if missing:
            missing.sort(key=lambda x: x.get('weight', 1.0), reverse=True)
            print(f"    🎯 Will ask: {missing[0]['id']} (weight: {missing[0].get('weight', 1.0)})")
            return self._format_question(missing[0], language, reason="importance")
        return None

    def _check_numeric_needed(self, specs, preferences, language, asked_specs=None):
        """Sayısal detay gereken sorular"""
        if asked_specs is None:
            asked_specs = []
        
        # Budget sorulduysa sayısal soruları atla (çok kritik olanlar hariç)
        if 'budget_band' in preferences:
            print(f"  🔢 Numeric check: Budget exists, skipping numeric questions")
            return None
            
        numeric_missing = [
            spec for spec in specs 
            if spec['type'] == 'number' 
            and spec['id'] not in preferences
            and spec['id'] not in asked_specs  # Bu satır eklendi - zaten sorulmuş soruları atla
            and not self._has_unsatisfied_dependencies(spec, preferences)  # BU SATIR EKLENDİ
        ]
        
        print(f"  🔢 Numeric check: found {len(numeric_missing)} missing numeric specs")
        
        if numeric_missing:
            return self._format_question(numeric_missing[0], language, reason="quantification")
        return None

    def _check_budget_needed(self, preferences, language, category=None):
        """Bütçe bilgisi gerekli mi? - Kategori-spesifik bütçe aralıkları"""
        print(f"💰 _check_budget_needed: budget_band in preferences? {'budget_band' in preferences}")
        
        if 'budget_band' in preferences:
            print(f"  ✅ Budget already set: {preferences['budget_band']}")
            return None
        
        print(f"  ❌ Budget missing, will ask for it")
        
        # Kategori-spesifik bütçe aralıkları
        budget_ranges = self._get_category_budget_ranges(category, language)
        
        # Ensure ID is always correctly formatted without spaces
        return {
            'id': 'budget_band', # Consistent ID without spaces
            'type': 'single_choice',
            'question': 'What\'s your budget range?' if language == 'en' else 'Bütçe aralığın nedir?',
            'emoji': '💰',
            'options': budget_ranges,
            'reason': 'budget',
            'tooltip': 'This helps me recommend products in your price range' if language == 'en' 
                      else 'Bu, fiyat aralığınıza uygun ürünler önermeme yardımcı olur'
        }

    def _get_category_budget_ranges(self, category, language):
        """Kategori-spesifik bütçe aralıklarını döndür"""
        
        if category and category in self.categories:
            # categories.json'dan direkt olarak al
            if "budget_bands" in self.categories[category]:
                return self.categories[category]["budget_bands"].get(language, 
                       self.categories[category]["budget_bands"]["en"])
        
        # Fallback: Genel elektronik bütçesi
        default_budgets = {
            'tr': ['1-3k₺', '3-7k₺', '7-15k₺', '15-30k₺', '30k₺+'],
            'en': ['$30-100', '$100-200', '$200-500', '$500-1000', '$1000+']
        }
        
        return default_budgets.get(language, default_budgets["en"])

    def _should_show_spec(self, spec, answers, previous_specs):
        """Spec'in gösterilip gösterilmeyeceğini dependency'lere göre kontrol et"""
        if 'depends_on' not in spec:
            return True
        
        for dependency in spec['depends_on']:
            dep_id = dependency['id']
            expected_value = dependency['eq']
            
            # Önceki spec'lerde bu ID'yi bul
            dep_spec_index = None
            for i, prev_spec in enumerate(previous_specs):
                if prev_spec['id'] == dep_id:
                    dep_spec_index = i
                    break
            
            if dep_spec_index is None or dep_spec_index >= len(answers):
                return False
            
            actual_answer = answers[dep_spec_index]
            
            # Boolean type için
            if previous_specs[dep_spec_index]['type'] == 'boolean':
                if (expected_value and actual_answer != 'Yes') or (not expected_value and actual_answer != 'No'):
                    return False
            # Single choice için
            elif previous_specs[dep_spec_index]['type'] == 'single_choice':
                # Option ID'sini bul
                selected_option_id = None
                for opt in previous_specs[dep_spec_index]['options']:
                    if opt['label']['en'] == actual_answer or opt['label']['tr'] == actual_answer:
                        selected_option_id = opt['id']
                        break
                if selected_option_id != expected_value:
                    return False
            # String değerler için
            elif actual_answer != expected_value:
                return False
        
        return True

    def _format_question(self, spec, language, reason=None):
        """Spec'i soru formatına çevir"""
        question_data = {
            'question': spec['label'][language],
            'emoji': spec.get('emoji', ''),
            'type': spec['type'],
            'id': spec['id']
        }
        
        # Spec'e özgü tooltip ekle
        if 'tooltip' in spec and language in spec['tooltip']:
            question_data['tooltip'] = spec['tooltip'][language]
    
        # Soru sorma nedenine göre tooltip ekle (eğer spec'te yoksa)
        elif reason:
            tooltips = {
                'mandatory': {
                    'en': 'This is essential for good recommendations',
                    'tr': 'Bu iyi öneriler için gerekli'
                },
                'dependency': {
                    'en': 'Based on your previous answer',
                    'tr': 'Önceki cevabınıza göre'
                },
                'importance': {
                    'en': 'This significantly affects your options',
                    'tr': 'Bu seçeneklerinizi önemli ölçüde etkiler'
                },
                'quantification': {
                    'en': 'Need specific numbers for precise recommendations',
                    'tr': 'Kesin öneriler için sayısal değer gerekli'
                }
            }
            question_data['tooltip'] = tooltips.get(reason, {}).get(language, '')
        
        if spec['type'] == 'boolean':
            question_data['options'] = ['Yes', 'No', 'No preference'] if language == 'en' else ['Evet', 'Hayır', 'Farketmez']
        
        elif spec['type'] == 'single_choice':
            options = [opt['label'][language] for opt in spec['options']]
            # "Bilmiyorum" seçeneği ekle
            options.append('Not sure' if language == 'en' else 'Bilmiyorum')
            question_data['options'] = options
        
        elif spec['type'] == 'number':
            question_data['min'] = spec.get('min', 0)
            question_data['max'] = spec.get('max', 100)
            question_data['placeholder'] = f"Enter a number between {spec.get('min', 0)} and {spec.get('max', 100)}"
        
        return question_data

    def _generate_recommendations(self, category, preferences, specs, language):
        """FindFlow Modern Search Engine kullanarak öneri oluşturma - fallback sistemi ile"""
        try:
            print(f"🚀 Modern Search Engine ile öneri oluşturuluyor: {category}")
            
            # Modern search sistemi için tercihleri hazırla
            search_preferences = self._prepare_search_preferences(category, preferences, language)
            
            # Modern Search Engine'i başlat
            from .search_engine import ModernSearchEngine
            search_engine = ModernSearchEngine()
            
            # Ürün arama yap
            search_results = search_engine.search_products(search_preferences)
            
            if search_results['status'] == 'success' and search_results.get('recommendations'):
                print(f"✅ Modern search engine başarılı, {len(search_results['recommendations'])} öneri döndü")
                
                # Budget filtreleme uygula
                filtered_recommendations = self._filter_recommendations_by_budget(
                    search_results['recommendations'], 
                    preferences, 
                    category
                )
                
                print(f"💰 Budget filtreleme sonrası: {len(filtered_recommendations)} öneri kaldı")
                
                # Eğer budget filtreleme sonrası hiç ürün yoksa fallback'e geç
                if not filtered_recommendations:
                    print(f"⚠️ Budget filtreleme sonrası hiç ürün kalmadı, fallback'e geçiliyor")
                    fallback_recommendations = self._get_fallback_recommendations(category, preferences, language)
                    return {
                        'type': 'fallback_recommendation',
                        'message': f'Seçtiğiniz bütçe aralığında ürün bulunamadı. Size benzer ürünler öneriyoruz.',
                        'recommendations': fallback_recommendations,
                        'category': category,
                        'preferences': preferences,
                        'confidence_score': self._calculate_confidence_score(preferences, specs),
                        'budget_filter_applied': True
                    }
                
                response_data = {
                    'type': 'modern_recommendation',
                    'grounding_results': search_results.get('grounding_results', []),
                    'shopping_results': search_results.get('shopping_results', []),
                    'sources': search_results.get('sources', []),
                    'recommendations': filtered_recommendations,
                    'category': category,
                    'preferences': preferences,
                    'confidence_score': self._calculate_confidence_score(preferences, specs),
                    'budget_filter_applied': True,
                    'original_count': len(search_results['recommendations']),
                    'filtered_count': len(filtered_recommendations)
                }
                
                print(f"🎯 Response data keys: {list(response_data.keys())}")
                print(f"📊 Recommendations count in response: {len(response_data['recommendations'])}")
                print(f"📦 First recommendation preview: {response_data['recommendations'][0] if response_data['recommendations'] else 'None'}")
                
                return response_data
            else:
                print(f"⚠️ Modern search engine başarısız veya boş sonuç, fallback'e geçiliyor")
                fallback_recommendations = self._get_fallback_recommendations(category, preferences, language)
                return {
                    'type': 'fallback_recommendation',
                    'message': 'Arama sistemi geçici olarak sınırlı, önerilerimizi sunuyoruz',
                    'recommendations': fallback_recommendations,
                    'category': category,
                    'preferences': preferences,
                    'confidence_score': self._calculate_confidence_score(preferences, specs)
                }
            
        except Exception as e:
            print(f"❌ Modern search engine hatası: {e}")
            print(f"🔄 Fallback önerilerine geçiliyor...")
            fallback_recommendations = self._get_fallback_recommendations(category, preferences, language)
            return {
                'type': 'fallback_recommendation',
                'message': 'Arama sistemi geçici olarak kullanılamıyor, güvenilir önerilerimizi sunuyoruz',
                'recommendations': fallback_recommendations,
                'category': category,
                'preferences': preferences,
                'confidence_score': self._calculate_confidence_score(preferences, specs),
                'fallback_reason': str(e)
            }
    
    def _filter_recommendations_by_budget(self, recommendations, preferences, category):
        """Önerileri kullanıcının bütçe aralığına göre filtrele"""
        try:
            budget_min, budget_max = self._extract_budget_range(preferences)
            
            if not budget_min and not budget_max:
                print("💰 Budget aralığı yok, filtreleme yapılmayacak")
                return recommendations
            
            print(f"💰 Budget filtreleme: {budget_min} - {budget_max} TL")
            
            filtered = []
            for rec in recommendations:
                try:
                    # Fiyat bilgisini çıkar
                    price_value = None
                    
                    if 'price' in rec:
                        if isinstance(rec['price'], dict):
                            price_value = rec['price'].get('value')
                        elif isinstance(rec['price'], (int, float)):
                            price_value = rec['price']
                        elif isinstance(rec['price'], str):
                            # String fiyat parse et
                            import re
                            price_match = re.search(r'(\d+(?:\.\d+)?)', rec['price'].replace('.', '').replace(',', ''))
                            if price_match:
                                price_value = float(price_match.group(1))
                    
                    if price_value is None:
                        print(f"⚠️ Fiyat bilgisi bulunamadı: {rec.get('title', 'Unknown')}")
                        continue
                    
                    # Budget kontrolü
                    price_in_range = True
                    
                    if budget_min and price_value < budget_min:
                        price_in_range = False
                        print(f"❌ {rec.get('title', 'Unknown')}: {price_value} TL < {budget_min} TL (minimum)")
                    
                    if budget_max and price_value > budget_max:
                        price_in_range = False
                        print(f"❌ {rec.get('title', 'Unknown')}: {price_value} TL > {budget_max} TL (maximum)")
                    
                    if price_in_range:
                        print(f"✅ {rec.get('title', 'Unknown')}: {price_value} TL - Bütçe aralığında")
                        filtered.append(rec)
                    
                except Exception as e:
                    print(f"⚠️ Fiyat filtreleme hatası {rec.get('title', 'Unknown')}: {e}")
                    # Hata durumunda ürünü dahil et
                    filtered.append(rec)
            
            print(f"💰 Filtreleme tamamlandı: {len(recommendations)} -> {len(filtered)} ürün")
            return filtered
            
        except Exception as e:
            print(f"❌ Budget filtreleme genel hatası: {e}")
            return recommendations

    def _prepare_search_preferences(self, category, preferences, language):
        """Preferences'ları modern search sistemi için hazırla"""
        # Budget bilgisini çıkar
        budget_min, budget_max = self._extract_budget_range(preferences)
        
        # Özellikleri çıkar
        features = []
        for pref_id, value in preferences.items():
            if pref_id != 'budget_band' and value and value not in ['Bilmiyorum', 'Not sure', 'Farketmez', 'No preference']:
                if isinstance(value, bool):
                    if value:  # Sadece True olan özellikleri ekle
                        features.append(pref_id.replace('_', ' '))
                elif isinstance(value, str):
                    features.append(value)
        
        return {
            'category': category,
            'budget_min': budget_min,
            'budget_max': budget_max,
            'features': features,
            'language': language
        }
    
    def _extract_budget_range(self, preferences):
        """Budget aralığını çıkar - 'k' formatını da destekler"""
        budget_band = preferences.get('budget_band', '')
        
        if not budget_band:
            return None, None
        
        print(f"🔍 Budget band parsing: '{budget_band}'")
        
        # "2-5k₺", "20-40k₺" formatını parse et
        import re
        
        # 'k' formatını kontrol et
        if 'k' in budget_band.lower():
            # "20-40k₺" -> [20000, 40000]  
            k_pattern = r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)k'
            k_match = re.search(k_pattern, budget_band.lower())
            
            if k_match:
                min_val = int(float(k_match.group(1)) * 1000)
                max_val = int(float(k_match.group(2)) * 1000)
                print(f"✅ K format parsed: {min_val} - {max_val}")
                return min_val, max_val
            
            # Tek k değeri "40k₺+" formatı
            single_k = re.search(r'(\d+(?:\.\d+)?)k', budget_band.lower())
            if single_k:
                base_value = int(float(single_k.group(1)) * 1000)
                if '+' in budget_band:
                    print(f"✅ K+ format parsed: {base_value} - {base_value * 2}")
                    return base_value, base_value * 2
                else:
                    print(f"✅ K max format parsed: None - {base_value}")
                    return None, base_value
        
        # Normal format "500-1000₺" veya "15.000-40.000₺"
        # Türkçe binlik ayırıcı noktaları da destekle
        normal_pattern = r'([\d.]+)\s*-\s*([\d.]+)'
        normal_match = re.search(normal_pattern, budget_band)
        
        if normal_match:
            # Binlik ayırıcı noktaları kaldır (15.000 -> 15000)
            min_str = normal_match.group(1).replace('.', '') if normal_match.group(1).count('.') > 0 and not normal_match.group(1).endswith('.') else normal_match.group(1)
            max_str = normal_match.group(2).replace('.', '') if normal_match.group(2).count('.') > 0 and not normal_match.group(2).endswith('.') else normal_match.group(2)
            
            min_val = int(float(min_str))
            max_val = int(float(max_str))
            print(f"✅ Normal format parsed: {min_val} - {max_val}")
            return min_val, max_val
        
        # Tek değer - binlik ayırıcı noktaları da destekle
        single_match = re.search(r'([\d.]+)', budget_band)
        if single_match:
            # Binlik ayırıcı noktaları kaldır
            value_str = single_match.group(1).replace('.', '') if single_match.group(1).count('.') > 0 and not single_match.group(1).endswith('.') else single_match.group(1)
            value = int(float(value_str))
            if '+' in budget_band:
                print(f"✅ Single+ format parsed: {value} - {value * 2}")
                return value, value * 2
            else:
                print(f"✅ Single format parsed: None - {value}")
                return None, value
        
        print(f"❌ Budget parsing failed for: '{budget_band}'")
        return None, None
    
    def _get_fallback_recommendations(self, category, preferences, language):
        """Fallback öneriler - doğru çalışan linklerle"""
        
        # Bütçe bilgisini al
        budget_min, budget_max = self._extract_budget_range(preferences)
        
        if category == 'Drone':
            return [
                {
                    'title': 'DJI Mini 3',
                    'price': {'value': min(budget_max or 15000, 15000), 'currency': 'TRY', 'display': f'{min(budget_max or 15000, 15000):.0f} ₺'},
                    'features': ['4K Kamera', '38 Dakika Uçuş', 'Katlanabilir Tasarım', 'GPS'],
                    'pros': ['Güvenilir marka', 'Uzun uçuş süresi', 'Kompakt taşınabilir'],
                    'cons': ['Yüksek fiyat', 'Rüzgara hassas'],
                    'match_score': 90,
                    'source_site': 'hepsiburada.com',
                    'product_url': 'https://www.hepsiburada.com/ara?q=dji+mini+3+drone',
                    'link_status': 'fallback',
                    'link_message': 'Hepsiburada arama sayfası',
                    'why_recommended': 'Başlangıç seviyesi için mükemmel drone'
                },
                {
                    'title': 'DJI Air 2S',
                    'price': {'value': min(budget_max or 25000, 25000), 'currency': 'TRY', 'display': f'{min(budget_max or 25000, 25000):.0f} ₺'},
                    'features': ['5.4K Video', '31 Dakika Uçuş', 'Engel Algılama', '1 inch Sensör'],
                    'pros': ['Profesyonel kalite', 'Güçlü özellikler', 'İleri seviye kamera'],
                    'cons': ['Pahalı', 'Ağır'],
                    'match_score': 85,
                    'source_site': 'teknosa.com',
                    'product_url': 'https://www.teknosa.com/arama?q=dji+air+2s+drone',
                    'link_status': 'fallback',
                    'link_message': 'Teknosa arama sayfası',
                    'why_recommended': 'Profesyonel çekimler için ideal'
                },
                {
                    'title': 'Hubsan H117S Zino',
                    'price': {'value': min(budget_max or 8000, 8000), 'currency': 'TRY', 'display': f'{min(budget_max or 8000, 8000):.0f} ₺'},
                    'features': ['4K Kamera', '23 Dakika Uçuş', '1km Menzil', 'GPS Return'],
                    'pros': ['Uygun fiyat', 'İyi kamera', 'Kolay kullanım'],
                    'cons': ['Daha kısa uçuş süresi', 'Sınırlı özellikler'],
                    'match_score': 75,
                    'source_site': 'trendyol.com',
                    'product_url': 'https://www.trendyol.com/sr?q=hubsan+zino+drone',
                    'link_status': 'fallback',
                    'link_message': 'Trendyol arama sayfası',
                    'why_recommended': 'Bütçe dostu seçenek'
                }
            ]
        
        elif category == 'Phone':
            return [
                {
                    'title': 'Samsung Galaxy A54 5G 128GB',
                    'price': {'value': min(budget_max or 15000, 15000), 'currency': 'TRY', 'display': f'{min(budget_max or 15000, 15000):.0f} ₺'},
                    'features': ['5G Destekli', '128GB Depolama', '50MP Kamera', '5000mAh Pil'],
                    'pros': ['Güvenilir marka', 'Uzun pil ömrü', 'İyi kamera'],
                    'cons': ['Orta segment işlemci'],
                    'match_score': 80,
                    'source_site': 'hepsiburada.com',
                    'product_url': 'https://www.hepsiburada.com/ara?q=samsung+galaxy+a54+5g',
                    'link_status': 'fallback',
                    'link_message': 'Hepsiburada arama sayfası',
                    'why_recommended': 'Güvenilir orta segment telefon'
                },
                {
                    'title': 'Xiaomi Redmi Note 12 256GB',
                    'price': {'value': min(budget_max or 10000, 10000), 'currency': 'TRY', 'display': f'{min(budget_max or 10000, 10000):.0f} ₺'},
                    'features': ['256GB Depolama', '48MP Kamera', '5000mAh Pil', 'Hızlı Şarj'],
                    'pros': ['Büyük depolama', 'Uygun fiyat', 'Hızlı şarj'],
                    'cons': ['MIUI arayüzü'],
                    'match_score': 75,
                    'source_site': 'trendyol.com',
                    'product_url': 'https://www.trendyol.com/sr?q=xiaomi+redmi+note+12+256gb',
                    'link_status': 'fallback',
                    'link_message': 'Trendyol arama sayfası',
                    'why_recommended': 'Fiyat/performans odaklı seçim'
                },
                {
                    'title': 'iPhone 13 128GB (Yenilenmiş)',
                    'price': {'value': min(budget_max or 20000, 20000), 'currency': 'TRY', 'display': f'{min(budget_max or 20000, 20000):.0f} ₺'},
                    'features': ['A15 Bionic Chip', '128GB Depolama', 'Dual Kamera', 'Face ID'],
                    'pros': ['iOS ekosistemi', 'Premium yapı', 'Uzun destek'],
                    'cons': ['Yenilenmiş ürün', 'Yüksek fiyat'],
                    'match_score': 85,
                    'source_site': 'teknosa.com',
                    'product_url': 'https://www.teknosa.com/arama?q=iphone+13+128gb',
                    'link_status': 'fallback',
                    'link_message': 'Teknosa arama sayfası',
                    'why_recommended': 'Apple kullanıcıları için uygun seçenek'
                }
            ]
        
        elif category == 'Headphones':
            return [
                {
                    'title': 'Sony WH-1000XM5',
                    'price': {'value': min(budget_max or 12000, 12000), 'currency': 'TRY', 'display': f'{min(budget_max or 12000, 12000):.0f} ₺'},
                    'features': ['Üst Seviye ANC', '30 Saat Pil', 'Kablosuz', 'Premium Ses'],
                    'pros': ['Mükemmel ses kalitesi', 'Güçlü gürültü engelleme', 'Konforlu'],
                    'cons': ['Pahalı', 'Büyük boyut'],
                    'match_score': 90,
                    'source_site': 'hepsiburada.com',
                    'product_url': 'https://www.hepsiburada.com/ara?q=sony+wh-1000xm5',
                    'link_status': 'fallback',
                    'link_message': 'Hepsiburada arama sayfası',
                    'why_recommended': 'Premium ses deneyimi için ideal'
                },
                {
                    'title': 'Apple AirPods Pro 2',
                    'price': {'value': min(budget_max or 8000, 8000), 'currency': 'TRY', 'display': f'{min(budget_max or 8000, 8000):.0f} ₺'},
                    'features': ['Uzamsal Ses', 'ANC', 'İOS Entegrasyonu', 'Kablosuz Şarj'],
                    'pros': ['Apple ekosistemi', 'Kompakt tasarım', 'İyi ANC'],
                    'cons': ['İOS odaklı', 'Pahalı'],
                    'match_score': 85,
                    'source_site': 'teknosa.com',
                    'product_url': 'https://www.teknosa.com/arama?q=apple+airpods+pro+2',
                    'link_status': 'fallback',
                    'link_message': 'Teknosa arama sayfası',
                    'why_recommended': 'Apple kullanıcıları için mükemmel'
                },
                {
                    'title': 'JBL Tune 770NC',
                    'price': {'value': min(budget_max or 3000, 3000), 'currency': 'TRY', 'display': f'{min(budget_max or 3000, 3000):.0f} ₺'},
                    'features': ['ANC', 'Bluetooth', '70 Saat Pil', 'Hızlı Şarj'],
                    'pros': ['Uygun fiyat', 'Uzun pil ömrü', 'İyi ses'],
                    'cons': ['Orta seviye build quality'],
                    'match_score': 75,
                    'source_site': 'trendyol.com',
                    'product_url': 'https://www.trendyol.com/sr?q=jbl+tune+770nc',
                    'link_status': 'fallback',
                    'link_message': 'Trendyol arama sayfası',
                    'why_recommended': 'Bütçe dostu ANC kulaklık'
                }
            ]

        elif category == 'Klima':
            return [
                {
                    'title': 'Daikin FTXM35R Comfora',
                    'price': {'value': min(budget_max or 25000, 25000), 'currency': 'TRY', 'display': f'{min(budget_max or 25000, 25000):.0f} ₺'},
                    'features': ['Inverter', 'A++ Enerji', '12.000 BTU', 'R32 Gaz'],
                    'pros': ['Güvenilir marka', 'Sessiz çalışma', 'Enerji tasarrufu'],
                    'cons': ['Yüksek fiyat', 'Kurulum gerekli'],
                    'match_score': 90,
                    'source_site': 'hepsiburada.com',
                    'product_url': 'https://www.hepsiburada.com/ara?q=daikin+comfora+klima',
                    'link_status': 'fallback',
                    'link_message': 'Hepsiburada arama sayfası',
                    'why_recommended': 'Premium kalite ve enerji tasarrufu'
                },
                {
                    'title': 'Mitsubishi MSZ-HR25VF',
                    'price': {'value': min(budget_max or 20000, 20000), 'currency': 'TRY', 'display': f'{min(budget_max or 20000, 20000):.0f} ₺'},
                    'features': ['Inverter', 'Wi-Fi', '9.000 BTU', 'Plasma Quad Plus'],
                    'pros': ['Japon teknolojisi', 'Akıllı özellikler', 'Güçlü soğutma'],
                    'cons': ['Pahalı servis', 'Karmaşık kumanda'],
                    'match_score': 85,
                    'source_site': 'teknosa.com',
                    'product_url': 'https://www.teknosa.com/arama?q=mitsubishi+klima',
                    'link_status': 'fallback',
                    'link_message': 'Teknosa arama sayfası',
                    'why_recommended': 'Teknoloji ve kalite odaklı'
                },
                {
                    'title': 'Arçelik Inverter 12570 EI',
                    'price': {'value': min(budget_max or 15000, 15000), 'currency': 'TRY', 'display': f'{min(budget_max or 15000, 15000):.0f} ₺'},
                    'features': ['Inverter', 'A+ Enerji', '12.000 BTU', '10 Yıl Garanti'],
                    'pros': ['Türk markası', 'Uygun fiyat', 'Yaygın servis'],
                    'cons': ['Daha az özellik', 'Ses seviyesi'],
                    'match_score': 75,
                    'source_site': 'trendyol.com',
                    'product_url': 'https://www.trendyol.com/sr?q=arcelik+inverter+klima',
                    'link_status': 'fallback',
                    'link_message': 'Trendyol arama sayfası',
                    'why_recommended': 'Yerli üretim güvenilir seçenek'
                }
            ]

        elif category == 'Television':
            return [
                {
                    'title': 'Samsung 55" QN90C Neo QLED',
                    'price': {'value': min(budget_max or 40000, 40000), 'currency': 'TRY', 'display': f'{min(budget_max or 40000, 40000):.0f} ₺'},
                    'features': ['4K', 'Neo QLED', 'Quantum Matrix', 'Tizen OS'],
                    'pros': ['Mükemmel görüntü', 'Akıllı özellikler', 'Premium tasarım'],
                    'cons': ['Pahalı', 'Karmaşık menüler'],
                    'match_score': 90,
                    'source_site': 'hepsiburada.com',
                    'product_url': 'https://www.hepsiburada.com/ara?q=samsung+55+qn90c+neo+qled',
                    'link_status': 'fallback',
                    'link_message': 'Hepsiburada arama sayfası',
                    'why_recommended': 'Premium görüntü kalitesi'
                },
                {
                    'title': 'LG 55" C3 OLED evo',
                    'price': {'value': min(budget_max or 35000, 35000), 'currency': 'TRY', 'display': f'{min(budget_max or 35000, 35000):.0f} ₺'},
                    'features': ['4K OLED', 'WebOS', 'Dolby Vision', '120Hz'],
                    'pros': ['OLED teknolojisi', 'Sinema kalitesi', 'Gaming desteği'],
                    'cons': ['Burn-in riski', 'Parlak ortamlarda sorun'],
                    'match_score': 85,
                    'source_site': 'teknosa.com',
                    'product_url': 'https://www.teknosa.com/arama?q=lg+55+c3+oled',
                    'link_status': 'fallback',
                    'link_message': 'Teknosa arama sayfası',
                    'why_recommended': 'Sinema ve oyun deneyimi'
                },
                {
                    'title': 'Xiaomi TV A2 43"',
                    'price': {'value': min(budget_max or 8000, 8000), 'currency': 'TRY', 'display': f'{min(budget_max or 8000, 8000):.0f} ₺'},
                    'features': ['4K HDR', 'Android TV', 'Dolby Audio', 'Chromecast'],
                    'pros': ['Uygun fiyat', 'Android TV', 'İyi özellikler'],
                    'cons': ['Orta seviye panel', 'Ses kalitesi'],
                    'match_score': 75,
                    'source_site': 'trendyol.com',
                    'product_url': 'https://www.trendyol.com/sr?q=xiaomi+tv+a2+43',
                    'link_status': 'fallback',
                    'link_message': 'Trendyol arama sayfası',
                    'why_recommended': 'Bütçe dostu akıllı TV'
                }
            ]

        elif category == 'Tire':
            return [
                {
                    'title': 'Michelin Pilot Sport 4 225/45 R17',
                    'price': {'value': min(budget_max or 2500, 2500), 'currency': 'TRY', 'display': f'{min(budget_max or 2500, 2500):.0f} ₺'},
                    'features': ['Spor Lastik', 'Yüksek Performans', 'Islak Yol Tutuşu', 'Uzun Ömür'],
                    'pros': ['Mükemmel tutuş', 'Premium marka', 'Güvenli'],
                    'cons': ['Pahalı', 'Gürültü seviyesi'],
                    'match_score': 90,
                    'source_site': 'hepsiburada.com',
                    'product_url': 'https://www.hepsiburada.com/ara?q=michelin+pilot+sport+4',
                    'link_status': 'fallback',
                    'link_message': 'Hepsiburada arama sayfası',
                    'why_recommended': 'Premium performans lastiği'
                },
                {
                    'title': 'Bridgestone Turanza T005 205/55 R16',
                    'price': {'value': min(budget_max or 1800, 1800), 'currency': 'TRY', 'display': f'{min(budget_max or 1800, 1800):.0f} ₺'},
                    'features': ['Konfor Odaklı', 'Düşük Gürültü', 'Enerji Tasarrufu', 'Uzun Ömür'],
                    'pros': ['Konforlu sürüş', 'Güvenilir marka', 'Dayanıklı'],
                    'cons': ['Spor performans sınırlı'],
                    'match_score': 85,
                    'source_site': 'teknosa.com',
                    'product_url': 'https://www.teknosa.com/arama?q=bridgestone+turanza+t005',
                    'link_status': 'fallback',
                    'link_message': 'Teknosa arama sayfası',
                    'why_recommended': 'Konfor ve güvenlik odaklı'
                },
                {
                    'title': 'Lassa Competus H/P 215/60 R17',
                    'price': {'value': min(budget_max or 1200, 1200), 'currency': 'TRY', 'display': f'{min(budget_max or 1200, 1200):.0f} ₺'},
                    'features': ['SUV Lastiği', 'Türk Malı', 'Uygun Fiyat', 'Dört Mevsim'],
                    'pros': ['Uygun fiyat', 'Yerli üretim', 'SUV uyumlu'],
                    'cons': ['Performans sınırlı', 'Gürültü'],
                    'match_score': 75,
                    'source_site': 'trendyol.com',
                    'product_url': 'https://www.trendyol.com/sr?q=lassa+competus+suv+lastik',
                    'link_status': 'fallback',
                    'link_message': 'Trendyol arama sayfası',
                    'why_recommended': 'Bütçe dostu yerli seçenek'
                }
            ]

        elif category == 'Telefon':
            return [
                {
                    'title': 'iPhone 15 128GB',
                    'price': {'value': min(budget_max or 35000, 35000), 'currency': 'TRY', 'display': f'{min(budget_max or 35000, 35000):.0f} ₺'},
                    'features': ['A17 Pro Chip', '48MP Kamera', 'iOS 17', 'USB-C'],
                    'pros': ['Premium performans', 'Uzun destek', 'Mükemmel kamera'],
                    'cons': ['Pahalı', 'Lightning yerine USB-C'],
                    'match_score': 90,
                    'source_site': 'hepsiburada.com',
                    'product_url': 'https://www.hepsiburada.com/ara?q=iphone+15+128gb',
                    'link_status': 'fallback',
                    'link_message': 'Hepsiburada arama sayfası',
                    'why_recommended': 'Premium iPhone deneyimi'
                },
                {
                    'title': 'Samsung Galaxy S23 256GB',
                    'price': {'value': min(budget_max or 25000, 25000), 'currency': 'TRY', 'display': f'{min(budget_max or 25000, 25000):.0f} ₺'},
                    'features': ['Snapdragon 8 Gen 2', '50MP Kamera', 'Android 14', '8GB RAM'],
                    'pros': ['Güçlü performans', 'İyi kamera', 'Samsung ekosistemi'],
                    'cons': ['OneUI arayüzü', 'Pil ömrü'],
                    'match_score': 85,
                    'source_site': 'teknosa.com',
                    'product_url': 'https://www.teknosa.com/arama?q=samsung+galaxy+s23+256gb',
                    'link_status': 'fallback',
                    'link_message': 'Teknosa arama sayfası',
                    'why_recommended': 'Android flagship deneyimi'
                },
                {
                    'title': 'Xiaomi Redmi Note 13 Pro 256GB',
                    'price': {'value': min(budget_max or 12000, 12000), 'currency': 'TRY', 'display': f'{min(budget_max or 12000, 12000):.0f} ₺'},
                    'features': ['Dimensity 7200', '200MP Kamera', 'AMOLED Ekran', '67W Şarj'],
                    'pros': ['Fiyat/performans', 'Hızlı şarj', 'İyi ekran'],
                    'cons': ['MIUI arayüzü', 'Plastik gövde'],
                    'match_score': 80,
                    'source_site': 'trendyol.com',
                    'product_url': 'https://www.trendyol.com/sr?q=xiaomi+redmi+note+13+pro',
                    'link_status': 'fallback',
                    'link_message': 'Trendyol arama sayfası',
                    'why_recommended': 'En iyi fiyat/performans'
                }
            ]

        # Diğer kategoriler için genel fallback
        else:
            return [
                {
                    'title': f'Önerilen {category}',
                    'price': {'value': budget_min or 1000, 'currency': 'TRY', 'display': f'{budget_min or 1000:.0f} ₺'},
                    'features': ['Kaliteli', 'Güvenilir'],
                    'pros': ['İyi performans'],
                    'cons': ['Sınırlı bilgi'],
                    'match_score': 75,
                    'source_site': 'hepsiburada.com',
                    'product_url': f'https://www.hepsiburada.com/ara?q={category.lower()}',
                    'link_status': 'fallback',
                'link_message': 'Hepsiburada arama sayfası',
                'why_recommended': 'Genel öneri - detaylı arama yapılamadı'
            }
        ]
    
    # Amazon entegrasyonu kaldırıldı - modern search sistemi kullanılacak

    def _build_gemini_prompt(self, category, preferences, language):
        """FindFlow Gemini AI için gelişmiş prompt oluşturma"""
        
        # Tercihleri analiz et
        priority_prefs = {}
        optional_prefs = {}
        
        for pref_id, value in preferences.items():
            if value is not None and value != 'Bilmiyorum' and value != 'Not sure' and value != 'Farketmez' and value != 'No preference':
                # Spec weight'ini bul
                spec_weight = 1.0
                for spec in self.categories[category]['specs']:
                    if spec['id'] == pref_id:
                        spec_weight = spec.get('weight', 1.0)
                        break
                
                if spec_weight >= 0.8:
                    priority_prefs[pref_id] = value
                else:
                    optional_prefs[pref_id] = value
        
        if language == 'tr':
            prompt = f"""Sen bir {category} uzmanısın. Türkiye pazarı için ürün önerisi yap.

Kullanıcı tercihleri:
{json.dumps(priority_prefs, indent=2, ensure_ascii=False)}
{json.dumps(optional_prefs, indent=2, ensure_ascii=False)}

3-4 ürün öner. Her ürün için:
- Ürün adı ve modeli
- Fiyat aralığı (TL)
- Ana özellikler
- Neden önerdiğin

Basit format kullan:
1. [ÜrünAdı] - [Fiyat] - [Özellikler]
2. [ÜrünAdı] - [Fiyat] - [Özellikler]
...

Örnek:
1. DJI Mini 3 - 15.000₺ - 4K kamera, 38dk uçuş süresi, kompakt tasarım"""
        else:
            prompt = f"""You are a {category} expert. Recommend products for Turkey market.

User preferences:
{json.dumps(priority_prefs, indent=2)}
{json.dumps(optional_prefs, indent=2)}

Recommend 3-4 products. For each:
- Product name and model
- Price range (TL)
- Key features
- Why you recommend it

Simple format:
1. [ProductName] - [Price] - [Features]
2. [ProductName] - [Price] - [Features]
...

Example:
1. DJI Mini 3 - 15,000₺ - 4K camera, 38min flight time, compact design"""
        
        return prompt

    def _parse_gemini_response(self, text):
        """Gemini response'unu parse et"""
        import re
        lines = text.strip().split('\n')
        recommendations = []
        
        for line in lines:
            line = line.strip()
            if not line or 'format' in line.lower() or 'örnek' in line.lower():
                continue
                
            # Format: ProductName - Price - Description
            parts = line.split(' - ')
            if len(parts) >= 3:
                name = parts[0].strip()
                price = parts[1].strip()
                description = parts[2].strip()
                
                recommendations.append({
                    'name': name,
                    'price': price,
                    'description': description
                })
        
        # Eğer parse edilemezse, ham metni döndür
        if not recommendations:
            recommendations.append({
                'name': 'Öneri',
                'price': '',
                'description': text
            })
        
        return recommendations
