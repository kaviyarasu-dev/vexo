class TranslationRegistry {
    constructor() {
        this.translations = {};
    }

    async loadTranslations() {
        try {
            // In a real app this might be loaded via a dynamic configuration or API endpoint
            const response = await fetch('/static/config/ux_translations.json');
            if (response.ok) {
                this.translations = await response.json();
            } else {
                const apiResponse = await fetch('/api/v1/system/ux_translations');
                if (apiResponse.ok) {
                    this.translations = await apiResponse.json();
                }
            }
        } catch (error) {
            console.error("Failed to load translations:", error);
        }
    }

    setTranslations(data) {
        this.translations = data;
    }

    get(key) {
        return this.translations[key];
    }
}

window.translationRegistry = new TranslationRegistry();
