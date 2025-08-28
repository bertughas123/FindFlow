/**
 * FindFlow Frontend JavaScript
 * Basit ve temiz JavaScript kodu
 */

// Global dil değişkeni
let currentLanguage = 'tr';
let currentTheme = 'light';  // Default light theme
let currentCategory = ''; // Global kategori değişkeni
let currentQuestionIndex = 0;
let totalQuestions = 7;

// Otomatik tamamlama için global değişkenler
let autocompleteData = [];
let selectedAutocompleteIndex = -1;

// Tema değiştirme fonksiyonu
function changeTheme(theme) {
    currentTheme = theme;
    
    // HTML'e tema attribute'u ekle
    document.documentElement.setAttribute('data-theme', theme);
    
    // Theme switch'i güncelle
    document.querySelectorAll('.theme-switch').forEach(switch_el => {
        switch_el.dataset.theme = theme;
        if (theme === 'dark') {
            switch_el.classList.add('active');
        } else {
            switch_el.classList.remove('active');
        }
    });
    
    // LocalStorage'a kaydet
    localStorage.setItem('findflow-theme', theme);
}

// Dil değiştirme fonksiyonu
function changeLanguage(lang) {
    currentLanguage = lang;
    
    // Dil butonlarını güncelle
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.lang === lang) {
            btn.classList.add('active');
        }
    });
    
    // Tüm çevrilebilir elementleri güncelle
    document.querySelectorAll('[data-tr], [data-en]').forEach(element => {
        const trText = element.dataset.tr;
        const enText = element.dataset.en;
        
        if (lang === 'tr' && trText) {
            element.textContent = trText;
        } else if (lang === 'en' && enText) {
            element.textContent = enText;
        }
    });
    
    // Placeholder'ları güncelle
    document.querySelectorAll('[data-tr-placeholder], [data-en-placeholder]').forEach(element => {
        const trPlaceholder = element.dataset.trPlaceholder;
        const enPlaceholder = element.dataset.enPlaceholder;
        
        if (lang === 'tr' && trPlaceholder) {
            element.placeholder = trPlaceholder;
        } else if (lang === 'en' && enPlaceholder) {
            element.placeholder = enPlaceholder;
        }
    });
    
    // Kategorileri yeniden yükle
    loadCategories();
}

function handleChatboxEntry() {
    const input = document.getElementById('chatbox-input').value.trim();
    if (!input) {
        const alertMsg = currentLanguage === 'tr' ? 'Lütfen bir ürün yazın' : 'Please enter a product';
        alert(alertMsg);
        return;
    }
    
    // Modern AI creation screen göster
    showAICreationScreen();
    
    // API çağrısı
    fetch('/detect_category', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input })
    })
    .then(res => res.json())
    .then(data => {
        hideAICreationScreen();
        
        if (data.category) {
            category = data.category;
            currentCategory = data.category; // Global kategoriyi güncelle
            step = 1;
            answers = [];
            
            // Modern geçiş
            document.querySelector('.landing').style.display = 'none';
            document.getElementById('interaction').style.display = '';
            askAgent();
        } else {
            showErrorScreen();
        }
    })
    .catch(error => {
        console.error("Arama hatası:", error);
        hideAICreationScreen();
        showErrorScreen();
    });
}

let step = 0;
let category = null;
let answers = [];

// Mevcut kategoriyi döndüren yardımcı fonksiyon
function getCurrentCategory() {
    return currentCategory || category || '';
}

// Ürün başlığından marka çıkarma fonksiyonu
function extractBrand(productTitle) {
    const title = productTitle.toLowerCase();
    const brandKeywords = [
        'sony', 'bose', 'apple', 'samsung', 'lg', 'sennheiser', 'beats', 
        'xiaomi', 'huawei', 'oppo', 'oneplus', 'realme', 'vivo', 'iphone',
        'airpods', 'galaxy', 'pixel', 'redmi', 'poco', 'honor',
        'jbl', 'marshall', 'audio-technica', 'beyerdynamic', 'akg',
        'skullcandy', 'plantronics', 'jabra', 'razer', 'steelseries',
        'hyperx', 'corsair', 'logitech', 'asus', 'msi', 'acer', 'hp',
        'dell', 'lenovo', 'macbook', 'thinkpad', 'pavilion', 'inspiron'
    ];
    
    for (const brand of brandKeywords) {
        if (title.includes(brand)) {
            return brand;
        }
    }
    return null;
}

// Ürün başlığından model çıkarma fonksiyonu  
function extractModel(productTitle) {
    const title = productTitle.toLowerCase();
    
    // Model pattern'leri (sayı kombinasyonları)
    const modelPatterns = [
        /\b\d{1,2}[a-z]*\b/g,  // 12, 12a, 13pro gibi
        /\b[a-z]+\s*\d+[a-z]*\b/g,  // pro max 12, air 3 gibi
        /\b\d+\s*[a-z]+\b/g  // 12 pro, 3 max gibi
    ];
    
    for (const pattern of modelPatterns) {
        const matches = title.match(pattern);
        if (matches && matches.length > 0) {
            return matches[0];
        }
    }
    return null;
}

const categoryIcons = {
    'Drone': 'fas fa-plane',
    'Headphones': 'fas fa-headphones',
    'Keyboard': 'fas fa-keyboard',
    'Air Conditioner': 'fas fa-snowflake',
    'Phone': 'fas fa-mobile-alt',
    'Television': 'fas fa-tv',
    'Mouse': 'fas fa-mouse',
    'Laptop': 'fas fa-laptop',
    'Monitor': 'fas fa-desktop',
    'Tablet': 'fas fa-tablet-alt',
    'Camera': 'fas fa-camera',
    'Speaker': 'fas fa-volume-up',
    'Smartwatch': 'fas fa-stopwatch'
};

// --- Akıllı Arama & Filtreleme Özelliği ---
// Not: HTML kısmını main.html dosyasına eklemelisin (bkz. açıklama)

