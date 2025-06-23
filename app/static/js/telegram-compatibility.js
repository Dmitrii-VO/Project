// TELEGRAM WEBAPP COMPATIBILITY LAYER
// Обеспечивает совместимость с разными версиями Telegram WebApp

class TelegramCompatibility {
    constructor() {
        this.tg = window.Telegram?.WebApp;
        this.version = this.getVersion();
        this.features = this.detectFeatures();
    }

    // Получение версии Telegram WebApp
    getVersion() {
        if (!this.tg) return '0.0';
        
        // Пытаемся получить версию из различных источников
        return this.tg.version || 
               this.tg.WebAppVersion || 
               window.Telegram?.WebAppVersion || 
               '6.0'; // Fallback для старых версий
    }

    // Определение поддерживаемых функций
    detectFeatures() {
        const features = {
            hapticFeedback: false,
            backButton: false,
            mainButton: false,
            settingsButton: false,
            invoices: false,
            popups: false,
            closingConfirmation: false,
            theme: false,
            cloudStorage: false
        };

        if (!this.tg) return features;

        // Проверяем поддержку функций по версии
        const versionFloat = parseFloat(this.version);

        // HapticFeedback появился в версии 6.1
        features.hapticFeedback = versionFloat >= 6.1 && 
                                  this.tg.HapticFeedback && 
                                  typeof this.tg.HapticFeedback.impactOccurred === 'function';

        // BackButton появился в версии 6.1
        features.backButton = versionFloat >= 6.1 && this.tg.BackButton;

        // MainButton доступен с версии 6.0
        features.mainButton = versionFloat >= 6.0 && this.tg.MainButton;

        // SettingsButton появился в версии 6.10
        features.settingsButton = versionFloat >= 6.10 && this.tg.SettingsButton;

        // Invoices доступны с версии 6.1
        features.invoices = versionFloat >= 6.1 && this.tg.showInvoice;

        // Popups появились в версии 6.2
        features.popups = versionFloat >= 6.2 && this.tg.showPopup;

        // Closing confirmation с версии 6.2
        features.closingConfirmation = versionFloat >= 6.2 && this.tg.enableClosingConfirmation;

        // Theme parameters с версии 6.1
        features.theme = versionFloat >= 6.1 && this.tg.themeParams;

        // Cloud Storage с версии 6.9
        features.cloudStorage = versionFloat >= 6.9 && this.tg.CloudStorage;

        return features;
    }

    // Безопасный Haptic Feedback
    hapticFeedback(type = 'light') {
        if (!this.features.hapticFeedback) {
            console.debug(`HapticFeedback не поддерживается в версии ${this.version}`);
            return false;
        }

        try {
            this.tg.HapticFeedback.impactOccurred(type);
            return true;
        } catch (error) {
            console.warn('Ошибка HapticFeedback:', error);
            return false;
        }
    }

    // Безопасное показ уведомления
    showAlert(message) {
        if (this.tg?.showAlert) {
            this.tg.showAlert(message);
            return true;
        } else {
            alert(message);
            return false;
        }
    }

    // Безопасный показ popup
    showPopup(params) {
        if (this.features.popups) {
            this.tg.showPopup(params);
            return true;
        } else {
            // Fallback на обычный alert
            this.showAlert(params.message || 'Уведомление');
            return false;
        }
    }

    // Безопасная работа с MainButton
    configureMainButton(params) {
        if (!this.features.mainButton) {
            console.debug('MainButton не поддерживается');
            return false;
        }

        try {
            const button = this.tg.MainButton;
            
            if (params.text) button.setText(params.text);
            if (params.color) button.setParams({ color: params.color });
            if (params.textColor) button.setParams({ text_color: params.textColor });
            
            if (params.show) {
                button.show();
            } else if (params.hide) {
                button.hide();
            }

            if (params.onClick && typeof params.onClick === 'function') {
                button.onClick(params.onClick);
            }

            return true;
        } catch (error) {
            console.warn('Ошибка настройки MainButton:', error);
            return false;
        }
    }

    // Безопасная работа с BackButton
    configureBackButton(params) {
        if (!this.features.backButton) {
            console.debug('BackButton не поддерживается');
            return false;
        }

        try {
            const button = this.tg.BackButton;
            
            if (params.show) {
                button.show();
            } else if (params.hide) {
                button.hide();
            }

            if (params.onClick && typeof params.onClick === 'function') {
                button.onClick(params.onClick);
            }

            return true;
        } catch (error) {
            console.warn('Ошибка настройки BackButton:', error);
            return false;
        }
    }

    // Применение темы (если поддерживается)
    applyTheme() {
        if (!this.features.theme) {
            console.debug('Theme parameters не поддерживаются');
            return false;
        }

        try {
            const theme = this.tg.themeParams;
            const root = document.documentElement;

            // Применяем только если параметры есть
            Object.entries({
                '--tg-theme-bg-color': theme.bg_color,
                '--tg-theme-text-color': theme.text_color,
                '--tg-theme-button-color': theme.button_color,
                '--tg-theme-button-text-color': theme.button_text_color,
                '--tg-theme-hint-color': theme.hint_color,
                '--tg-theme-link-color': theme.link_color,
                '--tg-theme-secondary-bg-color': theme.secondary_bg_color
            }).forEach(([property, value]) => {
                if (value) root.style.setProperty(property, value);
            });

            return true;
        } catch (error) {
            console.warn('Ошибка применения темы:', error);
            return false;
        }
    }

    // Информация о совместимости
    getCompatibilityInfo() {
        return {
            version: this.version,
            features: this.features,
            isSupported: !!this.tg,
            recommendations: this.getRecommendations()
        };
    }

    // Рекомендации по совместимости
    getRecommendations() {
        const recommendations = [];
        
        if (!this.tg) {
            recommendations.push('Telegram WebApp не обнаружен. Проверьте запуск в Telegram.');
            return recommendations;
        }

        const versionFloat = parseFloat(this.version);
        
        if (versionFloat < 6.1) {
            recommendations.push('Обновите Telegram для доступа к HapticFeedback и BackButton');
        }
        
        if (versionFloat < 6.2) {
            recommendations.push('Обновите Telegram для доступа к Popups');
        }
        
        if (versionFloat < 6.9) {
            recommendations.push('Обновите Telegram для доступа к CloudStorage');
        }

        if (recommendations.length === 0) {
            recommendations.push('Все функции поддерживаются!');
        }

        return recommendations;
    }
}

// Создание глобального экземпляра
window.TelegramCompatibility = new TelegramCompatibility();

// Логирование информации о совместимости
console.log('📱 Telegram WebApp Compatibility Info:', 
    window.TelegramCompatibility.getCompatibilityInfo());

// Экспорт для использования в других модулях
window.telegramCompat = window.TelegramCompatibility;