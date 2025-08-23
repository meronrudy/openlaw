# CAP Caselaw Plugin
# Harvard Law Case Access Project integration for OpenLaw
# Provides provenance-first access to 37M+ case law documents

from .plugin import CaselawPlugin

__version__ = "1.0.0"
__plugin_name__ = "caselaw_access_project"
__plugin_display_name__ = "Case Law Access Project"

# Plugin exports for OpenLaw core system
__all__ = [
    "CaselawPlugin"
]