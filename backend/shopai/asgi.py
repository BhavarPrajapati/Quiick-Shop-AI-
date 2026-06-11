"""
ASGI config for shopai project.
"""

import os
from django.core.handlers.asgi import ASGIHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopai.settings')

application = ASGIHandler()
