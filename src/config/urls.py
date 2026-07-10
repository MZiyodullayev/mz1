from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
]

# Serve /media/ (uploaded screenshots) in all environments, not just DEBUG.
# NOTE: this does NOT check authentication per-file — protection instead
# relies on filenames being unguessable UUIDs (see
# apps/screener/models.py: screenshot_upload_path). That's a reasonable
# tradeoff for a personal project, but isn't the same as real access
# control. On Render's free tier, the disk is also ephemeral, so uploaded
# files disappear on every restart/redeploy regardless.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]