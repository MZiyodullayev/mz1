from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from api.views.user_app import UserModeViewSet
from api.views.screener import ScreenshotViewSet, ScreenshotUploadView, WhitelistViewSet
from django.urls import path, include

r = DefaultRouter()

r.register(r'users', UserModeViewSet, basename='users')
r.register(r'screener/screenshots', ScreenshotViewSet, basename='screenshots')
r.register(r'screener/whitelist', WhitelistViewSet, basename='whitelist')

urlpatterns = [
    path('', include(r.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('screener/upload/', ScreenshotUploadView.as_view(), name='screenshot-upload'),
]
