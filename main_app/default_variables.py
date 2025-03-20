import os
from django.conf import settings
WEBSITE_TITLE = 'digital twin heatpump'
GMAIL_WEBSITE_TITLE = 'digital twin heatpump'

def THUMBNAIL_ICON_WEBSITE():
    thumbnail_image_url = os.path.join(settings.MEDIA_URL , 'assets/main_logo.png')
    
    THUMBNAIL_ICON_RETURN = thumbnail_image_url
    # thumbnail_image_path = os.path.join(settings.MEDIA_ROOT, 'assets', THUMBNAIL_ICON)
    # if os.path.exists(thumbnail_image_path):
    #     thumbnail_image_url = os.path.join(settings.MEDIA_URL, 'assets', THUMBNAIL_ICON)
    #     THUMBNAIL_ICON_RETURN = thumbnail_image_url
    # else:
    #     thumbnail_image_url = os.path.join(settings.MEDIA_URL , 'assets/main_logo.png')
    #     THUMBNAIL_ICON_RETURN = thumbnail_image_url
    return THUMBNAIL_ICON_RETURN

def THUMBNAIL_ICON_REACT():
    thumbnail_image_url = os.path.join(settings.MEDIA_URL , 'assets/main_logo.png')
    THUMBNAIL_ICON_RETURN = thumbnail_image_url
    return THUMBNAIL_ICON_RETURN