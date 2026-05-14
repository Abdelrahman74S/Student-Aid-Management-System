import os
from io import BytesIO
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.files.base import ContentFile

def fetch_resources(uri, rel):
    """
    Callback to allow xhtml2pdf to access Django's static and media files.
    """
    sUrl = settings.STATIC_URL
    mUrl = settings.MEDIA_URL
    mRoot = settings.MEDIA_ROOT
    sRoot = settings.STATIC_ROOT

    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri.replace(mUrl, ""))
    elif uri.startswith(sUrl):
        path = os.path.join(sRoot, uri.replace(sUrl, ""))
    else:
        return uri

    return path

def render_to_pdf(template_src, context_dict={}):
    """
    Render a Django template to a PDF. Returns a ContentFile.
    """
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    
    # Generate PDF
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, link_callback=fetch_resources, encoding='UTF-8')
    
    if not pdf.err:
        return ContentFile(result.getvalue())
    return None