// Örnek teknolojik ürün verisi (backend'den de çekilebilir)
const products = [
  { name: "Mouse", color: "siyah", size: "M", price: 399, rating: 4.6 },
  { name: "Laptop", color: "gri", size: "L", price: 15999, rating: 4.8 },
  { name: "Telefon", color: "mavi", size: "M", price: 10999, rating: 4.7 },
  { name: "Kulaklık", color: "siyah", size: "S", price: 799, rating: 4.3 },
  { name: "Monitör", color: "beyaz", size: "L", price: 2999, rating: 4.5 },
  { name: "Klavye", color: "siyah", size: "M", price: 599, rating: 4.2 },
  { name: "Tablet", color: "gri", size: "M", price: 4999, rating: 4.4 },
  { name: "Kamera", color: "siyah", size: "S", price: 3499, rating: 4.1 },
  { name: "Hoparlör", color: "kırmızı", size: "S", price: 699, rating: 4.0 },
  { name: "Akıllı Saat", color: "siyah", size: "S", price: 1999, rating: 4.6 }
];

// Ürünleri ekrana bas
function displayProducts(filtered) {
  const productList = document.getElementById("product-list");
  if (!productList) return;
  productList.innerHTML = "";
  filtered.forEach(p => {
    const div = document.createElement("div");
    div.className = "product";
    div.textContent = `${p.name} | Renk: ${p.color} | Beden: ${p.size} | ₺${p.price} | ⭐${p.rating}`;
    productList.appendChild(div);
  });
}

// Filtreleme fonksiyonu
function filterProducts() {
  const inputEl = document.getElementById("product-search-input");
  const colorEl = document.getElementById("color-filter");
  const sizeEl = document.getElementById("size-filter");
  const ratingEl = document.getElementById("rating-filter");
  if (!inputEl || !colorEl || !sizeEl || !ratingEl) return;
  const input = inputEl.value.toLowerCase();
  const color = colorEl.value;
  const size = sizeEl.value;
  const rating = parseFloat(ratingEl.value) || 0;

  const filtered = products.filter(p =>
    p.name.toLowerCase().includes(input) &&
    (color === "" || p.color === color) &&
    (size === "" || p.size === size) &&
    p.rating >= rating
  );
  displayProducts(filtered);
}

// Otomatik tamamlama
function setupSmartSearchEvents() {
  const inputEl = document.getElementById("product-search-input");
  const suggestionsDiv = document.getElementById("product-suggestions");
  if (!inputEl || !suggestionsDiv) return;
  inputEl.addEventListener("input", () => {
    const input = inputEl.value.toLowerCase();
    const matched = products
      .map(p => p.name)
      .filter(name => name.toLowerCase().startsWith(input));
    suggestionsDiv.innerHTML = matched.length > 0 ? matched.join(", ") : "";
    filterProducts();
  });
}

function setupFilterEvents() {
  const colorEl = document.getElementById("color-filter");
  const sizeEl = document.getElementById("size-filter");
  const ratingEl = document.getElementById("rating-filter");
  if (colorEl) colorEl.addEventListener("change", filterProducts);
  if (sizeEl) sizeEl.addEventListener("change", filterProducts);
  if (ratingEl) ratingEl.addEventListener("change", filterProducts);
}

// Sayfa yüklendiğinde smart search alanı varsa başlat
window.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById("product-search-input")) {
    setupSmartSearchEvents();
    setupFilterEvents();
    displayProducts(products);
  }
});

// Açıklama: HTML tarafına şunu eklemelisin (örnek):
// <div class="smart-search">
//   <input type="text" id="product-search-input" placeholder="Ürün Ara (örn: ka)">
//   <select id="color-filter"> ... </select>
//   <select id="size-filter"> ... </select>
//   <select id="rating-filter"> ... </select>
//   <div id="product-suggestions"></div>
// </div>
// <div id="product-list"></div>

