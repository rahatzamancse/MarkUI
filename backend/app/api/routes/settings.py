from fastapi import APIRouter, HTTPException, Depends
import logging
import time
import asyncio

from app.core.redis_client import get_redis, RedisClient
from app.core.config import get_settings
from app.schemas.settings import (
    LLMServiceTestRequest,
    LLMServiceTestResponse,
    ServerConfigResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/server-config", response_model=ServerConfigResponse)
async def get_server_config():
    """Get server configuration (environment variables availability)"""
    try:
        settings = get_settings()
        
        return ServerConfigResponse(
            # Check if API keys are available from environment variables
            has_gemini_api_key=bool(settings.gemini_api_key),
            has_openai_api_key=bool(settings.openai_api_key),
            has_claude_api_key=bool(settings.claude_api_key),
            
            # Default configurations from environment
            default_openai_model=settings.openai_model,
            default_openai_base_url=settings.openai_base_url,
            default_claude_model_name=settings.claude_model_name,
            default_ollama_base_url=settings.ollama_base_url,
            default_ollama_model=settings.ollama_model,
            default_vertex_project_id=settings.vertex_project_id
        )
        
    except Exception as e:
        logger.error(f"Error getting server config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get server configuration")

@router.post("/llm-services/test", response_model=LLMServiceTestResponse)
async def test_llm_service_connection(
    test_request: LLMServiceTestRequest,
    redis: RedisClient = Depends(get_redis)
):
    """Test LLM service connection"""
    try:
        start_time = time.time()
        
        # Get user settings for fallback values
        settings = await redis.get_user_settings()
        
        service_name = test_request.service_name
        
        # Test connection based on service type
        if "gemini" in service_name.lower():
            success, message = await _test_gemini_connection(test_request, settings)
        elif "openai" in service_name.lower():
            success, message = await _test_openai_connection(test_request, settings)
        elif "claude" in service_name.lower():
            success, message = await _test_claude_connection(test_request, settings)
        elif "ollama" in service_name.lower():
            success, message = await _test_ollama_connection(test_request, settings)
        elif "vertex" in service_name.lower():
            success, message = await _test_vertex_connection(test_request, settings)
        else:
            return LLMServiceTestResponse(
                service_name=service_name,
                success=False,
                message="Unknown service type",
                error_details="Service type not recognized"
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return LLMServiceTestResponse(
            service_name=service_name,
            success=success,
            message=message,
            response_time_ms=response_time_ms
        )
        
    except Exception as e:
        logger.error(f"Error testing LLM service {test_request.service_name}: {e}")
        return LLMServiceTestResponse(
            service_name=test_request.service_name,
            success=False,
            message="Connection test failed",
            error_details=str(e)
        )

async def _test_gemini_connection(test_request: LLMServiceTestRequest, settings: dict | None) -> tuple[bool, str]:
    """Test Gemini API connection"""
    try:
        import google.generativeai as genai
        import asyncio
        
        # Try to get API key from: 1) request, 2) user settings, 3) server environment
        api_key = (
            test_request.gemini_api_key or 
            (settings.get("gemini_api_key") if settings else None) or
            get_settings().gemini_api_key
        )
        
        if not api_key:
            return False, "API key not provided"
        
        genai.configure(api_key=api_key)
        
        try:
            # Test with a simple request using asyncio timeout
            model = genai.GenerativeModel('gemini-pro')
            
            # Run the synchronous call in a thread with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, "Hello"),
                timeout=30.0
            )
            
            if response and response.text:
                return True, "Connection successful"
            else:
                return False, "No response received"
                
        except asyncio.TimeoutError:
            return False, "Request timeout"
        except Exception as e:
            error_msg = str(e).lower()
            if "api_key" in error_msg or "authentication" in error_msg:
                return False, "Invalid API key"
            elif "quota" in error_msg or "rate" in error_msg:
                return False, "Rate limit exceeded"
            elif "not found" in error_msg:
                return False, "Model not found"
            else:
                return False, f"API error: {str(e)}"
            
    except ImportError:
        return False, "Gemini library not installed"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

async def _test_openai_connection(test_request: LLMServiceTestRequest, settings: dict | None) -> tuple[bool, str]:
    """Test OpenAI API connection"""
    try:
        import openai
        
        # Try to get API key from: 1) request, 2) user settings, 3) server environment
        api_key = (
            test_request.openai_api_key or 
            (settings.get("openai_api_key") if settings else None) or
            get_settings().openai_api_key
        )
        
        if not api_key:
            return False, "API key not provided"
        
        base_url = test_request.openai_base_url or (settings.get("openai_base_url") if settings else None)
        model = test_request.openai_model or (settings.get("openai_model") if settings else "gpt-4o")
        
        # Set default OpenAI base URL if not provided
        if not base_url:
            base_url = "https://api.openai.com/v1"
        
        # Use AsyncOpenAI for proper async handling
        try:
            client = openai.AsyncOpenAI(
                api_key=str(api_key),
                base_url=str(base_url)
            )
            
            # Test with a simple request
            response = await client.chat.completions.create(
                model=str(model),
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
                timeout=30.0  # 30 second timeout
            )
            
            if response and response.choices:
                return True, "Connection successful"
            else:
                return False, "No response received"
                
        except openai.AuthenticationError:
            return False, "Invalid API key"
        except openai.RateLimitError:
            return False, "Rate limit exceeded"
        except openai.APITimeoutError:
            return False, "Request timeout"
        except openai.APIConnectionError as e:
            return False, f"Connection error: {str(e)}"
        except openai.BadRequestError as e:
            return False, f"Bad request: {str(e)}"
        except openai.NotFoundError:
            return False, f"Model '{model}' not found"
        except openai.APIError as e:
            return False, f"API error: {str(e)}"
            
    except ImportError:
        return False, "OpenAI library not installed"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

async def _test_claude_connection(test_request: LLMServiceTestRequest, settings: dict | None) -> tuple[bool, str]:
    """Test Claude API connection"""
    try:
        import anthropic
        
        # Try to get API key from: 1) request, 2) user settings, 3) server environment
        api_key = (
            test_request.claude_api_key or 
            (settings.get("claude_api_key") if settings else None) or
            get_settings().claude_api_key
        )
        
        if not api_key:
            return False, "API key not provided"
        
        model = test_request.claude_model_name or (settings.get("claude_model_name") if settings else "claude-3-sonnet-20240229")
        
        try:
            client = anthropic.AsyncAnthropic(api_key=str(api_key))
            
            # Test with a simple request
            response = await client.messages.create(
                model=str(model),
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}],
                timeout=30.0  # 30 second timeout
            )
            
            if response and response.content:
                return True, "Connection successful"
            else:
                return False, "No response received"
                
        except anthropic.AuthenticationError:
            return False, "Invalid API key"
        except anthropic.RateLimitError:
            return False, "Rate limit exceeded"
        except anthropic.APITimeoutError:
            return False, "Request timeout"
        except anthropic.APIConnectionError as e:
            return False, f"Connection error: {str(e)}"
        except anthropic.BadRequestError as e:
            return False, f"Bad request: {str(e)}"
        except anthropic.NotFoundError:
            return False, f"Model '{model}' not found"
        except anthropic.APIError as e:
            return False, f"API error: {str(e)}"
            
    except ImportError:
        return False, "Anthropic library not installed"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

