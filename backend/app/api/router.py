from fastapi import APIRouter

from app.api import ai, analytics, auth, history, languages, settings as settings_api, speech, vocabulary

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(speech.router)
api_router.include_router(languages.router)
api_router.include_router(vocabulary.router)
api_router.include_router(history.router)
api_router.include_router(analytics.router)
api_router.include_router(ai.router)
api_router.include_router(settings_api.router)
