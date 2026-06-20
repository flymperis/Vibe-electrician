from pathlib import Path

from django.conf import settings

from .models import CompanyProfile

# Διαστάσεις λογότυπου — συγχρονισμένες με templates/reports/quote_pdf.html
LOGO_PDF_MAX_WIDTH = 180
LOGO_PDF_MAX_HEIGHT = 56
LOGO_RECOMMENDED_WIDTH = 360
LOGO_RECOMMENDED_HEIGHT = 112
LOGO_MAX_UPLOAD_WIDTH = 720
LOGO_MAX_UPLOAD_HEIGHT = 224
LOGO_MIN_WIDTH = 180
LOGO_MIN_HEIGHT = 56
LOGO_FORMATS = "PNG (διαφανές φόντο) ή JPG"


def get_logo_spec() -> dict:
    return {
        "pdf_width": LOGO_PDF_MAX_WIDTH,
        "pdf_height": LOGO_PDF_MAX_HEIGHT,
        "recommended_width": LOGO_RECOMMENDED_WIDTH,
        "recommended_height": LOGO_RECOMMENDED_HEIGHT,
        "min_width": LOGO_MIN_WIDTH,
        "min_height": LOGO_MIN_HEIGHT,
        "max_width": LOGO_MAX_UPLOAD_WIDTH,
        "max_height": LOGO_MAX_UPLOAD_HEIGHT,
        "formats": LOGO_FORMATS,
        "aspect_ratio": f"{LOGO_RECOMMENDED_WIDTH}:{LOGO_RECOMMENDED_HEIGHT}",
    }

def get_company_info() -> dict:
    profile = CompanyProfile.load()

    logo_uri = ""
    has_logo = False
    if profile.logo:
        try:
            logo_uri = Path(profile.logo.path).as_uri()
            has_logo = True
        except (ValueError, OSError):
            pass

    def pick(db_value: str, setting_name: str, default: str = "") -> str:
        if db_value and db_value.strip():
            return db_value.strip()
        return getattr(settings, setting_name, default) or ""

    return {
        "name": pick(profile.name, "COMPANY_NAME", "Vibe Electrician"),
        "tagline": pick(profile.tagline, "COMPANY_TAGLINE"),
        "address": pick(profile.address, "COMPANY_ADDRESS"),
        "phone": pick(profile.phone, "COMPANY_PHONE"),
        "email": pick(profile.email, "COMPANY_EMAIL"),
        "vat": pick(profile.vat, "COMPANY_VAT"),
        "website": pick(profile.website, "COMPANY_WEBSITE"),
        "logo_uri": logo_uri,
        "has_logo": has_logo,
    }