async def _test_ollama_connection(test_request: LLMServiceTestRequest, settings: dict | None) -> tuple[bool, str]:
    """Test Ollama connection"""
    try:
        import aiohttp
        
        base_url = test_request.ollama_base_url or (settings.get("ollama_base_url") if settings else "http://localhost:11434")
        model = test_request.ollama_model or (settings.get("ollama_model") if settings else "llama3.2")
        
        # Test connection to Ollama server
        async with aiohttp.ClientSession() as session:
            # First check if server is running
            async with session.get(f"{base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status != 200:
                    return False, f"Ollama server not accessible (HTTP {response.status})"
                
                tags_data = await response.json()
                available_models = [model_info['name'] for model_info in tags_data.get('models', [])]
                
                if not available_models:
                    return False, "No models available in Ollama"
                
                # Check if the specified model is available
                if model not in available_models:
                    return False, f"Model '{model}' not found. Available models: {', '.join(available_models)}"
                
                # Test generation with the model
                test_payload = {
                    "model": model,
                    "prompt": "Hello",
                    "stream": False
                }
                
                async with session.post(f"{base_url}/api/generate", json=test_payload, timeout=aiohttp.ClientTimeout(total=10)) as gen_response:
                    if gen_response.status == 200:
                        return True, "Connection successful"
                    else:
                        return False, f"Model generation failed (HTTP {gen_response.status})"
                        
    except ImportError:
        return False, "aiohttp library not installed"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

async def _test_vertex_connection(test_request: LLMServiceTestRequest, settings: dict | None) -> tuple[bool, str]:
    """Test Vertex AI connection"""
    try:
        # Vertex AI testing would require more complex setup
        # For now, just return a placeholder
        project_id = test_request.vertex_project_id or (settings.get("vertex_project_id") if settings else None)
        if not project_id:
            return False, "Project ID not provided"
        
        # TODO: Implement actual Vertex AI connection test
        return False, "Vertex AI testing not implemented yet"
        
    except Exception as e:
        return False, f"Connection failed: {str(e)}" 