// Otomatik tamamlama verileri
const autocompleteSuggestions = {
    'k': [
        { text: 'Kulaklık', icon: 'fas fa-headphones', category: 'Headphones' },
        { text: 'Klavye', icon: 'fas fa-keyboard', category: 'Keyboard' },
        { text: 'Klima', icon: 'fas fa-snowflake', category: 'Air Conditioner' }
    ],
    'ku': [
        { text: 'Kulaklık', icon: 'fas fa-headphones', category: 'Headphones' }
    ],
    'kul': [
        { text: 'Kulaklık', icon: 'fas fa-headphones', category: 'Headphones' }
    ],
    'kula': [
        { text: 'Kulaklık', icon: 'fas fa-headphones', category: 'Headphones' }
    ],
    'kulak': [
        { text: 'Kulaklık', icon: 'fas fa-headphones', category: 'Headphones' }
    ],
    'kulakl': [
        { text: 'Kulaklık', icon: 'fas fa-headphones', category: 'Headphones' }
    ],
    'kulakli': [
        { text: 'Kulaklık', icon: 'fas fa-headphones', category: 'Headphones' }
    ],
    'kulaklik': [
        { text: 'Kulaklık', icon: 'fas fa-headphones', category: 'Headphones' }
    ],
    'kulaklık': [
        { text: 'Kulaklık', icon: 'fas fa-headphones', category: 'Headphones' }
    ],
    'kl': [
        { text: 'Klima', icon: 'fas fa-snowflake', category: 'Air Conditioner' },
        { text: 'Klavye', icon: 'fas fa-keyboard', category: 'Keyboard' }
    ],
    'kli': [
        { text: 'Klima', icon: 'fas fa-snowflake', category: 'Air Conditioner' }
    ],
    'klim': [
        { text: 'Klima', icon: 'fas fa-snowflake', category: 'Air Conditioner' }

    ],
    'l': [
        { text: 'Laptop', icon: 'fas fa-laptop', category: 'Laptop' }
    ],
    'la': [
        { text: 'Laptop', icon: 'fas fa-laptop', category: 'Laptop' }
    ],
    'lap': [
        { text: 'Laptop', icon: 'fas fa-laptop', category: 'Laptop' }
    ],
    'lapt': [
        { text: 'Laptop', icon: 'fas fa-laptop', category: 'Laptop' }
    ],
    'lapto': [
        { text: 'Laptop', icon: 'fas fa-laptop', category: 'Laptop' }
    ],
    'laptop': [
        { text: 'Laptop', icon: 'fas fa-laptop', category: 'Laptop' }
    ],
    'm': [
        { text: 'Mouse', icon: 'fas fa-mouse', category: 'Mouse' },
        { text: 'Mikrofon', icon: 'fas fa-microphone', category: 'Microphone' },
        { text: 'Monitör', icon: 'fas fa-desktop', category: 'Monitor' }
    ],
    'mo': [
        { text: 'Mouse', icon: 'fas fa-mouse', category: 'Mouse' },
        { text: 'Monitör', icon: 'fas fa-desktop', category: 'Monitor' }
    ],
    'mi': [
        { text: 'Mikrofon', icon: 'fas fa-microphone', category: 'Microphone' }
    ],
    'mik': [
        { text: 'Mikrofon', icon: 'fas fa-microphone', category: 'Microphone' }
    ],
    'mikr': [
        { text: 'Mikrofon', icon: 'fas fa-microphone', category: 'Microphone' }
    ],
    'mikro': [
        { text: 'Mikrofon', icon: 'fas fa-microphone', category: 'Microphone' }
    ],
    'mikrof': [
        { text: 'Mikrofon', icon: 'fas fa-microphone', category: 'Microphone' }
    ],
    'mikrofo': [
        { text: 'Mikrofon', icon: 'fas fa-microphone', category: 'Microphone' }
    ],
    'mikrofon': [
        { text: 'Mikrofon', icon: 'fas fa-microphone', category: 'Microphone' }
    ],
    'mon': [
        { text: 'Monitör', icon: 'fas fa-desktop', category: 'Monitor' }
    ],
    'moni': [
        { text: 'Monitör', icon: 'fas fa-desktop', category: 'Monitor' }
    ],
    'monit': [
        { text: 'Monitör', icon: 'fas fa-desktop', category: 'Monitor' }
    ],
    'monito': [
        { text: 'Monitör', icon: 'fas fa-desktop', category: 'Monitor' }
    ],
    'monitor': [
        { text: 'Monitör', icon: 'fas fa-desktop', category: 'Monitor' }
    ],
    'monitör': [
        { text: 'Monitör', icon: 'fas fa-desktop', category: 'Monitor' }
    ],
    'mou': [
        { text: 'Mouse', icon: 'fas fa-mouse', category: 'Mouse' }
    ],
    'mous': [
        { text: 'Mouse', icon: 'fas fa-mouse', category: 'Mouse' }
    ],
    'mouse': [
        { text: 'Mouse', icon: 'fas fa-mouse', category: 'Mouse' }

    ],
    't': [
        { text: 'Telefon', icon: 'fas fa-mobile-alt', category: 'Phone' },
        { text: 'Tablet', icon: 'fas fa-tablet-alt', category: 'Tablet' },
        { text: 'TV', icon: 'fas fa-tv', category: 'TV' },
        { text: 'Televizyon', icon: 'fas fa-tv', category: 'TV' }
    ],
    'te': [
        { text: 'Telefon', icon: 'fas fa-mobile-alt', category: 'Phone' },
        { text: 'TV', icon: 'fas fa-tv', category: 'TV' },
        { text: 'Televizyon', icon: 'fas fa-tv', category: 'TV' }
    ],
    'tel': [
        { text: 'Telefon', icon: 'fas fa-mobile-alt', category: 'Phone' },
        { text: 'TV', icon: 'fas fa-tv', category: 'TV' },
        { text: 'Televizyon', icon: 'fas fa-tv', category: 'TV' }
    ],
    'tele': [
        { text: 'Telefon', icon: 'fas fa-mobile-alt', category: 'Phone' },
        { text: 'TV', icon: 'fas fa-tv', category: 'TV' },
        { text: 'Televizyon', icon: 'fas fa-tv', category: 'TV' }
    ],
    'telef': [
        { text: 'Telefon', icon: 'fas fa-mobile-alt', category: 'Phone' }
    ],
    'telefo': [
        { text: 'Telefon', icon: 'fas fa-mobile-alt', category: 'Phone' }
    ],
    'telefon': [
        { text: 'Telefon', icon: 'fas fa-mobile-alt', category: 'Phone' }
    ]
};

// Kategori isimlerini çevir
const categoryTranslations = {
    'Mouse': { tr: 'Mouse', en: 'Mouse' },
    'Headphones': { tr: 'Kulaklık', en: 'Headphones' },
    'Phone': { tr: 'Telefon', en: 'Phone' },
    'Laptop': { tr: 'Laptop', en: 'Laptop' },
    'Keyboard': { tr: 'Klavye', en: 'Keyboard' },
    'Monitor': { tr: 'Monitör', en: 'Monitor' },
    'Speaker': { tr: 'Hoparlör', en: 'Speaker' },
    'Camera': { tr: 'Kamera', en: 'Camera' },
    'Tablet': { tr: 'Tablet', en: 'Tablet' },
    'Smartwatch': { tr: 'Akıllı Saat', en: 'Smartwatch' },
    'Air Conditioner': { tr: 'Klima', en: 'Air Conditioner' },
    'Drone': { tr: 'Drone', en: 'Drone' },
    'Television': { tr: 'Televizyon', en: 'Television' }
};

// Otomatik tamamlama fonksiyonları
function handleAutocomplete() {
    const input = document.getElementById('chatbox-input');
    const dropdown = document.getElementById('autocomplete-dropdown');
    const query = input.value.toLowerCase().trim();
    
    if (query.length < 1) {
        hideAutocomplete();
        return;
    }
    
    // Önerileri bul
    const suggestions = getAutocompleteSuggestions(query);
    
    if (suggestions.length > 0) {
        showAutocompleteSuggestions(suggestions);
    } else {
        hideAutocomplete();
    }
}

function getAutocompleteSuggestions(query) {
    const suggestions = [];
    if (!query) return suggestions;

    // Regex ile anahtar eşleşmesi (başlangıç veya tam eşleşme)
    const keyRegex = new RegExp('^' + query, 'i');
    Object.keys(autocompleteSuggestions).forEach(key => {
        if (keyRegex.test(key)) {
            autocompleteSuggestions[key].forEach(suggestion => {
                if (!suggestions.some(s => s.text === suggestion.text)) {
                    suggestions.push(suggestion);
                }
            });
        }
    });

    // Regex ile ürün adında geçenler (herhangi bir yerde)
    const textRegex = new RegExp(query, 'i');
    Object.values(autocompleteSuggestions).forEach(categorySuggestions => {
        categorySuggestions.forEach(suggestion => {
            if (textRegex.test(suggestion.text) && !suggestions.some(s => s.text === suggestion.text)) {
                suggestions.push(suggestion);
            }
        });
    });

    return suggestions.slice(0, 8); // Maksimum 8 öneri
}

