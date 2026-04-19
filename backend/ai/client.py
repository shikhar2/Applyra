from backend.core.config import settings
from loguru import logger

def get_ai_client(provider: str = None):
    p = provider or settings.AI_PROVIDER
    
    try:
        if p == "anthropic" and settings.ANTHROPIC_API_KEY:
            import anthropic
            return anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            
        elif p == "openai" and settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
        elif p == "gemini" and settings.GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            return genai
            
        elif p == "groq" and settings.GROQ_API_KEY:
            try:
                from groq import AsyncGroq
                return AsyncGroq(api_key=settings.GROQ_API_KEY)
            except ImportError:
                logger.warning("Groq package not installed. run 'pip install groq'")
                return None
                
        elif p == "xai" and settings.XAI_API_KEY:
            from openai import AsyncOpenAI
            return AsyncOpenAI(api_key=settings.XAI_API_KEY, base_url="https://api.x.ai/v1")
            
    except Exception as e:
        logger.error(f"Failed to initialize AI client for {p}: {e}")
        
    return None
