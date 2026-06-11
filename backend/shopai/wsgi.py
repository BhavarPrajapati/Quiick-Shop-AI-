"""
WSGI config for shopai project.
"""

import os
from django.core.handlers.wsgi import WSGIHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopai.settings')

application = WSGIHandler()
