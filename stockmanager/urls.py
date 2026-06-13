from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from inventory.forms import StyledLoginForm


urlpatterns = [
    path('', lambda request: redirect('/inventory/')),
    path('admin/', admin.site.urls),
    path('inventory/', include('inventory.urls')),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='login.html',
            authentication_form=StyledLoginForm
        ),
        name='login'
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(
            next_page=reverse_lazy('login')
        ),
        name='logout'
    ),
]