function showAutocompleteSuggestions(suggestions) {
    const dropdown = document.getElementById('autocomplete-dropdown');
    
    dropdown.innerHTML = '';
    autocompleteData = suggestions; // Global değişkene ata
    
    suggestions.forEach((suggestion, index) => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.setAttribute('data-index', index);
        item.setAttribute('data-category', suggestion.category);
        
        item.innerHTML = `
            <span>${suggestion.text}</span>
            <i class="${suggestion.icon} icon" title="${suggestion.category}"></i>
        `;
        
        item.addEventListener('mousedown', () => {
            selectAutocompleteItem(suggestion);
        });
        
        item.addEventListener('mouseenter', () => {
            selectAutocompleteIndex(index);
        });
        
        // Add subtle animation delay for each item
        item.style.animationDelay = `${index * 0.05}s`;
        item.style.animation = 'fadeInUp 0.3s ease forwards';
        
        dropdown.appendChild(item);
    });
    
    dropdown.style.display = 'block';
    selectedAutocompleteIndex = -1;
}

function hideAutocomplete() {
    const dropdown = document.getElementById('autocomplete-dropdown');
    dropdown.style.display = 'none';
    selectedAutocompleteIndex = -1;
}

function selectAutocompleteIndex(index) {
    const items = document.querySelectorAll('.autocomplete-item');
    
    // Önceki seçimi temizle
    items.forEach(item => item.classList.remove('selected'));
    
    if (index >= 0 && index < items.length) {
        items[index].classList.add('selected');
        selectedAutocompleteIndex = index;
    }
}

function selectAutocompleteItem(suggestion) {
    const input = document.getElementById('chatbox-input');
    input.value = suggestion.text;
    hideAutocomplete();
    
    // Otomatik olarak arama yap
    handleChatboxEntry();
}

function handleAutocompleteKeydown(e) {
    const dropdown = document.getElementById('autocomplete-dropdown');
    const items = document.querySelectorAll('.autocomplete-item');
    
    if (dropdown.style.display === 'none') return;
    
    switch (e.key) {
        case 'ArrowDown':
            e.preventDefault();
            selectedAutocompleteIndex = Math.min(selectedAutocompleteIndex + 1, items.length - 1);
            selectAutocompleteIndex(selectedAutocompleteIndex);
            break;
            
        case 'ArrowUp':
            e.preventDefault();
            selectedAutocompleteIndex = Math.max(selectedAutocompleteIndex - 1, -1);
            selectAutocompleteIndex(selectedAutocompleteIndex);
            break;
            
        case 'Enter':
            e.preventDefault();
            if (selectedAutocompleteIndex >= 0 && selectedAutocompleteIndex < items.length) {
                const selectedItem = items[selectedAutocompleteIndex];
                const suggestion = autocompleteData[selectedAutocompleteIndex];
                if (suggestion) {
                    selectAutocompleteItem(suggestion);
                }
            } else {
                handleChatboxEntry();
            }
            break;
            
        case 'Escape':
            hideAutocomplete();
            break;
    }
}

function getCategoryName(categoryName) {
    const translation = categoryTranslations[categoryName];
    if (translation) {
        return translation[currentLanguage] || categoryName;
    }
    return categoryName;
}

function loadCategories() {
    fetch('/categories')
        .then(res => res.json())
        .then(data => {
            const categories = Object.keys(data);
            renderLanding(categories);
        })
        .catch(error => {
            console.error("Kategoriler yüklenirken hata:", error);
        });
}

function renderLanding(categories) {
    const grid = document.getElementById('category-cards');
    grid.innerHTML = '';
    
    categories.forEach(cat => {
        const card = document.createElement('div');
        card.className = 'category-card';
        card.onclick = () => startInteraction(cat);
        
        const icon = document.createElement('div');
        icon.className = 'category-icon';
        
        // Font Awesome ikonu için
        const iconElement = document.createElement('i');
        iconElement.className = categoryIcons[cat] || 'fas fa-search';
        icon.appendChild(iconElement);
        
        const label = document.createElement('div');
        label.className = 'category-label';
        label.textContent = getCategoryName(cat);
        
        card.appendChild(icon);
        card.appendChild(label);
        grid.appendChild(card);
    });
    
    // Event listeners
    const chatboxSend = document.getElementById('chatbox-send');
    const chatboxInput = document.getElementById('chatbox-input');
    if (chatboxSend && chatboxInput) {
        chatboxSend.onclick = handleChatboxEntry;
        chatboxInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') handleChatboxEntry();
        });
    }
}

function startInteraction(selectedCategory) {
    category = selectedCategory;
    currentCategory = selectedCategory; // Global kategoriyi güncelle
    step = 1;
    answers = [];
    currentQuestionIndex = 1;
    
    // Get total questions from category specs
    if (window.currentSpecs && window.currentSpecs[selectedCategory]) {
        totalQuestions = window.currentSpecs[selectedCategory].length;
    } else {
        totalQuestions = 5; // fallback
    }
    
    // Basit geçiş
    document.querySelector('.landing').style.display = 'none';
    document.getElementById('interaction').style.display = '';
    askAgent();
}

// Question progress functions
function updateQuestionProgress() {
    const currentElement = document.getElementById('current-question');
    const totalElement = document.getElementById('total-questions');
    
    if (currentElement && totalElement) {
        currentElement.textContent = currentQuestionIndex;
        totalElement.textContent = totalQuestions;
    }
}

function updateQuestionIcon(emoji) {
    const iconElement = document.querySelector('.question-icon i');
    if (iconElement && emoji) {
        // Map emoji to FontAwesome icon with better icons
        const iconMap = {
            '📍': 'fas fa-map-marker-alt',
            '💰': 'fas fa-dollar-sign',
            '🏢': 'fas fa-building',
            '⚡': 'fas fa-bolt',
            '🖥️': 'fas fa-desktop',
            '📱': 'fas fa-mobile-alt',
            '🎮': 'fas fa-gamepad',
            '🎵': 'fas fa-music',
            '💡': 'fas fa-lightbulb',
            '🔧': 'fas fa-wrench',
            '📐': 'fas fa-ruler-combined',
            '🌈': 'fas fa-palette',
            '⌨️': 'fas fa-keyboard',
            '🖱️': 'fas fa-mouse',
            '🔍': 'fas fa-search',
            '❓': 'fas fa-question-circle',
            '📊': 'fas fa-chart-bar',
            '🔥': 'fas fa-fire',
            '⭐': 'fas fa-star',
            '🎯': 'fas fa-bullseye'
        };
        
        const iconClass = iconMap[emoji] || 'fas fa-question-circle';
        iconElement.className = iconClass;
    } else if (iconElement) {
        // Default icon for category
        const categoryIcon = categoryIcons[getCurrentCategory()] || 'fas fa-search';
        iconElement.className = categoryIcon;
    }
}

