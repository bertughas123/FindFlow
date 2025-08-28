"""
FindFlow Yapılandırma Modülü
=======================================

Bu modül, FindFlow uygulamasının Gemini AI yapılandırması ve yardımcı fonksiyonlarını içerir.SwipeStyle Yapılandırma Modülü
==============================

Bu modül, SwipeStyle uygulamasının Gemini AI yapılandırması ve yardımcı fonksiyonlarını içerir.
Gemini API'yi yapılandırır, model nesnelerini oluşturur ve retry mekanizmaları sağlar.

Ana Fonksiyonlar:
- setup_gemini(): Gemini API'yi yapılandırır
- get_gemini_model(): Optimize edilmiş Gemini modeli döner
- generate_with_retry(): Retry mekanizması ile API istekleri gönderir

Özellikler:
- Otomatik API yapılandırması
- Optimize edilmiş model parametreleri
- Exponential backoff retry mekanizması
- Hata yönetimi ve loglama

Gereksinimler:
- Google Generative AI (Gemini)
- .env dosyasında GEMINI_API_KEY
- python-dotenv paketi
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
import time

def setup_gemini():
    """
    Gemini API'yi yapılandırır ve başlatır - FindFlow için optimize edilmiş.
    
    .env dosyasından API anahtarını okur ve Gemini API'yi yapılandırır.
    Başarılı yapılandırma durumunda True, başarısız durumda False döner.
    
    Returns:
        bool: Yapılandırma başarılı mı?
        
    Örnek:
        >>> if setup_gemini():
        ...     print("Gemini API başarıyla yapılandırıldı")
        ... else:
        ...     print("Gemini API yapılandırılamadı")
    """
    load_dotenv()
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        return True
    return False

def get_gemini_model():
    """
    Optimize edilmiş Gemini modeli döner.
    
    FindFlow uygulaması için özel olarak yapılandırılmış
    Gemini modeli oluşturur. Sıcaklık, top_p, top_k ve
    max_output_tokens parametreleri optimize edilmiştir.
    
    Returns:
        genai.GenerativeModel: Yapılandırılmış Gemini modeli
        
    Örnek:
        >>> model = get_gemini_model()
        >>> response = model.generate_content("Merhaba")
    """
    # Relaxed safety settings to prevent empty responses
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE"
        }
    ]
    
    return genai.GenerativeModel(
        'gemini-1.5-flash',  # Daha yüksek limit: 1000 req/min vs 10 req/min
        generation_config=genai.types.GenerationConfig(
            temperature=0.8,  # Increased for more creative responses
            top_p=0.95,      # Increased for more diverse responses
            top_k=40,        # Increased for more variety
            max_output_tokens=4096,  # Increased for longer responses
        ),
        safety_settings=safety_settings
    )

def generate_with_retry(model, prompt, max_retries=2, delay=10):
    """
    Gemini API'ye retry mekanizması ile istek gönderir.
    
    Bu fonksiyon, API isteklerini güvenilir hale getirmek için
    exponential backoff retry mekanizması kullanır. Her başarısız
    denemeden sonra bekleme süresi artırılır.
    
    Args:
        model (genai.GenerativeModel): Gemini model nesnesi
        prompt (str): AI'ya gönderilecek prompt metni
        max_retries (int): Maksimum deneme sayısı (varsayılan: 3)
        delay (int): İlk deneme arası bekleme süresi (varsayılan: 2)
        
    Returns:
        genai.types.GenerateContentResponse or None: API yanıtı veya None
        
    Raises:
        Exception: Tüm denemeler başarısız olduğunda
        
    Örnek:
        >>> model = get_gemini_model()
        >>> response = generate_with_retry(model, "Kategori önerisi yap")
        >>> if response:
        ...     print(response.text)
    """
    for attempt in range(max_retries):
        try:
            print(f"🔄 Gemini API isteği (deneme {attempt + 1}/{max_retries})")
            response = model.generate_content(prompt)
            
            # Detailed response checking
            if response and hasattr(response, 'text') and response.text:
                print(f"✅ Gemini API başarılı (deneme {attempt + 1})")
                print(f"📄 Response length: {len(response.text)} characters")
                return response
            elif response and hasattr(response, 'candidates') and response.candidates:
                # Check if response was blocked
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    print(f"⚠️ Response blocked: {candidate.finish_reason} (deneme {attempt + 1})")
                    if hasattr(candidate, 'safety_ratings'):
                        print(f"🛡️ Safety ratings: {candidate.safety_ratings}")
                else:
                    print(f"⚠️ Boş yanıt alındı (deneme {attempt + 1})")
            else:
                print(f"⚠️ Geçersiz response objesi (deneme {attempt + 1})")
                
        except Exception as e:
            print(f"❌ Gemini API hatası (deneme {attempt + 1}): {e}")
            
        # Wait before retry (except on last attempt)
        if attempt < max_retries - 1:
            print(f"⏳ {delay} saniye bekleniyor...")
            time.sleep(delay)
            delay *= 1.5  # Exponential backoff
    
    print(f"❌ Tüm denemeler başarısız oldu ({max_retries} deneme)")
    return None
