// Упрощенная версия - без автоматического анализа канала
document.getElementById('channelUrl').addEventListener('input', function() {
    const url = this.value.trim();
    const submitBtn = document.getElementById('submitBtn');
    
    // Просто включаем/выключаем кнопку на основе наличия URL
    if (url) {
        submitBtn.disabled = false;
    } else {
        submitBtn.disabled = true;
    }
});

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    console.log('📺 Страница каналов загружена');
    });