// Go to home page function - removed duplicate, using detailed version below

function renderQuestion(question, options, emoji) {
    const interaction = document.getElementById('interaction');
    
    // Update question progress
    currentQuestionIndex = step;
    updateQuestionProgress();
    
    // Update question icon
    updateQuestionIcon(emoji);
    
    // Update tooltip if available
    updateQuestionTooltip();
    
    const questionDiv = interaction.querySelector('.question');
    const optionsDiv = interaction.querySelector('.options');
    
    if (!questionDiv || !optionsDiv) {
        console.error("Question or options div not found!");
        const errorMsg = currentLanguage === 'tr' ? 'Sayfa yapısında sorun var. Lütfen sayfayı yenileyin.' : 'There is a problem with the page structure. Please refresh the page.';
        document.querySelector('.error').textContent = errorMsg;
        return;
    }
    
    questionDiv.innerHTML = question;
    optionsDiv.innerHTML = '';

    // Seçenekleri oluştur
    options.forEach(opt => {
        const button = document.createElement('button');
        button.className = 'option-btn';
        button.textContent = opt;
        button.addEventListener('click', function() {
            handleOption(opt);
        });
        optionsDiv.appendChild(button);
    });
    
    // Loading'i gizle
    const loadingDiv = interaction.querySelector('.loading');
    if (loadingDiv) loadingDiv.style.display = 'none';
    
    interaction.style.display = 'block';
}

function renderRecommendations(recs) {
    console.log("🎯 renderRecommendations called");
    console.log("📊 Recommendations data:", recs);

    hideAICreationScreen();
    const loadingElement = document.querySelector('.loading');
    if (loadingElement) loadingElement.style.display = 'none';

    const recDiv = document.querySelector('.recommendations');
    const titleText = currentLanguage === 'tr' ? 'Önerilen Ürünler' : 'Recommended Products';

    if (!recs || !Array.isArray(recs) || recs.length === 0) {
        console.error("❌ No valid recommendations to render");
        recDiv.innerHTML = `
            <div class="error-message">
                <h3>Ürün bulunamadı</h3>
                <p>Seçimlerinizle eşleşen ürün bulunamadı. Lütfen farklı seçenekler deneyin.</p>
            </div>`;
        return;
    }

    let html = `<h2><i class="fas fa-star"></i> ${titleText}</h2>`;

    recs.forEach((r, index) => {
        const productTitle = r.title || r.name || 'Ürün';
        const productPrice = r.price ? (typeof r.price === 'object' ? r.price.display : r.price) : 'Fiyat bilgisi yok';
        const productUrl = r.product_url || r.link || r.url || '#';
        const productDescription = r.why_recommended || r.description || '';
        const matchScore = r.match_score || 0;
        const sourceSite = r.source_site || 'Bilinmeyen Mağaza';
        const features = r.features || [];

        let featuresHtml = '';
        if (features.length > 0) {
            featuresHtml = features.map(feature => `<span class="product-tag">${feature}</span>`).join('');
        }

        const storeInfo = getStoreInfo(sourceSite);

        html += `
            <div class="recommendation-item">
                <div class="product-header">
                    <div class="product-info">
                        <h3 class="product-name">${productTitle}</h3>
                        <div class="match-badge">
                            <i class="fas fa-star"></i>
                            <span>${matchScore}% ${currentLanguage === 'tr' ? 'uygun' : 'match'}</span>
                        </div>
                    </div>
                    <div class="product-price">${productPrice}</div>
                </div>
                <div class="product-details">
                    <div class="product-tags">${featuresHtml}</div>
                    <p class="product-description">${productDescription}</p>
                </div>
                <div class="product-footer">
                    <a href="${productUrl}" target="_blank" rel="noopener noreferrer" class="store-button ${storeInfo.class}">
                        <i class="${storeInfo.icon}"></i>
                        <span>${sourceSite}'da Gör</span>
                    </a>
                </div>
            </div>
        `;
    });

    const backButtonText = currentLanguage === 'tr' ? 'Yeni Arama Yap' : 'New Search';
    html += `
        <div class="back-section" style="text-align: center; margin-top: 30px;">
            <button id="back-to-categories" class="back-btn">
                <i class="fas fa-arrow-left"></i> ${backButtonText}
            </button>
        </div>
    `;

    recDiv.innerHTML = html;
    document.querySelector('.error').textContent = '';

    document.getElementById('back-to-categories').onclick = () => {
        resetToLanding();
    };
}

function getStoreInfo(storeName) {
    const lowerCaseName = storeName.toLowerCase();
    if (lowerCaseName.includes('hepsiburada')) return { class: 'hepsiburada', icon: 'fas fa-shopping-cart' };
    if (lowerCaseName.includes('trendyol')) return { class: 'trendyol', icon: 'fas fa-store' };
    if (lowerCaseName.includes('amazon')) return { class: 'amazon', icon: 'fab fa-amazon' };
    if (lowerCaseName.includes('teknosa')) return { class: 'teknosa', icon: 'fas fa-plug' };
    if (lowerCaseName.includes('vatan')) return { class: 'vatan', icon: 'fas fa-desktop' };
    if (lowerCaseName.includes('n11')) return { class: 'n11', icon: 'fas fa-tag' };
    if (lowerCaseName.includes('media markt')) return { class: 'mediamarkt', icon: 'fas fa-tv' };
    return { class: 'default-store', icon: 'fas fa-external-link-alt' };
}

function resetToLanding() {
    const interaction = document.getElementById('interaction');
    const landing = document.querySelector('.landing');
    
    interaction.style.display = 'none';
    landing.style.display = '';
    
    // Hide all screens
    hideAICreationScreen();
    hideErrorScreen();
    
    // Reset all content
    document.querySelector('.recommendations').innerHTML = '';
    document.querySelector('.question').innerHTML = '';
    document.querySelector('.options').innerHTML = '';
    document.querySelector('.error').textContent = '';
    
    // Reset variables
    step = 0;
    category = null;
    answers = [];
    currentQuestionIndex = 0;
    
    // Clear search input
    const searchInput = document.getElementById('chatbox-input');
    if (searchInput) searchInput.value = '';
}

let isRequestInProgress = false;

