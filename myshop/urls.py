from django.contrib import admin
from django.urls import path, include  # <-- ОБЯЗАТЕЛЬНО добавьте include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),  # Админка: /admin
    path('', include('main.urls')),   # Подключаем URL-адреса из приложения main
]

# Для отображения картинок в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)