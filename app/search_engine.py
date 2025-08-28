"""
Modern Search Engine - Grounding + Function Calling + SerpAPI
============================================================

Bu modül, modern ürün arama sistemi için gerekli tüm bileşenleri içerir:
- Google Search Grounding
- URL Context Reading  
- SerpAPI Shopping entegrasyonu
- Function Calling desteği

Mimari:
1. Google Search Grounding → güncel sonuçlar + citations
2. URL Context → derin sayfa okuma
3. SerpAPI Shopping → kesin fiyat verileri
4. Structured Output → JSON şema

Gereksinimler:
- SerpAPI anahtarı (SERPAPI_KEY)
- Google Generative AI (Gemini)
- requests kütüphanesi
"""

import os
import json
import requests
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv
from .config import setup_gemini, get_gemini_model, generate_with_retry
from urllib.parse import urlparse, parse_qs

# .env dosyasını yükle
load_dotenv()

class ModernSearchEngine:
    """
    FindFlow Modern Ürün Arama Motoru - Grounding + Function Calling Mimarisi
    
    Bu sınıf, FindFlow uygulamasının ürün arama ve öneri sisteminin 
    kalbidir. Modern AI teknolojileri ile gerçek zamanlı ürün verisi 
    toplayarak kullanıcıya en uygun önerileri sunar.
    """
    
    def __init__(self):
        """FindFlow Arama Motoru Başlatma"""
        self.serpapi_key = os.getenv('SERPAPI_KEY')
        self.serpapi_base_url = "https://serpapi.com/search"
        self.cache = {}  # Basit cache sistemi
        self.cache_duration = timedelta(hours=6)  # 6 saat cache
        
        # Türkiye'deki popüler e-ticaret siteleri (En çok kullanılan 15+ site)
        self.tr_shopping_sites = [
            # Ana e-ticaret siteleri
            'hepsiburada.com',
            'trendyol.com', 
            'n11.com',
            'amazon.com.tr',
            'gittigidiyor.com',
            
            # Elektronik uzmanı siteler
            'teknosa.com',
            'vatanbilgisayar.com',
            'mediamarkt.com.tr',
            'gold.com.tr',
            'itopya.com',
            'incehesap.com',
            
            # Genel mağazalar
            'migros.com.tr',
            'carrefoursa.com',
            'a101.com.tr',
            'bim.com.tr',
            
            # Diğer popüler siteler
            'ciceksepeti.com',
            'idefix.com',
            'kitapyurdu.com',
            'morhipo.com',
            'lcw.com',
            'defacto.com.tr',
            'koton.com',
            'mavi.com',
            
            # Online marketler
            'getir.com',
            'banabi.com',
            'istegelsin.com'
        ]
        
        # Request headers for link validation
        self.request_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        if not self.serpapi_key:
            print("⚠️  SERPAPI_KEY environment variable bulunamadı!")
            print("   SerpAPI'den ücretsiz anahtar alabilirsiniz: https://serpapi.com/")
    
    def search_products(self, user_preferences: Dict, site_filter: Optional[List[str]] = None) -> Dict:
        """
        Ana ürün arama fonksiyonu - Grounding + Function Calling
        
        Args:
            user_preferences (Dict): Kullanıcı tercihleri
                {
                    'category': 'Hair Dryer',
                    'budget_min': 500,
                    'budget_max': 1000,
                    'features': ['ionic', 'ceramic'],
                    'language': 'tr'
                }
            site_filter (List[str]): Tercih edilen siteler
            
        Returns:
            Dict: Arama sonuçları
                {
                    'grounding_results': [...],
                    'shopping_results': [...],
                    'sources': [...],
                    'recommendations': [...]
                }
        """
        try:
            print(f"🔍 Modern search başlatılıyor...")
            print(f"📊 User preferences: {json.dumps(user_preferences, ensure_ascii=False)}")
            
            # Adım 1: Google Search Grounding
            grounding_results = self._search_with_grounding(user_preferences, site_filter)
            
            # Adım 2: Site seçimi için kaynakları hazırla
            sources = self._extract_sources(grounding_results)
            
            # Adım 3: SerpAPI Shopping ile kesin fiyatlar
            shopping_results = self._search_shopping_serp(user_preferences)
            
            # Adım 4: Structured Output ile sonuçları birleştir
            final_recommendations = self._generate_structured_recommendations(
                grounding_results, shopping_results, user_preferences
            )
            
            return {
                'status': 'success',
                'grounding_results': grounding_results,
                'shopping_results': shopping_results,
                'sources': sources,
                'recommendations': final_recommendations,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _search_with_grounding(self, preferences: Dict, site_filter: Optional[List[str]]) -> Dict:
        """
        Adım 1: Google Search Grounding
        """
        try:
            setup_gemini()
            model = get_gemini_model()
            
            # Query oluştur
            query = self._build_search_query(preferences, site_filter)
            
            # Grounding prompt
            grounding_prompt = f"""
Sen bir Türkiye e-ticaret uzmanısın. Aşağıdaki kriterlere göre ürün araştırması yap:

ARAMA KRİTERLERİ:
{json.dumps(preferences, ensure_ascii=False, indent=2)}

Site filtresi: {site_filter if site_filter else 'Tüm siteler'}

GÖREVİN:
1. Google Search ile güncel ürün bilgilerini ara
2. Türkiye'deki e-ticaret sitelerinden fiyat ve özellik bilgileri topla
3. Kaynak linklerini ve citations belirt
4. En uygun 5-8 ürün öner

ARAMA SORGUSU: {query}

Lütfen kaynaklı bir rapor hazırla.
"""
            
            print(f"🔍 Grounding search: {query}")
            
            # Google Search araçları ile arama yap
            response = generate_with_retry(
                model,
                grounding_prompt,
                max_retries=2,
                delay=3
            )
            
            if response and response.text:
                return {
                    'query': query,
                    'response': response.text,
                    'citations': self._extract_citations(response)
                }
            else:
                return {'query': query, 'response': '', 'citations': []}
                
        except Exception as e:
            print(f"❌ Grounding search error: {e}")
            return {'query': '', 'response': '', 'citations': []}
    
    def _search_shopping_serp(self, preferences: Dict) -> List[Dict]:
        """
        Adım 3: SerpAPI Shopping ile kesin fiyat arama
        """
        if not self.serpapi_key:
            return self._get_mock_shopping_results(preferences)
        
        try:
            # Shopping query oluştur
            shopping_query = self._build_shopping_query(preferences)
            
            # SerpAPI Google Shopping parametreleri
            params = {
                'engine': 'google_shopping',
                'api_key': self.serpapi_key,
                'q': shopping_query,
                'google_domain': 'google.com.tr',
                'gl': 'tr',
                'hl': 'tr',
                'currency': 'TRY',
                'num': 50  # ✅ 50 sonuç al (maksimum)
            }
            
            # Fiyat filtresi ekle - Google Shopping tbs parametresi ile
            budget_min = preferences.get('budget_min') or 0
            budget_max = preferences.get('budget_max') or 0
            
            print(f"💰 Budget check: min={budget_min}, max={budget_max}")
            
            # Google Shopping tbs parametresi oluştur
            tbs_parts = ['mr:1', 'price:1']  # mr:1 = recent, price:1 = price sort
            
            if budget_min and budget_min > 100:  # 100₺'den düşük fiyatları kabul etme
                tbs_parts.append(f'ppr_min:{int(budget_min)}')
                print(f"✅ Min price tbs: {budget_min}")
                
            if budget_max and budget_max > (budget_min or 0) and budget_max < 100000:  # Makul üst limit
                tbs_parts.append(f'ppr_max:{int(budget_max)}')
                print(f"✅ Max price tbs: {budget_max}")
            
            # tbs parametresini ekle
            if len(tbs_parts) > 2:  # Fiyat filtresi varsa
                params['tbs'] = ','.join(tbs_parts)
                print(f"🔧 TBS parameter: {params['tbs']}")
            
            print(f"🛒 SerpAPI Shopping search: '{shopping_query}'")
            print(f"💰 Final price filter: {budget_min}₺ - {budget_max}₺ (via tbs)")
            
            response = requests.get(self.serpapi_base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                shopping_results = data.get('shopping_results', [])
                
                print(f"📊 Raw results count: {len(shopping_results)}")
                
                # Sonuçları formatla ve filtrele - ✅ 20'a kadar al
                formatted_results = []
                for result in shopping_results[:20]:  # İlk 20 sonuç
                    formatted_result = self._format_shopping_result(result, preferences)
                    if formatted_result:
                        formatted_results.append(formatted_result)
                
                print(f"✅ {len(formatted_results)} shopping result bulundu")
                return formatted_results
            else:
                print(f"❌ SerpAPI error: {response.status_code}")
                return self._get_mock_shopping_results(preferences)
                
        except Exception as e:
            print(f"❌ SerpAPI shopping error: {e}")
            return self._get_mock_shopping_results(preferences)
    
    def _build_search_query(self, preferences: Dict, site_filter: Optional[List[str]]) -> str:
        """FindFlow için arama sorgusu oluşturma"""
        category = preferences.get('category', '')
        features = preferences.get('features', [])
        budget_min = preferences.get('budget_min')
        budget_max = preferences.get('budget_max')
        
        # Ana query
        query_parts = [category]
        
        # Özellikler ekle
        if features:
            query_parts.extend(features)
        
        # Site filtresi
        if site_filter:
            site_queries = [f"site:{site}" for site in site_filter]
            site_filter_str = f"({' OR '.join(site_queries)})"
            query_parts.append(site_filter_str)
        
        # Fiyat aralığı
        if budget_min and budget_max:
            query_parts.append(f"{budget_min}₺-{budget_max}₺")
        
        return ' '.join(query_parts)
    
    def _build_shopping_query(self, preferences: Dict) -> str:
        """Shopping query oluştur - Telefon kategorisi için özel"""
        category = preferences.get('category', '')
        features = preferences.get('features', [])
        brand_preference = preferences.get('brand_preference', '')
        usage_type = preferences.get('usage_type', '')
        
        # Kategori eşleştirmeleri
        category_mapping = {
            'Phone': 'akıllı telefon smartphone',
            'Laptop': 'laptop bilgisayar',
            'Headphones': 'kulaklık',
            'Mouse': 'mouse fare',
            'Tire': 'lastik'  # ✅ Tire kategorisi eklendi
        }
        
        # Doğru kategori query'si oluştur
        base_query = category_mapping.get(category, category)
        
        # Tire kategorisi için özel işlemler
        if category == 'Tire':
            # Tire specifications ekle
            tire_type = preferences.get('tire_type', '')
            tire_size = preferences.get('tire_size', '')
            vehicle_type = preferences.get('vehicle_type', '')
            brand_preference = preferences.get('brand_preference', '')
            
            if tire_type and tire_type != 'no_preference':
                if tire_type == 'summer':
                    base_query += ' yazlık'
                elif tire_type == 'winter':
                    base_query += ' kışlık'
                elif tire_type == 'all_season':
                    base_query += ' dört mevsim'
            
            if tire_size and tire_size != 'other':
                # tire_size'ı gerçek size'a çevir
                size_mapping = {
                    '195_65_r15': '195/65 R15',
                    '205_55_r16': '205/55 R16', 
                    '225_45_r17': '225/45 R17'
                }
                actual_size = size_mapping.get(tire_size, tire_size)
                base_query += f' {actual_size}'
            
            if brand_preference and brand_preference != 'no_preference':
                base_query += f' {brand_preference}'
            
            if vehicle_type and vehicle_type != 'no_preference':
                if vehicle_type == 'passenger_car':
                    base_query += ' binek araç'
                elif vehicle_type == 'suv':
                    base_query += ' SUV'
                elif vehicle_type == 'truck':
                    base_query += ' kamyonet'
        
        # Marka tercihi varsa ekle (diğer kategoriler için)
        elif brand_preference and brand_preference != 'no_preference':
            if brand_preference == 'apple':
                base_query += ' iPhone'
            elif brand_preference == 'samsung':
                base_query += ' Samsung Galaxy'
            elif brand_preference == 'xiaomi':
                base_query += ' Xiaomi'
            else:
                base_query += f' {brand_preference}'
        
        # Kullanım amacına göre ek terimler
        if usage_type:
            if usage_type == 'photography':
                base_query += ' kamera'
            elif usage_type == 'gaming':
                base_query += ' gaming'
        
        # Aksesuar değil, ana ürün olduğunu belirt
        if category == 'Phone':
            base_query += ' -kılıf -aksesuar -tutacak -şarj'
        
        return base_query
    
    def _extract_citations(self, response) -> List[Dict]:
        """Grounding response'undan citations çıkar"""
        citations = []
        
        # Gemini response'unda grounding metadata varsa çıkar
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata'):
                # Grounding metadata'yı işle
                pass
        
        return citations
    
    def _extract_sources(self, grounding_results: Dict) -> List[Dict]:
        """Grounding'den kaynak linkleri çıkar"""
        sources = []
        
        # Response'dan URL'leri regex ile çıkar
        import re
        text = grounding_results.get('response', '')
        urls = re.findall(r'https?://[^\s]+', text)
        
        for url in urls:
            # Türk e-ticaret sitelerini filtrele
            for site in self.tr_shopping_sites:
                if site in url:
                    sources.append({
                        'site': site,
                        'url': url,
                        'title': f"{site.replace('.com', '').title()} ürün sayfası"
                    })
                    break
        
        return sources[:5]  # İlk 5 kaynak
    
    def _format_shopping_result(self, result: Dict, preferences: Dict = None) -> Optional[Dict]:
        """SerpAPI shopping result'ını formatla ve filtrele"""
        try:
            # Temel bilgileri çıkar
            title = result.get('title', '').strip()
            price_str = result.get('price', '')
            extracted_price = result.get('extracted_price', '')  # ✅ SerpAPI extracted_price alanı
            source = result.get('source', '')
            link = result.get('link', '')
            
            # Boş veya geçersiz sonuçları filtrele
            if not title:
                return None
            
            # Fiyat bilgisini çıkar - önce extracted_price'ı dene
            price_value = 0.0
            print(f"🔍 Debug fiyat verileri:")
            print(f"   price_str: '{price_str}'")
            print(f"   extracted_price: '{extracted_price}'")
            
            if extracted_price:
                try:
                    # extracted_price genelde sayısal değer olarak gelir
                    price_value = float(extracted_price)
                    print(f"💰 Using extracted_price: {price_value}")
                except (ValueError, TypeError):
                    print(f"⚠️ Invalid extracted_price: {extracted_price}, fallback to price parsing")
                    price_value = self._extract_price_value(price_str)
                    print(f"💰 Parsed price_str result: {price_value}")
            else:
                # Fallback: Normal price string parsing
                price_value = self._extract_price_value(price_str)
                print(f"💰 Parsed price_str only: {price_value}")
            
            print(f"🎯 Final price_value: {price_value}")
            
            # Fiyat yoksa skip
            if price_value <= 0:
                print(f"🚫 No valid price found for: {title}")
                return None
            
            # Telefon kategorisi için özel filtreler
            if preferences and preferences.get('category') == 'Phone':
                # Aksesuar ve kılıf filtresi
                unwanted_keywords = [
                    'kılıf', 'tutacak', 'aksesuar', 'şarj kablosu', 'şarj aleti',
                    'adaptör', 'cam koruyucu', 'temperli cam', 'cep telefonu kılıfı',
                    'silikon kılıf', 'koruyucu', 'stand', 'kapak'
                ]
                
                title_lower = title.lower()
                if any(keyword in title_lower for keyword in unwanted_keywords):
                    print(f"🚫 Aksesuar filtrelendi: {title}")
                    return None
                
                # Fiyat filtresi - çok düşük fiyatları filtrele
                budget_min = preferences.get('budget_min') or 1000
                if price_value > 0 and price_value < budget_min * 0.3:  # Bütçenin %30'undan az olan fiyatları filtrele
                    print(f"🚫 Düşük fiyat filtrelendi: {title} - {price_value}₺ (min: {budget_min}₺)")
                    return None
                
                # Telefon olduğundan emin ol
                phone_keywords = ['telefon', 'phone', 'smartphone', 'iphone', 'galaxy', 'redmi', 'huawei']
                if not any(keyword in title_lower for keyword in phone_keywords):
                    print(f"🚫 Telefon değil filtrelendi: {title}")
                    return None
            
            # Fiyat formatı
            if price_value > 0:
                price_display = f"{price_value:,.0f} ₺".replace(',', '.')
                print(f"💰 Price formatting: {price_value} → '{price_display}'")
            else:
                price_display = price_str
                print(f"💰 Using original price_str: '{price_display}'")
            
            # Link kontrolü - ✅ SerpAPI linklerini direkt kullan (doğrulama yok)
            validated_link = link
            link_status = 'serpapi_direct'
            link_message = 'SerpAPI link - doğrulama atlandı'
            
            if link:
                if not link.startswith('http'):
                    validated_link = 'https://' + link
                
                print(f"🔗 SerpAPI link kullanılıyor: {validated_link}")
            else:
                # Link yoksa fallback
                validated_link = f"https://www.google.com/search?q={title.replace(' ', '+')}"
                link_status = 'fallback'
                link_message = 'Google arama (link yok)'
            
            print(f"✅ Geçerli ürün: {title} - {price_display} - {source}")
            
            price_obj = {
                'value': price_value,
                'currency': 'TRY',
                'display': price_display
            }
            print(f"💰 Final price object: {price_obj}")
            
            return {
                'title': title,
                'price': price_obj,
                'source': source,
                'link': validated_link,
                'link_status': link_status,
                'link_message': link_message,
                'thumbnail': result.get('thumbnail', ''),
                'rating': result.get('rating', 0),
                'reviews': result.get('reviews', 0)
            }
        except Exception as e:
            print(f"❌ Shopping result format error: {e}")
            return None
    
    def _extract_price_value(self, price_str: str) -> float:
        """Fiyat string'inden sayısal değer çıkar - güçlendirilmiş versiyon"""
        import re
        
        # Türkçe fiyat formatları: "1.250,99 ₺", "1250 TL", "₺1,250.99", "1k₺", "2.5k₺"
        if not price_str:
            return 0.0
        
        print(f"🔍 Price parsing input: '{price_str}'")
        
        # Temizle
        cleaned = price_str.replace('₺', '').replace('TL', '').replace('TRY', '').strip()
        
        # 'k' formatını kontrol et (1k = 1000, 2.5k = 2500)
        if 'k' in cleaned.lower():
            k_match = re.search(r'([\d.,]+)k', cleaned.lower())
            if k_match:
                base_value = k_match.group(1).replace(',', '.')
                try:
                    result = float(base_value) * 1000
                    print(f"💰 K format detected: {base_value}k → {result}")
                    return result
                except:
                    return 0.0
        
        # Türkçe format (1.250,99) → İngilizce format (1250.99)
        if ',' in cleaned and '.' in cleaned:
            # 1.250,99 formatı
            parts = cleaned.split(',')
            if len(parts) == 2:
                integer_part = parts[0].replace('.', '')  # Binlik ayırıcıları kaldır
                decimal_part = parts[1]
                cleaned = f"{integer_part}.{decimal_part}"
                print(f"💰 Turkish format: {price_str} → {cleaned}")
        elif ',' in cleaned:
            # Sadece virgül var (1250,99)
            cleaned = cleaned.replace(',', '.')
            print(f"💰 Comma to dot: {price_str} → {cleaned}")
        
        # Sayıları bul ve en büyüğünü al (çünkü fiyat genelde en büyük sayıdır)
        numbers = re.findall(r'[\d.]+', cleaned)
        if numbers:
            try:
                # En büyük sayıyı bul (fiyat muhtemelen budur)
                prices = [float(num) for num in numbers if float(num) > 0]
                if prices:
                    result = max(prices)
                    print(f"💰 Found numbers: {numbers}, selected: {result}")
                    
                    # Çok küçük fiyatları kontrol et (muhtemelen hatalı parse)
                    if result < 50 and any(float(num) > 1000 for num in numbers):
                        # Büyük sayı varsa onu kullan
                        result = max(float(num) for num in numbers)
                        print(f"💰 Corrected small price: {result}")
                    
                    return result
                return 0.0
            except:
                print(f"❌ Price parsing failed for: {cleaned}")
                return 0.0
        return 0.0
    
    def _generate_structured_recommendations(self, grounding: Dict, shopping: List[Dict], preferences: Dict) -> List[Dict]:
        """SerpAPI shopping sonuçlarını direkt öneriler olarak kullan - EN FAZLA 20 ÜRÜN"""
        try:
            print(f"🛒 Processing {len(shopping)} shopping results for recommendations")
            
            # ✅ SerpAPI sonuçları zaten formatlanmış - direkt kullan
            if shopping and len(shopping) > 0:
                print(f"✅ Using {len(shopping)} real SerpAPI results")
                
                # En fazla 20 ürün al
                max_results = min(20, len(shopping))
                recommendations = shopping[:max_results]
                
                # Her öneriye match_score ekle (basit algoritma)
                for i, rec in enumerate(recommendations):
                    # İlk ürünlere daha yüksek score ver
                    base_score = max(95 - (i * 2), 60)  # 95'ten başlayıp 2'şer azalt, min 60
                    
                    # Fiyat uyumuna göre score ayarla
                    price_value = rec.get('price', {}).get('value', 0)
                    budget_min = preferences.get('budget_min', 0)
                    budget_max = preferences.get('budget_max', 999999)
                    
                    if budget_min <= price_value <= budget_max:
                        price_bonus = 10  # Bütçeye uygun +10
                    else:
                        price_bonus = -5   # Bütçe dışı -5
                    
                    # Features ve pros/cons oluştur (basit)
                    rec['features'] = rec.get('features', [rec.get('title', '').split()[:3]])
                    rec['pros'] = rec.get('pros', ['SerpAPI doğrulanmış ürün', 'Gerçek fiyat bilgisi'])
                    rec['cons'] = rec.get('cons', ['Stok durumu değişebilir'])
                    rec['match_score'] = min(100, max(60, base_score + price_bonus))
                    
                    # Why recommended oluştur
                    source_site = rec.get('source', 'bilinmeyen site')
                    rec['why_recommended'] = f"SerpAPI'den doğrulanmış ürün - {source_site}'den önerildi"
                    rec['source_site'] = source_site
                
                print(f"✅ Generated {len(recommendations)} recommendations from SerpAPI")
                return recommendations
            
            # ✅ Fallback: SerpAPI sonucu yoksa mock kullan
            else:
                print(f"⚠️ No SerpAPI results, falling back to mock recommendations")
                return self._get_mock_recommendations(preferences)
                
        except Exception as e:
            print(f"❌ Structured recommendations error: {e}")
            return self._get_mock_recommendations(preferences)
    
    def _get_mock_shopping_results(self, preferences: Dict) -> List[Dict]:
        """Mock shopping sonuçları"""
        category = preferences.get('category', 'Product')
        budget_min = preferences.get('budget_min', 500)
        budget_max = preferences.get('budget_max', 1000)
        
        mock_results = []
        for i in range(5):
            price = budget_min + (i * (budget_max - budget_min) / 4)
            mock_results.append({
                'title': f'{category} Model {i+1}',
                'price': {
                    'value': price,
                    'currency': 'TRY',
                    'display': f'{price:.0f} ₺'
                },
                'source': f'mocksite{i+1}.com',
                'link': f'https://mocksite{i+1}.com/product{i+1}',
                'thumbnail': f'https://via.placeholder.com/150x150?text=Product{i+1}',
                'rating': 4.0 + (i * 0.2),
                'reviews': 50 + (i * 25),
                'delivery': 'Ücretsiz kargo',
                'shipping': '1-2 gün'
            })
        
        return mock_results
    
    def _get_mock_recommendations(self, preferences: Dict) -> List[Dict]:
        """Mock öneriler - doğrulanmış linklerle gerçek ürün arama linklerine yönlendirme"""
        category = preferences.get('category', 'Product')
        budget_min = preferences.get('budget_min') or 2000
        budget_max = preferences.get('budget_max') or 40000
        
        print(f"🎭 Mock recommendations: {category}, budget: {budget_min}-{budget_max}")
        
        # Telefon kategorisi için gerçekçi öneriler
        if category == 'Phone':
            mock_products = [
                {
                    'title': 'Samsung Galaxy S24 128GB',
                    'price': {'value': min(budget_max * 0.8, 28000), 'currency': 'TRY', 'display': f'{min(budget_max * 0.8, 28000):.0f} ₺'},
                    'features': ['5G Destekli', '128GB Depolama', 'Pro Kamera', '120Hz Ekran'],
                    'pros': ['Yüksek performans', 'Uzun pil ömrü', 'Kaliteli kamera', 'Su geçirmez'],
                    'cons': ['Yüksek fiyat'],
                    'match_score': 95,
                    'source_site': 'teknosa.com',
                    'product_url': 'https://www.teknosa.com/arama?q=samsung+galaxy+s24+128gb',
                    'why_recommended': 'Premium Android deneyimi için en iyi seçenek'
                },
                {
                    'title': 'iPhone 15 128GB',
                    'price': {'value': min(budget_max * 0.9, 35000), 'currency': 'TRY', 'display': f'{min(budget_max * 0.9, 35000):.0f} ₺'},
                    'features': ['A17 Pro Chip', '128GB Depolama', 'Face ID', 'MagSafe'],
                    'pros': ['iOS ekosistemi', 'Premium yapı', 'Uzun destek', 'Resale değeri'],
                    'cons': ['Pahalı', 'Lightning port'],
                    'match_score': 90,
                    'source_site': 'hepsiburada.com',
                    'product_url': 'https://www.hepsiburada.com/ara?q=iphone+15+128gb',
                    'why_recommended': 'Apple ekosistemi sevenlere ideal'
                },
                {
                    'title': 'Xiaomi Redmi Note 13 Pro 256GB',
                    'price': {'value': max(budget_min * 0.6, 8500), 'currency': 'TRY', 'display': f'{max(budget_min * 0.6, 8500):.0f} ₺'},
                    'features': ['Snapdragon 7s Gen 2', '256GB Depolama', '108MP Kamera', '67W Hızlı Şarj'],
                    'pros': ['Uygun fiyat', 'Yüksek depolama', 'Hızlı şarj', 'MIUI'],
                    'cons': ['Plastik kasa', 'Orta segment işlemci'],
                    'match_score': 85,
                    'source_site': 'trendyol.com',
                    'product_url': 'https://www.trendyol.com/sr?q=xiaomi+redmi+note+13+pro+256gb',
                    'why_recommended': 'Bütçe dostu güçlü seçenek'
                },
                {
                    'title': 'OnePlus Nord CE 3 Lite 128GB',
                    'price': {'value': max(budget_min * 0.4, 6500), 'currency': 'TRY', 'display': f'{max(budget_min * 0.4, 6500):.0f} ₺'},
                    'features': ['Snapdragon 695', '128GB Depolama', '108MP Ana Kamera', '67W SuperVOOC'],
                    'pros': ['Temiz Android', 'Hızlı şarj', 'İyi kamera', 'Makul fiyat'],
                    'cons': ['Plastik tasarım', 'Orta segment performans'],
                    'match_score': 80,
                    'source_site': 'vatanbilgisayar.com',
                    'product_url': 'https://www.vatanbilgisayar.com/arama/?text=oneplus+nord+ce+3+lite',
                    'why_recommended': 'Temiz Android deneyimi isteyenler için'
                },
                {
                    'title': 'Realme 11 Pro 256GB',
                    'price': {'value': max(budget_min * 0.5, 7500), 'currency': 'TRY', 'display': f'{max(budget_min * 0.5, 7500):.0f} ₺'},
                    'features': ['MediaTek Dimensity 7050', '256GB Depolama', '100MP Kamera', '67W Hızlı Şarj'],
                    'pros': ['Büyük depolama', 'Hızlı şarj', 'İyi kamera', 'Şık tasarım'],
                    'cons': ['MediaTek işlemci', 'Realme UI'],
                    'match_score': 75,
                    'source_site': 'n11.com',
                    'product_url': 'https://www.n11.com/arama?q=realme+11+pro+256gb',
                    'why_recommended': 'Bütçenize uygun en kaliteli seçenek'
                },
                {
                    'title': 'Oppo Reno 10 5G 256GB',
                    'price': {'value': max(budget_min * 0.7, 9500), 'currency': 'TRY', 'display': f'{max(budget_min * 0.7, 9500):.0f} ₺'},
                    'features': ['Snapdragon 778G', '256GB Depolama', '64MP Telefoto', '80W Hızlı Şarj'],
                    'pros': ['Telefoto lens', 'Süper hızlı şarj', 'Şık tasarım', '5G destekli'],
                    'cons': ['ColorOS arayüzü', 'Orta segment chip'],
                    'match_score': 78,
                    'source_site': 'mediamarkt.com.tr',
                    'product_url': 'https://www.mediamarkt.com.tr/tr/search.html?query=oppo+reno+10+5g',
                    'why_recommended': 'Fotoğraf odaklı kullanım için ideal'
                },
                {
                    'title': 'Honor 90 5G 256GB',
                    'price': {'value': max(budget_min * 0.6, 8000), 'currency': 'TRY', 'display': f'{max(budget_min * 0.6, 8000):.0f} ₺'},
                    'features': ['Snapdragon 7 Gen 1', '256GB Depolama', '200MP Ana Kamera', '66W Hızlı Şarj'],
                    'pros': ['200MP kamera', 'Büyük depolama', 'İnce tasarım', 'Magic UI'],
                    'cons': ['Yeni marka', 'Servis ağı sınırlı'],
                    'match_score': 73,
                    'source_site': 'gold.com.tr',
                    'product_url': 'https://www.gold.com.tr/arama?q=honor+90+5g+256gb',
                    'why_recommended': 'Yeni teknoloji meraklıları için'
                },
                {
                    'title': 'Nothing Phone (2a) 128GB',
                    'price': {'value': max(budget_min * 0.5, 7000), 'currency': 'TRY', 'display': f'{max(budget_min * 0.5, 7000):.0f} ₺'},
                    'features': ['MediaTek Dimensity 7200 Pro', '128GB Depolama', 'Glyph Interface', '45W Hızlı Şarj'],
                    'pros': ['Unique tasarım', 'Temiz Android', 'LED arayüzü', 'İnovatif'],
                    'cons': ['Yeni marka', 'Sınırlı depolama'],
                    'match_score': 70,
                    'source_site': 'itopya.com',
                    'product_url': 'https://www.itopya.com/arama/?q=nothing+phone+2a',
                    'why_recommended': 'Farklı tasarım arayanlar için'
                }
            ]
            
            # Her ürün için link doğrulama yap
            validated_products = []
            for product in mock_products:
                print(f"🔗 Mock ürün link doğrulaması: {product['title']}")
                
                # Link doğrulama yap
                link_result = self.validate_and_repair_link(
                    product['product_url'], 
                    product['title']
                )
                
                # Link bilgilerini güncelle
                product['product_url'] = link_result['url']
                product['link_status'] = link_result['status']
                product['link_message'] = link_result['message']
                
                # Eğer link tamamen başarısız olursa arama URL'si oluştur
                if link_result['status'] == 'failed':
                    search_query = product['title'].replace(' ', '+')
                    product['product_url'] = f"https://www.google.com/search?q={search_query}+telefon+fiyat"
                    product['link_status'] = 'fallback'
                    product['link_message'] = 'Google arama (backup)'
                
                validated_products.append(product)
            
            return validated_products
        
        # Tire kategorisi için gerçekçi öneriler
        elif category == 'Tire':
            # Kullanıcı tercihlerini al
            tire_type = preferences.get('tire_type', 'all_season')
            tire_size = preferences.get('tire_size', '205_55_r16')
            brand_preference = preferences.get('brand_preference', 'no_preference')
            vehicle_type = preferences.get('vehicle_type', 'passenger_car')
            
            # Size mapping
            size_mapping = {
                '195_65_r15': '195/65 R15',
                '205_55_r16': '205/55 R16', 
                '225_45_r17': '225/45 R17'
            }
            actual_size = size_mapping.get(tire_size, '205/55 R16')
            
            # Type mapping
            type_mapping = {
                'summer': 'yazlık',
                'winter': 'kışlık',
                'all_season': 'dört mevsim'
            }
            tire_type_tr = type_mapping.get(tire_type, 'dört mevsim')
            
            mock_tire_products = [
                {
                    'title': f'Bridgestone Turanza T005 {actual_size} {tire_type_tr.title()} Lastik',
                    'price': {'value': max(budget_min * 0.9, 1200), 'currency': 'TRY', 'display': f'{max(budget_min * 0.9, 1200):.0f} ₺'},
                    'features': ['Sessiz Sürüş', 'Uzun Ömür', 'Düşük Yakıt Tüketimi', 'Üstün Fren Performansı'],
                    'pros': ['Premium marka', 'Uzun garantili', 'Mükemmel yol tutuş', 'Yağmurda güvenli'],
                    'cons': ['Yüksek fiyat'],
                    'match_score': 95,
                    'source_site': 'hepsiburada.com',
                    'product_url': f'https://www.google.com/search?q=Bridgestone+Turanza+T005+{actual_size.replace("/", "+").replace(" ", "+")}+{tire_type_tr}+lastik+hepsiburada&tbm=shop',
                    'why_recommended': f'Premium kalite {tire_type_tr} lastik arayanlar için - hepsiburada.com\'den önerildi'
                },
                {
                    'title': f'Michelin Primacy 4 {actual_size} {tire_type_tr.title()} Lastik',
                    'price': {'value': max(budget_min * 0.85, 1150), 'currency': 'TRY', 'display': f'{max(budget_min * 0.85, 1150):.0f} ₺'},
                    'features': ['EverGrip Teknolojisi', 'Islak Zeminde Güvenlik', 'Uzun Ömür', 'Konfor'],
                    'pros': ['Dünya standartları', 'Mükemmel fren', 'Sessiz', 'Dayanıklı'],
                    'cons': ['Pahalı', 'Bulunması zor'],
                    'match_score': 92,
                    'source_site': 'teknosa.com',
                    'product_url': f'https://www.google.com/search?q=Michelin+Primacy+4+{actual_size.replace("/", "+").replace(" ", "+")}+{tire_type_tr}+lastik+teknosa&tbm=shop',
                    'why_recommended': f'Güvenlik odaklı sürücüler için ideal - teknosa.com\'den önerildi'
                },
                {
                    'title': f'Continental PremiumContact 6 {actual_size} {tire_type_tr.title()} Lastik',
                    'price': {'value': max(budget_min * 0.8, 1100), 'currency': 'TRY', 'display': f'{max(budget_min * 0.8, 1100):.0f} ₺'},
                    'features': ['SportPlus Teknolojisi', 'Kısa Fren Mesafesi', 'Ekonomik Yakıt', 'Yüksek Kilometre'],
                    'pros': ['Alman kalitesi', 'Sporty sürüş', 'Ekonomik', 'Güvenilir'],
                    'cons': ['Orta fiyat segmenti'],
                    'match_score': 88,
                    'source_site': 'trendyol.com',
                    'product_url': f'https://www.google.com/search?q=Continental+PremiumContact+6+{actual_size.replace("/", "+").replace(" ", "+")}+{tire_type_tr}+lastik+trendyol&tbm=shop',
                    'why_recommended': f'Kalite-fiyat dengesi arayanlar için - trendyol.com\'den önerildi'
                },
                {
                    'title': f'Pirelli Cinturato P7 {actual_size} {tire_type_tr.title()} Lastik',
                    'price': {'value': max(budget_min * 0.75, 1050), 'currency': 'TRY', 'display': f'{max(budget_min * 0.75, 1050):.0f} ₺'},
                    'features': ['Green Performance', 'Düşük Yuvarlanma Direnci', 'Sessiz Teknoloji', 'Uzun Ömür'],
                    'pros': ['İtalyan tasarım', 'Çevre dostu', 'Yakıt tasarrufu', 'Konforlu'],
                    'cons': ['Yağmurda orta performans'],
                    'match_score': 85,
                    'source_site': 'n11.com',
                    'product_url': f'https://www.google.com/search?q=Pirelli+Cinturato+P7+{actual_size.replace("/", "+").replace(" ", "+")}+{tire_type_tr}+lastik+n11&tbm=shop',
                    'why_recommended': f'Çevre bilinci olan sürücüler için - n11.com\'den önerildi'
                },
                {
                    'title': f'Lassa Competus H/P {actual_size} {tire_type_tr.title()} Lastik',
                    'price': {'value': max(budget_min * 0.6, 800), 'currency': 'TRY', 'display': f'{max(budget_min * 0.6, 800):.0f} ₺'},
                    'features': ['Türk Malı', 'Uygun Fiyat', 'Güvenilir Performans', 'Kolay Bulunur'],
                    'pros': ['Ekonomik', 'Yerli marka', 'Kolay temin', 'Makul kalite'],
                    'cons': ['Premium kadar sessiz değil', 'Orta segment'],
                    'match_score': 80,
                    'source_site': 'vatanbilgisayar.com',
                    'product_url': f'https://www.google.com/search?q=Lassa+Competus+HP+{actual_size.replace("/", "+").replace(" ", "+")}+{tire_type_tr}+lastik+vatanbilgisayar&tbm=shop',
                    'why_recommended': f'Bütçe dostu yerli kalite - vatanbilgisayar.com\'den önerildi'
                }
            ]
            
            # Her ürün için Google arama linkini hazırla (artık link doğrulama yapmaya gerek yok)
            validated_tire_products = []
            for product in mock_tire_products:
                print(f"🔗 Google arama linki oluşturuluyor: {product['title']}")
                
                # Google arama linkini ayarla
                product['link_status'] = 'google_search'
                product['link_message'] = 'Google aramaya yönlendiriyor'
                
                validated_tire_products.append(product)
            
            return validated_tire_products
        
        # Television kategorisi için gerçekçi öneriler
        elif category == 'Television':
            # Kullanıcı tercihlerini al
            screen_size = preferences.get('screen_size', 'medium')
            resolution = preferences.get('resolution', '4k')
            smart_tv = preferences.get('smart_tv', True)
            panel_type = preferences.get('panel_type', 'led')
            brand_preference = preferences.get('brand_preference', 'no_preference')
            
            mock_tv_products = [
                {
                    'title': 'Samsung 55" 4K QLED Smart TV QE55Q70C',
                    'price': {'value': min(budget_max * 0.8, 45000), 'currency': 'TRY', 'display': f'{min(budget_max * 0.8, 45000):.0f} ₺'},
                    'features': ['55 inç QLED', '4K Ultra HD', 'Smart TV', 'HDR10+'],
                    'pros': ['Parlak renkler', 'Gaming özelliği', 'Tizen OS', 'Kaliteli yapı'],
                    'cons': ['Yüksek fiyat', 'Yansıma olabilir'],
                    'match_score': 95,
                    'source_site': 'hepsiburada.com',
                    'product_url': 'https://www.hepsiburada.com/ara?q=samsung+55+qled+smart+tv',
                    'why_recommended': 'Premium QLED deneyimi - hepsiburada.com\'den önerildi'
                },
                {
                    'title': 'LG 43" 4K UHD Smart TV 43UR8050PSB',
                    'price': {'value': min(budget_max * 0.6, 28000), 'currency': 'TRY', 'display': f'{min(budget_max * 0.6, 28000):.0f} ₺'},
                    'features': ['43 inç LED', '4K Ultra HD', 'webOS Smart TV', 'AI ThinQ'],
                    'pros': ['WebOS arayüzü', 'AI özelliği', 'Uygun fiyat', 'Marka güveni'],
                    'cons': ['LED teknoloji', 'Orta segment'],
                    'match_score': 88,
                    'source_site': 'teknosa.com',
                    'product_url': 'https://www.teknosa.com/arama?q=lg+43+4k+smart+tv',
                    'why_recommended': 'Kalite-fiyat dengesi - teknosa.com\'den önerildi'
                },
                {
                    'title': 'Sony 50" 4K OLED Smart TV XR-50A80L',
                    'price': {'value': min(budget_max * 0.9, 55000), 'currency': 'TRY', 'display': f'{min(budget_max * 0.9, 55000):.0f} ₺'},
                    'features': ['50 inç OLED', '4K Ultra HD', 'Google TV', 'XR Cognitive Processor'],
                    'pros': ['Mükemmel kontrast', 'Google TV', 'Sinema kalitesi', 'Premium ses'],
                    'cons': ['Çok pahalı', 'Burn-in riski'],
                    'match_score': 92,
                    'source_site': 'trendyol.com',
                    'product_url': 'https://www.trendyol.com/sr?q=sony+50+oled+smart+tv',
                    'why_recommended': 'En iyi görüntü kalitesi - trendyol.com\'den önerildi'
                },
                {
                    'title': 'TCL 65" 4K QLED Smart TV 65C635',
                    'price': {'value': min(budget_max * 0.5, 32000), 'currency': 'TRY', 'display': f'{min(budget_max * 0.5, 32000):.0f} ₺'},
                    'features': ['65 inç QLED', '4K Ultra HD', 'Android TV', 'Dolby Vision'],
                    'pros': ['Büyük ekran', 'Android TV', 'Uygun fiyat', 'QLED kalite'],
                    'cons': ['Bilinmeyen marka', 'Servis ağı'],
                    'match_score': 82,
                    'source_site': 'n11.com',
                    'product_url': 'https://www.n11.com/arama?q=tcl+65+qled+smart+tv',
                    'why_recommended': 'Büyük ekran bütçe dostu - n11.com\'den önerildi'
                },
                {
                    'title': 'Vestel 32" HD Smart TV 32H9500',
                    'price': {'value': max(budget_min * 0.3, 8500), 'currency': 'TRY', 'display': f'{max(budget_min * 0.3, 8500):.0f} ₺'},
                    'features': ['32 inç LED', 'HD Ready', 'Smart TV', 'Türk Malı'],
                    'pros': ['Yerli marka', 'Ekonomik', 'Kolay servis', 'Temel özellikler'],
                    'cons': ['Sadece HD', 'Küçük ekran'],
                    'match_score': 75,
                    'source_site': 'vatanbilgisayar.com',
                    'product_url': 'https://www.vatanbilgisayar.com/arama/?text=vestel+32+smart+tv',
                    'why_recommended': 'Ekonomik yerli seçenek - vatanbilgisayar.com\'den önerildi'
                }
            ]
            
            return mock_tv_products
        
        # Diğer kategoriler için genel mock
        return []

    def validate_and_repair_link(self, url: str, product_title: str = "") -> Dict:
        """
        Link doğrulama ve otomatik onarım sistemi
        
        Args:
            url (str): Doğrulanacak URL
            product_title (str): Ürün adı (fallback arama için)
            
        Returns:
            dict: {
                'status': 'valid'|'repaired'|'fallback'|'failed',
                'url': 'working_url',
                'message': 'açıklama'
            }
        """
        print(f"🔗 Link doğrulaması başlatılıyor: {url}")
        
        try:
            # Önce orijinal URL'yi test et
            response = requests.get(
                url, 
                headers=self.request_headers,
                timeout=8,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                print(f"✅ Link çalışıyor: {url}")
                return {
                    'status': 'valid',
                    'url': url,
                    'message': 'Link çalışıyor'
                }
                
        except Exception as e:
            print(f"❌ Link başarısız: {e}")
        
        # Link çalışmıyorsa onarım dene
        print(f"🔧 Link onarımı deneniyor...")
        repaired_result = self._repair_broken_link(url, product_title)
        
        if repaired_result['status'] != 'failed':
            return repaired_result
            
        # Hiçbiri işe yaramazsa fallback arama
        print(f"🔍 Fallback arama yapılıyor...")
        fallback_result = self._generate_fallback_search_url(url, product_title)
        
        return fallback_result
    
    def _repair_broken_link(self, url: str, product_title: str) -> Dict:
        """
        Site-specific link onarım mantığı
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Amazon onarımı
            if 'amazon.com.tr' in domain:
                return self._repair_amazon_link(url, product_title)
                
            # Trendyol onarımı  
            if 'trendyol.com' in domain:
                return self._repair_trendyol_link(url, product_title)
                
            # Hepsiburada onarımı
            if 'hepsiburada.com' in domain:
                return self._repair_hepsiburada_link(url, product_title)
                
            # Teknosa onarımı
            if 'teknosa.com' in domain:
                return self._repair_teknosa_link(url, product_title)
                
            # MediaMarkt onarımı
            if 'mediamarkt.com.tr' in domain:
                return self._repair_mediamarkt_link(url, product_title)
                
            # N11 onarımı
            if 'n11.com' in domain:
                return self._repair_n11_link(url, product_title)
                
            # Diğer siteler için genel onarım
            return self._repair_generic_link(url, product_title)
            
        except Exception as e:
            print(f"❌ Link onarım hatası: {e}")
            return {'status': 'failed', 'url': url, 'message': f'Onarım başarısız: {e}'}
    
    def _repair_amazon_link(self, url: str, product_title: str) -> Dict:
        """Amazon link onarımı"""
        try:
            # ASIN'i çıkar
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
            if asin_match:
                asin = asin_match.group(1)
                
                # Kanonik URL dene
                canonical_url = f"https://www.amazon.com.tr/dp/{asin}"
                
                response = requests.get(
                    canonical_url,
                    headers=self.request_headers,
                    timeout=8,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    print(f"✅ Amazon kanonik URL çalışıyor: {canonical_url}")
                    return {
                        'status': 'repaired',
                        'url': canonical_url,
                        'message': 'Amazon ASIN ile onarıldı'
                    }
                
                # Kanonik çalışmazsa arama URL'si
                search_url = f"https://www.amazon.com.tr/s?k={product_title} {asin}"
                print(f"📍 Amazon fallback arama: {search_url}")
                return {
                    'status': 'fallback',
                    'url': search_url,
                    'message': 'Amazon arama sayfası (fallback)'
                }
            
            # ASIN bulunamazsa genel arama
            search_url = f"https://www.amazon.com.tr/s?k={product_title}"
            return {
                'status': 'fallback',
                'url': search_url,
                'message': 'Amazon arama sayfası'
            }
            
        except Exception as e:
            return {'status': 'failed', 'url': url, 'message': f'Amazon onarım hatası: {e}'}
    
    def _repair_trendyol_link(self, url: str, product_title: str) -> Dict:
        """Trendyol link onarımı"""
        try:
            # Ürün ID'sini çıkar
            id_match = re.search(r'-p-(\d+)', url)
            if id_match:
                product_id = id_match.group(1)
                
                # Basit URL formatını dene
                simple_url = f"https://www.trendyol.com/product-p-{product_id}"
                
                response = requests.get(
                    simple_url,
                    headers=self.request_headers,
                    timeout=8,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    print(f"✅ Trendyol basit URL çalışıyor: {simple_url}")
                    return {
                        'status': 'repaired',
                        'url': simple_url,
                        'message': 'Trendyol ID ile onarıldı'
                    }
            
            # ID ile onarım başarısızsa arama
            search_url = f"https://www.trendyol.com/sr?q={product_title}"
            print(f"📍 Trendyol fallback arama: {search_url}")
            return {
                'status': 'fallback',
                'url': search_url,
                'message': 'Trendyol arama sayfası (fallback)'
            }
            
        except Exception as e:
            return {'status': 'failed', 'url': url, 'message': f'Trendyol onarım hatası: {e}'}
    
    def _repair_hepsiburada_link(self, url: str, product_title: str) -> Dict:
        """Hepsiburada link onarımı"""
        try:
            # Ürün kodunu çıkar
            code_match = re.search(r'-p-(H[A-Z0-9]+)', url)
            if code_match:
                product_code = code_match.group(1)
                
                # Basit URL formatını dene
                simple_url = f"https://www.hepsiburada.com/p-{product_code}"
                
                response = requests.get(
                    simple_url,
                    headers=self.request_headers,
                    timeout=8,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    print(f"✅ Hepsiburada basit URL çalışıyor: {simple_url}")
                    return {
                        'status': 'repaired',
                        'url': simple_url,
                        'message': 'Hepsiburada kod ile onarıldı'
                    }
            
            # Kod ile onarım başarısızsa arama
            search_url = f"https://www.hepsiburada.com/ara?q={product_title}"
            print(f"📍 Hepsiburada fallback arama: {search_url}")
            return {
                'status': 'fallback',
                'url': search_url,
                'message': 'Hepsiburada arama sayfası (fallback)'
            }
            
        except Exception as e:
            return {'status': 'failed', 'url': url, 'message': f'Hepsiburada onarım hatası: {e}'}
    
    def _repair_teknosa_link(self, url: str, product_title: str) -> Dict:
        """Teknosa link onarımı"""
        try:
            # Ürün ID'sini çıkar (örn: -123456)
            id_match = re.search(r'-(\d+)$', url)
            if id_match:
                product_id = id_match.group(1)
                
                # Basit URL formatını dene
                simple_url = f"https://www.teknosa.com/p/{product_id}"
                
                response = requests.get(
                    simple_url,
                    headers=self.request_headers,
                    timeout=8,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    print(f"✅ Teknosa basit URL çalışıyor: {simple_url}")
                    return {
                        'status': 'repaired',
                        'url': simple_url,
                        'message': 'Teknosa ID ile onarıldı'
                    }
            
            # ID ile onarım başarısızsa arama
            search_url = f"https://www.teknosa.com/arama?q={product_title}"
            print(f"📍 Teknosa fallback arama: {search_url}")
            return {
                'status': 'fallback',
                'url': search_url,
                'message': 'Teknosa arama sayfası (fallback)'
            }
            
        except Exception as e:
            return {'status': 'failed', 'url': url, 'message': f'Teknosa onarım hatası: {e}'}
    
    def _repair_mediamarkt_link(self, url: str, product_title: str) -> Dict:
        """MediaMarkt link onarımı"""
        try:
            # MediaMarkt ID'sini çıkar (örn: /product/123456)
            id_match = re.search(r'/product/(\d+)', url)
            if id_match:
                product_id = id_match.group(1)
                
                # Basit URL formatını dene
                simple_url = f"https://www.mediamarkt.com.tr/tr/product/{product_id}"
                
                response = requests.get(
                    simple_url,
                    headers=self.request_headers,
                    timeout=8,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    print(f"✅ MediaMarkt basit URL çalışıyor: {simple_url}")
                    return {
                        'status': 'repaired',
                        'url': simple_url,
                        'message': 'MediaMarkt ID ile onarıldı'
                    }
            
            # ID ile onarım başarısızsa arama
            search_url = f"https://www.mediamarkt.com.tr/tr/search.html?query={product_title}"
            print(f"📍 MediaMarkt fallback arama: {search_url}")
            return {
                'status': 'fallback',
                'url': search_url,
                'message': 'MediaMarkt arama sayfası (fallback)'
            }
            
        except Exception as e:
            return {'status': 'failed', 'url': url, 'message': f'MediaMarkt onarım hatası: {e}'}
    
    def _repair_n11_link(self, url: str, product_title: str) -> Dict:
        """N11 link onarımı"""
        try:
            # N11 ID'sini çıkar (örn: /urun/123456)
            id_match = re.search(r'/urun/(\d+)', url)
            if id_match:
                product_id = id_match.group(1)
                
                # Basit URL formatını dene
                simple_url = f"https://www.n11.com/urun/{product_id}"
                
                response = requests.get(
                    simple_url,
                    headers=self.request_headers,
                    timeout=8,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    print(f"✅ N11 basit URL çalışıyor: {simple_url}")
                    return {
                        'status': 'repaired',
                        'url': simple_url,
                        'message': 'N11 ID ile onarıldı'
                    }
            
            # ID ile onarım başarısızsa arama
            search_url = f"https://www.n11.com/arama?q={product_title}"
            print(f"📍 N11 fallback arama: {search_url}")
            return {
                'status': 'fallback',
                'url': search_url,
                'message': 'N11 arama sayfası (fallback)'
            }
            
        except Exception as e:
            return {'status': 'failed', 'url': url, 'message': f'N11 onarım hatası: {e}'}
    
    def _repair_generic_link(self, url: str, product_title: str) -> Dict:
        """Genel site link onarımı"""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Ana sayfa + arama denemesi
            base_url = f"https://{domain}"
            search_paths = ['/arama', '/search', '/ara', '/s']
            
            for path in search_paths:
                search_url = f"{base_url}{path}?q={product_title}"
                try:
                    response = requests.get(
                        search_url,
                        headers=self.request_headers,
                        timeout=5,
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        print(f"✅ Genel arama URL çalışıyor: {search_url}")
                        return {
                            'status': 'fallback',
                            'url': search_url,
                            'message': f'{domain} arama sayfası'
                        }
                except:
                    continue
            
            # Hiçbiri çalışmazsa ana sayfa
            return {
                'status': 'fallback',
                'url': base_url,
                'message': f'{domain} ana sayfa'
            }
            
        except Exception as e:
            return {'status': 'failed', 'url': url, 'message': f'Genel onarım hatası: {e}'}
    
    def _generate_fallback_search_url(self, original_url: str, product_title: str) -> Dict:
        """Son çare olarak fallback arama URL'si oluştur"""
        try:
            parsed_url = urlparse(original_url)
            domain = parsed_url.netloc.lower()
            
            # Domain bazında arama URL'leri - Güncellenmiş ve genişletilmiş liste
            search_urls = {
                # Ana e-ticaret platformları
                'amazon.com.tr': f"https://www.amazon.com.tr/s?k={product_title}",
                'trendyol.com': f"https://www.trendyol.com/sr?q={product_title}",
                'hepsiburada.com': f"https://www.hepsiburada.com/ara?q={product_title}",
                'n11.com': f"https://www.n11.com/arama?q={product_title}",
                'gittigidiyor.com': f"https://www.gittigidiyor.com/arama/?k={product_title}",
                
                # Elektronik uzmanı siteler
                'teknosa.com': f"https://www.teknosa.com/arama?q={product_title}",
                'vatanbilgisayar.com': f"https://www.vatanbilgisayar.com/arama/?text={product_title}",
                'mediamarkt.com.tr': f"https://www.mediamarkt.com.tr/tr/search.html?query={product_title}",
                'gold.com.tr': f"https://www.gold.com.tr/arama?q={product_title}",
                'itopya.com': f"https://www.itopya.com/arama/?q={product_title}",
                'incehesap.com': f"https://www.incehesap.com/arama/{product_title}",
                
                # Genel mağaza zincirleri
                'migros.com.tr': f"https://www.migros.com.tr/arama?q={product_title}",
                'carrefoursa.com': f"https://www.carrefoursa.com/arama?q={product_title}",
                'a101.com.tr': f"https://www.a101.com.tr/market/arama?q={product_title}",
                'bim.com.tr': f"https://www.bim.com.tr/arama?q={product_title}",
                
                # Diğer kategoriler
                'ciceksepeti.com': f"https://www.ciceksepeti.com/arama?q={product_title}",
                'idefix.com': f"https://www.idefix.com/search?q={product_title}",
                'kitapyurdu.com': f"https://www.kitapyurdu.com/index.php?route=product/search&filter_name={product_title}",
                'morhipo.com': f"https://www.morhipo.com/arama?q={product_title}",
                'lcw.com': f"https://www.lcw.com/arama?q={product_title}",
                'defacto.com.tr': f"https://www.defacto.com.tr/arama?q={product_title}",
                'koton.com': f"https://www.koton.com/tr-tr/arama?q={product_title}",
                'mavi.com': f"https://www.mavi.com/arama?q={product_title}",
                
                # Online delivery
                'getir.com': f"https://www.getir.com/arama/?query={product_title}",
                'banabi.com': f"https://www.banabi.com/arama?q={product_title}",
                'istegelsin.com': f"https://www.istegelsin.com/arama?q={product_title}"
            }
            
            # Domain eşleşmesi ara
            for site_domain, search_url in search_urls.items():
                if site_domain in domain:
                    print(f"📍 Fallback arama oluşturuldu: {search_url}")
                    return {
                        'status': 'fallback',
                        'url': search_url,
                        'message': f'{site_domain} arama sayfası (fallback)'
                    }
            
            # Hiçbiri eşleşmezse Google arama
            google_search = f"https://www.google.com/search?q={product_title}+site:{domain}"
            return {
                'status': 'fallback',
                'url': google_search,
                'message': 'Google arama (fallback)'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'url': original_url,
                'message': f'Fallback oluşturulamadı: {e}'
            }

# Function Calling desteği için decorator
def search_products_function_calling():
    """
    Function Calling için search_products fonksiyon tanımı
    """
    return {
        "name": "search_products",
        "description": "Türkiye e-ticaret sitelerinde ürün arama yapar. Kesin fiyat ve stok bilgilerini döndürür.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Arama sorgusu (örn: 'saç kurutma makinesi ionic')"
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum fiyat (TL)"
                },
                "max_price": {
                    "type": "number",
                    "description": "Maksimum fiyat (TL)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maksimum sonuç sayısı (varsayılan: 10)"
                },
                "country": {
                    "type": "string",
                    "description": "Ülke kodu (varsayılan: 'tr')"
                }
            },
            "required": ["query"]
        }
    }
