// Упрощенная версия - без автоматического анализа канала
const channelUrlElement = document.getElementById('channelUrl');
if (channelUrlElement) {
    channelUrlElement.addEventListener('input', function() {
        const url = this.value.trim();
        const submitBtn = document.getElementById('submitBtn');
        
        if (submitBtn) {
            // Просто включаем/выключаем кнопку на основе наличия URL
            if (url) {
                submitBtn.disabled = false;
            } else {
                submitBtn.disabled = true;
            }
        }
    });
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    console.log('📺 Страница каналов загружена');
    });