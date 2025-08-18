# -*- coding: utf-8 -*-
"""
Centralized error handling utilities
"""
from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class ServiceError(Exception):
    """Base service error class"""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class WikipediaError(ServiceError):
    """Wikipedia API related errors"""
    pass


class LLMError(ServiceError):
    """LLM processing related errors"""
    pass


class CacheError(ServiceError):
    """Cache operation related errors"""
    pass


def handle_service_error(func):
    """
    Decorator for standardized error handling in service methods
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ServiceError:
            # Re-raise our own service errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            # Convert unknown errors to ServiceError
            raise ServiceError(
                message=f"Service operation failed: {str(e)}",
                error_code="INTERNAL_ERROR",
                details={"function": func.__name__, "original_error": str(e)}
            )
    return wrapper


def log_and_raise_error(error_type: type, message: str, error_code: str, 
                       original_exception: Optional[Exception] = None, 
                       details: Optional[Dict[str, Any]] = None):
    """
    Helper function to log and raise standardized errors
    """
    if original_exception:
        logger.error(f"{message}: {str(original_exception)}")
        if details is None:
            details = {}
        details["original_error"] = str(original_exception)
    else:
        logger.error(message)
    
    raise error_type(message=message, error_code=error_code, details=details)