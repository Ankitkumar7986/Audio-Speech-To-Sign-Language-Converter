import os
import sys
from django.conf import settings
from django.core.management import execute_from_command_line
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponse

# --- 1. CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='preview-secret-key',
        ROOT_URLCONF=__name__,
        # Database is required for Login/Signup to work
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
            }
        },
        INSTALLED_APPS=[
            'django.contrib.staticfiles',
            'django.contrib.contenttypes',
            'django.contrib.auth', 
            'django.contrib.sessions',
            'django.contrib.messages',
        ],
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
            'APP_DIRS': False,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        }],
        STATIC_URL='/static/',
        STATICFILES_DIRS=[os.path.join(BASE_DIR, 'assets')],
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ]
    )

import django
django.setup()

from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

# --- 2. VIEWS ---

def view_login(request):
    """Fully functional Login Page"""
    form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def view_signup(request):
    """Fully functional Signup Page"""
    form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

def view_animation_ui(request):
    """
    Renders the Animation UI but DISABLES the backend logic.
    We pass empty 'words' so no video plays, but the page looks normal.
    """
    context = {
        'text': '',
        'words': [] # Empty list ensures no animation plays
    }
    return render(request, 'animation.html', context)

def view_disabled(request):
    """Placeholder for other pages"""
    return HttpResponse("<h3>This feature is disabled. <a href='/login/'>Go to Login</a></h3>")

# --- 3. URLS ---
urlpatterns = [
    # WORKING PAGES
    path('login/', view_login, name='login'),
    path('signup/', view_signup, name='signup'),
    
    # UI ONLY (No Logic)
    path('animation/', view_animation_ui, name='animation'),

    # DISABLED / REDIRECTS
    path('', lambda request: redirect('login'), name='home'),     
    path('about/', view_disabled, name='about'),                  
    path('contact/', view_disabled, name='contact'),              
    path('logout/', lambda request: redirect('login'), name='logout'),
]

# --- 4. RUN SERVER ---
if __name__ == '__main__':
    # Run on port 9000
    sys.argv = ['preview_server.py', 'runserver', '9000']
    execute_from_command_line(sys.argv)