from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import time
import asyncio

from app.core.database import get_db
from app.models.user_settings import UserSettings
from app.schemas.settings import (
    UserSettingsUpdate, 
    UserSettingsResponse, 
    LLMServiceInfo, 
    LLMServicesResponse,
    LLMServiceTestRequest,
    LLMServiceTestResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/user", response_model=UserSettingsResponse)
async def get_user_settings(db: AsyncSession = Depends(get_db)):
    """Get user settings"""
    try:
        result = await db.execute(select(UserSettings).limit(1))
        settings = result.scalar_one_or_none()
        
        if not settings:
            # Create default settings
            settings = UserSettings()
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        
        return UserSettingsResponse(
            id=settings.id,  # type: ignore
            theme=settings.theme,  # type: ignore
            default_llm_service=settings.default_llm_service,  # type: ignore
            has_gemini_api_key=bool(settings.gemini_api_key),
            has_openai_api_key=bool(settings.openai_api_key),
            has_claude_api_key=bool(settings.claude_api_key),
            ollama_base_url=settings.ollama_base_url,  # type: ignore
            ollama_model=settings.ollama_model,  # type: ignore
            openai_model=settings.openai_model,  # type: ignore
            openai_base_url=settings.openai_base_url,  # type: ignore
            claude_model_name=settings.claude_model_name,  # type: ignore
            vertex_project_id=settings.vertex_project_id,  # type: ignore
            default_output_format=settings.default_output_format,  # type: ignore
            default_use_llm=settings.default_use_llm,  # type: ignore
            default_force_ocr=settings.default_force_ocr,  # type: ignore
            default_format_lines=settings.default_format_lines,  # type: ignore
            additional_settings=settings.additional_settings  # type: ignore
        )
        
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        raise HTTPException(status_code=500, detail="Error getting user settings")

@router.put("/user", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update user settings"""
    try:
        result = await db.execute(select(UserSettings).limit(1))
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = UserSettings()
            db.add(settings)
        
        # Update fields
        update_data = settings_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)
        
        await db.commit()
        await db.refresh(settings)
        
        return UserSettingsResponse(
            id=settings.id,  # type: ignore
            theme=settings.theme,  # type: ignore
            default_llm_service=settings.default_llm_service,  # type: ignore
            has_gemini_api_key=bool(settings.gemini_api_key),
            has_openai_api_key=bool(settings.openai_api_key),
            has_claude_api_key=bool(settings.claude_api_key),
            ollama_base_url=settings.ollama_base_url,  # type: ignore
            ollama_model=settings.ollama_model,  # type: ignore
            openai_model=settings.openai_model,  # type: ignore
            openai_base_url=settings.openai_base_url,  # type: ignore
            claude_model_name=settings.claude_model_name,  # type: ignore
            vertex_project_id=settings.vertex_project_id,  # type: ignore
            default_output_format=settings.default_output_format,  # type: ignore
            default_use_llm=settings.default_use_llm,  # type: ignore
            default_force_ocr=settings.default_force_ocr,  # type: ignore
            default_format_lines=settings.default_format_lines,  # type: ignore
            additional_settings=settings.additional_settings  # type: ignore
        )
        
    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        raise HTTPException(status_code=500, detail="Error updating user settings")

@router.get("/llm-services", response_model=LLMServicesResponse)
async def get_llm_services():
    """Get available LLM services"""
    services = [
        LLMServiceInfo(
            name="marker.services.gemini.GoogleGeminiService",
            display_name="Google Gemini",
            requires_api_key=True,
            models=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            description="Google's Gemini AI models via API"
        ),
        LLMServiceInfo(
            name="marker.services.openai.OpenAIService",
            display_name="OpenAI",
            requires_api_key=True,
            models=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            description="OpenAI GPT models"
        ),
        LLMServiceInfo(
            name="marker.services.claude.ClaudeService",
            display_name="Anthropic Claude",
            requires_api_key=True,
            models=["claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
            description="Anthropic's Claude AI models"
        ),
        LLMServiceInfo(
            name="marker.services.ollama.OllamaService",
            display_name="Ollama (Local)",
            requires_api_key=False,
            models=["llama3.2"],
            description="Local LLM models via Ollama"
        ),
        LLMServiceInfo(
            name="marker.services.vertex.GoogleVertexService",
            display_name="Google Vertex AI",
            requires_api_key=False,
            models=["gemini-pro", "gemini-pro-vision"],
            description="Google's Vertex AI platform"
        )
    ]
    
    return LLMServicesResponse(services=services)

@router.post("/llm-services/test", response_model=LLMServiceTestResponse)
async def test_llm_service_connection(
    test_request: LLMServiceTestRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test LLM service connection"""
    try:
        start_time = time.time()
        
        # Get user settings for fallback values
        result = await db.execute(select(UserSettings).limit(1))
        settings = result.scalar_one_or_none()
        
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

async def _test_gemini_connection(test_request: LLMServiceTestRequest, settings: UserSettings) -> tuple[bool, str]:
    """Test Gemini API connection"""
    try:
        import google.generativeai as genai
        import asyncio
        
        api_key = test_request.gemini_api_key or (settings.gemini_api_key if settings else None)
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

async def _test_openai_connection(test_request: LLMServiceTestRequest, settings: UserSettings) -> tuple[bool, str]:
    """Test OpenAI API connection"""
    try:
        import openai
        
        api_key = test_request.openai_api_key or (settings.openai_api_key if settings else None)
        if not api_key:
            return False, "API key not provided"
        
        base_url = test_request.openai_base_url or (settings.openai_base_url if settings else None)
        model = test_request.openai_model or (settings.openai_model if settings else "gpt-4o")
        
        # Set default OpenAI base URL if not provided
        if not base_url:
            base_url = "https://api.openai.com/v1"
        
        # Use AsyncOpenAI for proper async handling
        try:
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            # Test with a simple request
            response = await client.chat.completions.create(
                model=model,
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

async def _test_claude_connection(test_request: LLMServiceTestRequest, settings: UserSettings) -> tuple[bool, str]:
    """Test Claude API connection"""
    try:
        import anthropic
        
        api_key = test_request.claude_api_key or (settings.claude_api_key if settings else None)
        if not api_key:
            return False, "API key not provided"
        
        model = test_request.claude_model_name or (settings.claude_model_name if settings else "claude-3-sonnet-20240229")
        
        try:
            client = anthropic.AsyncAnthropic(api_key=api_key)
            
            # Test with a simple request
            response = await client.messages.create(
                model=model,
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

async def _test_ollama_connection(test_request: LLMServiceTestRequest, settings: UserSettings) -> tuple[bool, str]:
    """Test Ollama connection"""
    try:
        import aiohttp
        
        base_url = test_request.ollama_base_url or (settings.ollama_base_url if settings else "http://localhost:11434")
        model = test_request.ollama_model or (settings.ollama_model if settings else "llama3.2")
        
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
    except asyncio.TimeoutError:
        return False, "Connection timeout - Ollama server may not be running"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

async def _test_vertex_connection(test_request: LLMServiceTestRequest, settings: UserSettings) -> tuple[bool, str]:
    """Test Vertex AI connection"""
    try:
        project_id = test_request.vertex_project_id or (settings.vertex_project_id if settings else None)
        if not project_id:
            return False, "Project ID not provided"
        
        # For Vertex AI, we need to check if the credentials are properly configured
        # This is a basic check - in production you might want to make an actual API call
        import google.auth
        
        try:
            credentials, project = google.auth.default()
            if credentials:
                return True, "Credentials found - connection likely successful"
            else:
                return False, "No valid credentials found"
        except google.auth.exceptions.DefaultCredentialsError:
            return False, "No valid credentials found. Please configure Google Cloud authentication."
            
    except ImportError:
        return False, "Google Cloud libraries not installed"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

@router.get("/llm-services/configured", response_model=LLMServicesResponse)
async def get_configured_llm_services(db: AsyncSession = Depends(get_db)):
    """Get only configured LLM services"""
    try:
        # Get user settings
        result = await db.execute(select(UserSettings).limit(1))
        settings = result.scalar_one_or_none()
        
        all_services = [
            LLMServiceInfo(
                name="marker.services.gemini.GoogleGeminiService",
                display_name="Google Gemini",
                requires_api_key=True,
                models=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
                description="Google's Gemini AI models via API"
            ),
            LLMServiceInfo(
                name="marker.services.openai.OpenAIService",
                display_name="OpenAI",
                requires_api_key=True,
                models=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                description="OpenAI GPT models"
            ),
            LLMServiceInfo(
                name="marker.services.claude.ClaudeService",
                display_name="Anthropic Claude",
                requires_api_key=True,
                models=["claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
                description="Anthropic's Claude AI models"
            ),
            LLMServiceInfo(
                name="marker.services.ollama.OllamaService",
                display_name="Ollama (Local)",
                requires_api_key=False,
                models=["llama3.2"],
                description="Local LLM models via Ollama"
            ),
            LLMServiceInfo(
                name="marker.services.vertex.GoogleVertexService",
                display_name="Google Vertex AI",
                requires_api_key=False,
                models=["gemini-pro", "gemini-pro-vision"],
                description="Google's Vertex AI platform"
            )
        ]
        
        if not settings:
            # If no settings, only return services that don't require API keys
            configured_services = [s for s in all_services if not s.requires_api_key]
        else:
            configured_services = []
            for service in all_services:
                if service.name == "marker.services.gemini.GoogleGeminiService" and settings.gemini_api_key:
                    configured_services.append(service)
                elif service.name == "marker.services.openai.OpenAIService" and settings.openai_api_key:
                    configured_services.append(service)
                elif service.name == "marker.services.claude.ClaudeService" and settings.claude_api_key:
                    configured_services.append(service)
                elif service.name == "marker.services.ollama.OllamaService":
                    # Ollama is always considered configured if base URL is set
                    if settings.ollama_base_url:
                        configured_services.append(service)
                elif service.name == "marker.services.vertex.GoogleVertexService":
                    # Vertex is considered configured if project ID is set
                    if settings.vertex_project_id:
                        configured_services.append(service)
        
        return LLMServicesResponse(services=configured_services)
        
    except Exception as e:
        logger.error(f"Error getting configured LLM services: {e}")
        raise HTTPException(status_code=500, detail="Error getting configured LLM services")

@router.get("/ollama/models")
async def get_ollama_models(base_url: str = "http://localhost:11434"):
    """Get available models from Ollama server"""
    try:
        import aiohttp
        
        # Clean up the base URL
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"http://{base_url}"
        
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to connect to Ollama server at {base_url} (HTTP {response.status})"
                    )
                
                data = await response.json()
                models = []
                
                for model_info in data.get('models', []):
                    model_name = model_info.get('name', '')
                    if model_name:
                        # Remove tag suffix if present (e.g., "llama3.2:latest" -> "llama3.2")
                        base_name = model_name.split(':')[0]
                        if base_name not in models:
                            models.append(base_name)
                
                return {"models": sorted(models)}
                
    except ImportError:
        raise HTTPException(status_code=500, detail="aiohttp library not installed")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=400, detail=f"Connection timeout - Ollama server at {base_url} may not be running")
    except Exception as e:
        logger.error(f"Error fetching Ollama models from {base_url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch models: {str(e)}") 