function handleOption(opt) {
    if (isRequestInProgress) {
        console.log("Request already in progress, ignoring click");
        return;
    }
    
    console.log("Option selected:", opt);
    
    try {
        isRequestInProgress = true;
        
        // Disable all option buttons
        const optionButtons = document.querySelectorAll('.option-btn');
        optionButtons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
        });
        
        // Seçimi görsel olarak göster
        const selectedButton = Array.from(optionButtons).find(btn => btn.textContent === opt);
        if (selectedButton) {
            selectedButton.style.backgroundColor = 'var(--cta-orange)';
            selectedButton.style.borderColor = 'var(--cta-orange)';
            selectedButton.style.color = 'white';
        }
        
        answers.push(opt);
        step++;
        currentQuestionIndex = step;
        
        document.querySelector('.error').textContent = '';
        
        console.log("İlerliyor: Adım", step, "Cevaplar:", answers);
        
        setTimeout(function() {
            askAgent();
        }, 300);
    } catch(e) {
        console.error("handleOption'da hata:", e);
        isRequestInProgress = false;
        const errorMsg = currentLanguage === 'tr' ? 'İşlem sırasında bir hata oluştu. Lütfen sayfayı yenileyin.' : 'An error occurred during processing. Please refresh the page.';
        document.querySelector('.error').textContent = errorMsg;
    }
}

function askAgent() {
    console.log(`Soru soruluyor: Step ${step}, Category ${category}, Answers:`, answers);
    
    document.querySelector('.error').textContent = '';
    
    const loadingElement = document.querySelector('.loading');
    if (loadingElement) {
        loadingElement.style.display = 'block';
        const loadingText = currentLanguage === 'tr' ? '<i class="fas fa-spinner fa-spin"></i> Yükleniyor...' : '<i class="fas fa-spinner fa-spin"></i> Loading...';
        loadingElement.innerHTML = loadingText;
    }
    
    console.log("İstek başlatılıyor:", {
        step: step,
        category: category,
        answers: answers,
        isRequestInProgress: isRequestInProgress
    });
    
    let specs = window.currentSpecs && window.currentSpecs[category] ? window.currentSpecs[category] : [];
    if (step > specs.length) {
        showAICreationScreen();
    }
    
    const timeoutId = setTimeout(() => {
        if (isRequestInProgress) {
            console.log("Zaman aşımı oluştu!");
            isRequestInProgress = false;
            hideAICreationScreen();
            if (loadingElement) loadingElement.style.display = 'none';
            showErrorScreen();
        }
    }, 45000);
    
    fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            step: step, 
            category: category, 
            answers: answers,
            language: currentLanguage
        })
    })
    .then(res => {
        console.log("Sunucu yanıt verdi:", res.status);
        if (!res.ok) {
            throw new Error(`HTTP hata: ${res.status} ${res.statusText}`);
        }
        return res.json();
    })
    .then(data => {
        clearTimeout(timeoutId);
        isRequestInProgress = false;
        console.log("🔄 Sunucudan gelen yanıt:", data);
        console.log("🔍 Response type:", data.type);
        console.log("🔍 Response keys:", Object.keys(data));
        console.log("🔍 Has recommendations:", !!data.recommendations);
        console.log("🔍 Has question:", !!data.question);
        console.log("🔍 Has options:", !!data.options);
        
        console.log("Response has question:", !!data.question);
        console.log("Response has options:", !!data.options);
        console.log("Response has recommendations:", !!data.recommendations);
        console.log("Response has error:", !!data.error);
        console.log("Response type:", data.type);
        console.log("Response keys:", Object.keys(data));
        
        if (data.question && data.options) {
            console.log("✅ Rendering question...");
            hideAICreationScreen();
            window.currentQuestionTooltip = data.tooltip || null;
            renderQuestion(data.question, data.options, data.emoji || '🔍');
        } else if (data.type === 'modern_recommendation' && data.recommendations) {
            console.log("✅ Modern recommendation path triggered");
            // Modern search engine response
            console.log("🚀 Modern recommendations found:", data.recommendations.length);
            console.log("📦 Modern recommendation data:", JSON.stringify(data, null, 2));
            
            hideAICreationScreen();
            renderRecommendations(data.recommendations);
            
            // Grounding results varsa göster
            if (data.grounding_results) {
                console.log("🔍 Grounding results:", data.grounding_results);
            }
            
            // Shopping results varsa göster
            if (data.shopping_results) {
                console.log("🛒 Shopping results:", data.shopping_results.length);
            }
            
            // Sources varsa göster
            if (data.sources) {
                console.log("📄 Sources:", data.sources.length);
            }
            
            // Modern search başarı bilgisi göster
            const modernMessage = currentLanguage === 'tr' ? 
                '✅ Online arama sistemi aktif - Güncel piyasa verilerimizle ürün önerilerinizi sunuyoruz.' : 
                '✅ Online search system active - Showing product recommendations with current market data.';
            
            showInfoMessage(modernMessage);
        } else if (data.type === 'fallback_recommendation' && data.recommendations) {
            console.log("✅ Fallback recommendation path triggered");
            // Fallback recommendations - güvenilir öneriler
            console.log("Fallback recommendations found:", data.recommendations.length);
            hideAICreationScreen();
            renderRecommendations(data.recommendations);
            
            // Fallback durumu için özel bildirim
            const fallbackMessage = currentLanguage === 'tr' ? 
                '⚠️ Online arama servisi şu anda kullanılamıyor. Size önceden hazırlanmış kaliteli ürün önerilerimizi sunuyoruz.' : 
                '⚠️ Online search service is currently unavailable. We are showing you our pre-prepared quality product recommendations.';
            
            showInfoMessage(fallbackMessage);
            
            // Ek mesaj varsa da göster
            if (data.message && data.message !== fallbackMessage) {
                setTimeout(() => showInfoMessage(data.message), 2000);
            }
        } else if (data.recommendations) {
            console.log("✅ Legacy recommendation path triggered");
            // Legacy recommendations
            renderRecommendations(data.recommendations);
        } else if (data.categories) {
            console.log("✅ Categories path triggered");
            renderLanding(data.categories);
        } else if (data.error) {
            console.log("❌ Error path triggered");
            hideAICreationScreen();
            if (loadingElement) loadingElement.style.display = 'none';
            showErrorScreen();
        } else if (data.type === 'error' && data.fallback_recommendations) {
            console.log("✅ Error with fallback path triggered");
            // Error with fallback recommendations
            console.log("Error occurred but fallback recommendations provided");
            hideAICreationScreen();
            renderRecommendations(data.fallback_recommendations);
            
            // Error message'ı göster ama bloke etme
            const errorMsg = currentLanguage === 'tr' ? 
                'Arama sisteminde bir sorun oluştu, yedek öneriler gösteriliyor.' : 
                'Search system error occurred, showing fallback recommendations.';
            showInfoMessage(errorMsg);
        } else {
            console.error('❌ Hiçbir path eşleşmedi! Beklenmeyen yanıt formatı:', data);
            hideAICreationScreen();
            if (loadingElement) loadingElement.style.display = 'none';
            showErrorScreen();
        }
    })
    .catch(err => {
        clearTimeout(timeoutId);
        isRequestInProgress = false;
        
        hideAICreationScreen();
        if (loadingElement) loadingElement.style.display = 'none';
        showErrorScreen();
        console.error('Hata:', err);
    });
}

