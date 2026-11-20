from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, re_path, include
from registers.mcp_views import mcp

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # barra final opcional: o 301 do APPEND_SLASH transforma o POST do conector em GET
    re_path(r'^mcp/(?P<token>[^/]+)/?$', mcp, name='mcp'),
    path('register/', include('registers.urls')),
    path('export/', include('export.urls')),
    path('', include('reports.urls')),
    path('admin/', admin.site.urls),
]
