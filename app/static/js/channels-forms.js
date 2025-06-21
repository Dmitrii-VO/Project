document.getElementById('channelUrl').addEventListener('input', async function() {
            const url = this.value.trim();

            if (!url) {
                document.getElementById('channelPreview').classList.remove('active');
                document.getElementById('additionalFields').style.display = 'none';
                document.getElementById('pricingFields').style.display = 'none';
                document.getElementById('submitBtn').disabled = true;
                return;
            }

            // Анализируем канал с задержкой для избежания спама
            clearTimeout(this.timeoutId);
            this.timeoutId = setTimeout(async () => {
                try {
                    const channelData = await channelAnalyzer.analyzeChannel(url);
                    if (channelData && channelData.success) {
                        channelAnalyzer.showChannelPreview(channelData);
                    }
                } catch (error) {
                    channelAnalyzer.showError(error.message || 'Не удалось получить данные канала');
                }
            }, 1000);
        });

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    console.log('📺 Страница каналов загружена');
    });