/**
 * Language Selector Component
 * Sistema de seleção de idioma com flags
 */

class LanguageSelector {
    constructor() {
        this.currentLanguage = this.getCurrentLanguage();
        this.init();
    }

    init() {
        // Inicializa o seletor se existir na página
        const selector = document.getElementById('languageSelector');
        if (selector) {
            this.setupEventListeners();
            this.updateCurrentLanguageDisplay();
        }
    }

    getCurrentLanguage() {
        // Tenta obter da session storage primeiro
        let lang = sessionStorage.getItem('language');
        if (lang) return lang;

        // Fallback para detectar do servidor
        fetch('/i18n/get-language')
            .then(response => response.json())
            .then(data => {
                this.currentLanguage = data.language;
                sessionStorage.setItem('language', data.language);
                return data.language;
            })
            .catch(error => {
                console.error('Error getting language:', error);
                return 'pt-BR';
            });

        return 'pt-BR'; // Default
    }

    setupEventListeners() {
        const button = document.getElementById('languageSelectorButton');
        const dropdown = document.getElementById('languageDropdown');
        const options = document.querySelectorAll('.language-option');

        // Toggle dropdown
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!button.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });

        // Handle language selection
        options.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const lang = option.dataset.lang;
                this.changeLanguage(lang);
            });
        });
    }

    changeLanguage(lang) {
        // Mostra loading
        const button = document.getElementById('languageSelectorButton');
        const originalContent = button.innerHTML;
        button.innerHTML = '<span class="mdi mdi-loading mdi-spin"></span>';
        button.disabled = true;

        // Envia requisição para mudar idioma
        fetch(`/i18n/set-language/${lang}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Atualiza session storage
                sessionStorage.setItem('language', lang);
                this.currentLanguage = lang;

                // Recarrega a página para aplicar as traduções
                window.location.reload();
            } else {
                throw new Error('Failed to change language');
            }
        })
        .catch(error => {
            console.error('Error changing language:', error);
            button.innerHTML = originalContent;
            button.disabled = false;
            alert('Erro ao mudar idioma. Tente novamente.');
        });
    }

    updateCurrentLanguageDisplay() {
        const button = document.getElementById('languageSelectorButton');
        const options = document.querySelectorAll('.language-option');
        
        // Atualiza opções ativas
        options.forEach(option => {
            if (option.dataset.lang === this.currentLanguage) {
                option.classList.add('active');
            } else {
                option.classList.remove('active');
            }
        });

        // Atualiza flag no botão
        const flagMap = {
            'pt-BR': '🇧🇷',
            'en-US': '🇺🇸'
        };

        const langNameMap = {
            'pt-BR': 'PT',
            'en-US': 'EN'
        };

        if (button && this.currentLanguage) {
            const flag = flagMap[this.currentLanguage] || '🌐';
            const langName = langNameMap[this.currentLanguage] || 'Lang';
            button.innerHTML = `
                <span style="font-size: 1.2rem;">${flag}</span>
                <span>${langName}</span>
                <span class="mdi mdi-chevron-down"></span>
            `;
        }
    }

    // Método para traduzir elementos dinamicamente via JavaScript
    static translateElement(element, key, translations) {
        const keys = key.split('.');
        let value = translations;
        
        for (const k of keys) {
            if (value && typeof value === 'object') {
                value = value[k];
            } else {
                value = null;
                break;
            }
        }
        
        if (value && typeof value === 'string') {
            element.textContent = value;
        }
    }

    // Método para obter tradução via fetch (para uso dinâmico)
    static async getTranslations() {
        try {
            const response = await fetch('/i18n/get-translations');
            return await response.json();
        } catch (error) {
            console.error('Error loading translations:', error);
            return {};
        }
    }
}

// Inicializa quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.languageSelector = new LanguageSelector();
});

// Exporta para uso global
window.LanguageSelector = LanguageSelector;
