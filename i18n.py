from fastapi import Request
from babel.support import Translations
import os

class TranslationManager:
    def __init__(self, translations_dir: str = 'translations'):
        self.translations_dir = translations_dir

    def get_translations(self, locale: str = 'zh'):
        """
        Get translations for a specific locale using Babel
        
        :param locale: Language code (e.g., 'en', 'zh')
        :return: Translations object
        """
        translations_path = os.path.join(self.translations_dir, locale, 'LC_MESSAGES', 'messages.mo')
        if os.path.exists(translations_path):
            return Translations.load(self.translations_dir, [locale])
        return None

    def get_locale(self, request: Request) -> str:
        """
        Detect locale from request
        
        :param request: FastAPI request object
        :return: Detected locale code
        """
        # Always return Chinese for now
        return 'zh'

    def install_translations(self, env, locale: str = 'zh'):
        """
        Install translations into Jinja2 environment
        
        :param env: Jinja2 environment
        :param locale: Language code
        """
        translations = self.get_translations(locale)
        if translations:
            env.globals['_'] = translations.gettext
        else:
            # Fallback to returning the original text if no translations found
            env.globals['_'] = lambda x: x

# Global translation manager
translation_manager = TranslationManager()

def gettext(message: str, locale: str = 'zh') -> str:
    """
    Translate a message to the specified locale
    
    :param message: Message to translate
    :param locale: Target locale
    :return: Translated message
    """
    translations = translation_manager.get_translations(locale)
    if translations:
        return translations.gettext(message)
    return message

# Alias for convenience
_ = gettext