window.onload = () => {
    console.log("FindFlow uygulaması başlatılıyor...");
    
    // Tema tercihini localStorage'dan yükle
    const savedTheme = localStorage.getItem('findflow-theme') || 'light';
    changeTheme(savedTheme);
    
    // Dil değiştirme event listener'ları
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const lang = this.dataset.lang;
            changeLanguage(lang);
        });
    });
    
    // Tema değiştirme event listener'ları
    document.querySelectorAll('.theme-switch').forEach(switch_el => {
        switch_el.addEventListener('click', function() {
            const currentTheme = this.dataset.theme;
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            // Switch'i güncelle
            this.dataset.theme = newTheme;
            this.classList.toggle('active');
            
            // Temayı değiştir
            changeTheme(newTheme);
        });
    });
    
    // Otomatik tamamlama için input event listener
    const searchInput = document.getElementById('chatbox-input');
    searchInput.addEventListener('input', handleAutocomplete);
    searchInput.addEventListener('keydown', handleAutocompleteKeydown);
    searchInput.addEventListener('blur', hideAutocomplete);
    
    // CSS ekle
    document.head.insertAdjacentHTML('beforeend', `
        <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .recommendations-grid {
                display: grid;
                gap: 15px;
                margin-bottom: 30px;
            }
            
            .recommendation-content {
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 10px;
            }
            
            .recommendation-name {
                font-weight: 600;
                color: var(--text-dark);
                flex: 1;
            }
            
            .recommendation-price {
                color: var(--primary-blue);
                font-weight: 500;
            }
            
            .buy-link {
                background: var(--cta-orange);
                color: white;
                padding: 8px 15px;
                border-radius: 8px;
                text-decoration: none;
                font-size: 0.9rem;
                font-weight: 500;
                transition: all 0.3s ease;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }
            
            .buy-link:hover {
                background: var(--cta-orange-hover);
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(249, 115, 22, 0.3);
            }
            
            .back-section {
                text-align: center;
                margin-top: 20px;
            }
        </style>
    `);
    
    // Get categories from backend
    fetch('/categories')
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            console.log("Kategoriler yüklendi:", Object.keys(data));
            
            const categories = Object.keys(data);
            window.currentSpecs = {};
            
            for (const cat of categories) {
                window.currentSpecs[cat] = data[cat].specs || [];
            }
            
            renderLanding(categories);
            
            const chatboxSend = document.getElementById('chatbox-send');
            const chatboxInput = document.getElementById('chatbox-input');
            
            if (chatboxSend && chatboxInput) {
                chatboxSend.onclick = handleChatboxEntry;
                chatboxInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') handleChatboxEntry();
                });
            }
            
            console.log("FindFlow başarıyla başlatıldı");
        })
        .catch(error => {
            console.error("Kategoriler yüklenirken hata oluştu:", error);
            const errorMsg = currentLanguage === 'tr' ? "Kategoriler yüklenemedi. Lütfen sayfayı yenileyin." : "Categories could not be loaded. Please refresh the page.";
            document.querySelector('.error').textContent = errorMsg;
        });
    
    // Akıllı arama bileşenini oluştur
    const smartSearchHtml = `
        <div class="smart-search">
          <input type="text" id="product-search-input" placeholder="Ürün Ara (örn: ka)">
          <select id="color-filter">
            <option value="">Renk</option>
            <option value="kırmızı">Kırmızı</option>
            <option value="siyah">Siyah</option>
            <option value="mavi">Mavi</option>
          </select>
          <select id="size-filter">
            <option value="">Beden</option>
            <option value="S">S</option>
            <option value="M">M</option>
            <option value="L">L</option>
          </select>
          <select id="rating-filter">
            <option value="">Puan</option>
            <option value="4">4+ Yıldız</option>
            <option value="3">3+ Yıldız</option>
          </select>
          <div id="product-suggestions"></div>
        </div>
        <div id="product-list"></div>
    `;
    
    document.getElementById('smart-search-container').innerHTML = smartSearchHtml;
    
    // Ürün arama ve filtreleme
    const productSearchInput = document.getElementById('product-search-input');
    const colorFilter = document.getElementById('color-filter');
    const sizeFilter = document.getElementById('size-filter');
    const ratingFilter = document.getElementById('rating-filter');
    const productSuggestions = document.getElementById('product-suggestions');
    const productList = document.getElementById('product-list');
    
    // Ürünleri yükle
    function loadProducts() {
        fetch('/products')
            .then(res => res.json())
            .then(data => {
                window.allProducts = data;
                renderProductList(data);
            })
            .catch(error => {
                console.error("Ürünler yüklenirken hata:", error);
            });
    }
    
    // Ürün listesini renderla
    function renderProductList(products) {
        productList.innerHTML = '';
        
        products.forEach(product => {
            const productItem = document.createElement('div');
            productItem.className = 'product-item';
            productItem.innerHTML = `
                <div class="product-image">
                    <img src="${product.image}" alt="${product.name}">
                </div>
                <div class="product-info">
                    <div class="product-name">${product.name}</div>
                    <div class="product-price">${product.price} ₺</div>
                </div>
            `;
            
            productItem.addEventListener('click', () => {
                // Ürün tıklandığında yapılacaklar
                console.log("Ürün tıklandı:", product);
            });
            
            productList.appendChild(productItem);
        });
    }
    
    // Arama ve filtreleme işlemini gerçekleştir
    function performSearchAndFilter() {
        const query = productSearchInput.value.toLowerCase().trim();
        const selectedColor = colorFilter.value;
        const selectedSize = sizeFilter.value;
        const selectedRating = ratingFilter.value;
        
        let filteredProducts = window.allProducts || [];
        
        // Ürün adında arama
        if (query) {
            filteredProducts = filteredProducts.filter(product => product.name.toLowerCase().includes(query));
        }
        
        // Renk filtresi
        if (selectedColor) {
            filteredProducts = filteredProducts.filter(product => product.color === selectedColor);
        }
        
        // Beden filtresi
        if (selectedSize) {
            filteredProducts = filteredProducts.filter(product => product.size === selectedSize);
        }
        
        // Puan filtresi
        if (selectedRating) {
            filteredProducts = filteredProducts.filter(product => product.rating >= parseInt(selectedRating));
        }
        
        renderProductList(filteredProducts);
    }
    
    // Olay dinleyicileri ekle
    productSearchInput.addEventListener('input', performSearchAndFilter);
    colorFilter.addEventListener('change', performSearchAndFilter);
    sizeFilter.addEventListener('change', performSearchAndFilter);
    ratingFilter.addEventListener('change', performSearchAndFilter);
    
    // Ürünleri yükle
    loadProducts();
};

// Ana sayfaya dönüş fonksiyonu
function goToHomePage() {
    // Tüm ekranları gizle
    hideErrorScreen();
    hideAICreationScreen();
    hideLoadingScreen();
    
    // Interaction'ı gizle ve landing'i göster
    document.getElementById('interaction').style.display = 'none';
    document.querySelector('.landing').style.display = 'block';
    
    // Değişkenleri sıfırla
    step = 0;
    category = null;
    answers = [];
    
    // Input'u temizle
    document.getElementById('chatbox-input').value = '';
    
    // Arama butonunu aktif hale getir
    const searchBtn = document.getElementById('chatbox-send');
    const originalText = currentLanguage === 'tr' ? '<i class="fas fa-search"></i> <span>AI ile Bul</span>' : '<i class="fas fa-search"></i> <span>Find with AI</span>';
    searchBtn.innerHTML = originalText;
    searchBtn.disabled = false;
}

// AI Creation Screen fonksiyonları
function showAICreationScreen() {
    document.getElementById('ai-creation-screen').style.display = 'flex';
    
    // Progress bar animasyonu
    setTimeout(() => {
        const progressBar = document.querySelector('.ai-progress-bar');
        if (progressBar) progressBar.style.width = '75%';
    }, 1000);
    
    setTimeout(() => {
        const progressBar = document.querySelector('.ai-progress-bar');
        if (progressBar) progressBar.style.width = '100%';
    }, 2000);
}

function hideAICreationScreen() {
    document.getElementById('ai-creation-screen').style.display = 'none';
    // Progress bar'ı sıfırla
    const progressBar = document.querySelector('.ai-progress-bar');
    if (progressBar) progressBar.style.width = '45%';
}

// Error Screen fonksiyonları
function showInfoMessage(message) {
    // Info mesajı için stil oluştur
    const infoDiv = document.createElement('div');
    infoDiv.className = 'info-message';
    infoDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(79, 70, 229, 0.3);
        z-index: 10000;
        max-width: 350px;
        font-size: 14px;
        line-height: 1.4;
        animation: slideInRight 0.3s ease;
    `;
    infoDiv.innerHTML = `
        <i class="fas fa-info-circle" style="margin-right: 8px; color: #fbbf24;"></i>
        ${message}
    `;
    
    document.body.appendChild(infoDiv);
    
    // 5 saniye sonra otomatik olarak kaldır
    setTimeout(() => {
        if (infoDiv.parentNode) {
            infoDiv.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(infoDiv);
            }, 300);
        }
    }, 5000);
    
    // Tıklayınca kapat
    infoDiv.addEventListener('click', () => {
        if (infoDiv.parentNode) {
            infoDiv.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(infoDiv);
            }, 300);
        }
    });
}

function showErrorScreen() {
    document.getElementById('error-screen').style.display = 'flex';
}

function hideErrorScreen() {
    document.getElementById('error-screen').style.display = 'none';
}

function hideLoadingScreen() {
    const loadingElement = document.querySelector('.loading');
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
}

// Tooltip functions
function updateQuestionTooltip() {
    const tooltipWrapper = document.getElementById('question-tooltip');
    const tooltipText = tooltipWrapper?.querySelector('.tooltip-text');
    
    if (!tooltipWrapper || !tooltipText) {
        return;
    }
    
    // Check if current question has tooltip
    if (window.currentQuestionTooltip && window.currentQuestionTooltip.trim() !== '') {
        tooltipText.textContent = window.currentQuestionTooltip;
        tooltipWrapper.style.display = 'inline-flex';
        
        // Add click and hover events for mobile and desktop
        const tooltipIcon = tooltipWrapper.querySelector('.tooltip-icon');
        if (tooltipIcon) {
            // Remove existing event listeners
            tooltipIcon.replaceWith(tooltipIcon.cloneNode(true));
            const newTooltipIcon = tooltipWrapper.querySelector('.tooltip-icon');
            
            // Desktop hover
            newTooltipIcon.addEventListener('mouseenter', showTooltip);
            newTooltipIcon.addEventListener('mouseleave', hideTooltip);
            
            // Mobile tap
            newTooltipIcon.addEventListener('click', toggleTooltip);
        }
    } else {
        tooltipWrapper.style.display = 'none';
    }
}

function showTooltip() {
    const tooltipWrapper = document.getElementById('question-tooltip');
    const tooltipText = tooltipWrapper?.querySelector('.tooltip-text');
    if (tooltipText) {
        tooltipText.style.visibility = 'visible';
        tooltipText.style.opacity = '1';
    }
}

function hideTooltip() {
    const tooltipWrapper = document.getElementById('question-tooltip');
    const tooltipText = tooltipWrapper?.querySelector('.tooltip-text');
    if (tooltipText) {
        tooltipText.style.visibility = 'hidden';
        tooltipText.style.opacity = '0';
    }
}

function toggleTooltip() {
    const tooltipWrapper = document.getElementById('question-tooltip');
    const tooltipText = tooltipWrapper?.querySelector('.tooltip-text');
    if (tooltipText) {
        const isVisible = tooltipText.style.visibility === 'visible';
        if (isVisible) {
            hideTooltip();
        } else {
            showTooltip();
        }
    }
}
