# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""
Bot agent logic using Microsoft Agents SDK with Azure OpenAI.
Supports multi-tenant scenarios with optional tenant validation.
Configured for User-Assigned Managed Identity authentication.
"""

from os import environ
import logging

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.authentication.msal import MsalConnectionManager

from microsoft_agents.hosting.core import (
    Authorization,
    AgentApplication,
    AgentAuthConfiguration,
    TurnState,
    TurnContext,
    MemoryStorage,
)
from microsoft_agents.hosting.core.authorization.auth_types import AuthTypes

from microsoft_agents.activity import (
    load_configuration_from_env,
    Activity,
    ActivityTypes,
    SensitivityUsageInfo
)

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Load Microsoft Agents SDK configuration from environment
# This reads MicrosoftAppType, MicrosoftAppId, MicrosoftAppTenantId, etc.
agents_sdk_config = load_configuration_from_env(environ)

# Configure the managed identity service connection used across the bot
_service_connection_settings = {
    "auth_type": AuthTypes.user_managed_identity,
    "client_id": environ.get("MicrosoftAppId"),
    "tenant_id": environ.get("MicrosoftAppTenantId"),
    "scopes": ["https://api.botframework.com/.default"],
}

CONNECTION_MANAGER = MsalConnectionManager(
    CONNECTIONS={
        "SERVICE_CONNECTION": {
            "SETTINGS": _service_connection_settings
        }
    }
)

# Create auth configuration for the server middleware (jwt_authorization_middleware)
AUTH_CONFIG = CONNECTION_MANAGER.get_default_connection_configuration()

# Initialize bot components
STORAGE = MemoryStorage()
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)

AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE, adapter=ADAPTER, authorization=AUTHORIZATION, **agents_sdk_config
)

# Initialize Azure OpenAI client
CLIENT = AsyncAzureOpenAI(
    api_version=environ["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=environ["AZURE_OPENAI_ENDPOINT"],
    api_key=environ["AZURE_OPENAI_API_KEY"]
)

@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState):
    """
    Handle new members joining the conversation.
    Sends a welcome message when users are added to the conversation.
    """
    await context.send_activity(
        "Welcome! I'm your AI assistant powered by Azure OpenAI. Ask me anything!"
    )

@AGENT_APP.activity("invoke")
async def invoke(context: TurnContext, _state: TurnState) -> str:
    """
    Handle invoke activities from the Bot Framework.
    Internal method to process template expansion or function invocation.
    """
    invoke_response = Activity(
        type=ActivityTypes.invoke_response, value={"status": 200}
    )
    logger.info(f"Invoke activity received: {context.activity.type}")
    await context.send_activity(invoke_response)

# Listen for ANY message to be received. MUST BE AFTER ANY OTHER MESSAGE HANDLERS
@AGENT_APP.activity(ActivityTypes.message)
async def on_message(context: TurnContext, _state: TurnState):
    """
    Main message handler: captures user messages and forwards to Azure OpenAI.
    Includes optional tenant validation for multi-tenant scenarios.
    Uses streaming responses for better user experience.
    """
    user_message = context.activity.text
    conversation_id = context.activity.conversation.id
    
    logger.info(f"Received message from {conversation_id}: {user_message[:50]}...")
    
    # ========================================
    # MULTI-TENANT VALIDATION (Optional)
    # ========================================
    # Only enforced if ALLOWED_TENANTS environment variable is configured
    # This allows you to restrict which Azure AD tenants can use this bot
    allowed_tenants_str = environ.get("ALLOWED_TENANTS", "").strip()
    
    if allowed_tenants_str:
        allowed_tenants = [t.strip() for t in allowed_tenants_str.split(",") if t.strip()]
        
        # Get tenant ID from conversation (available in Teams/Microsoft 365 scenarios)
        # For other channels, this might be None
        user_tenant_id = getattr(context.activity.conversation, "tenant_id", None)
        
        if user_tenant_id and allowed_tenants:
            if user_tenant_id not in allowed_tenants:
                logger.warning(
                    f"Unauthorized tenant access attempt: {user_tenant_id}. "
                    f"Allowed tenants: {allowed_tenants}"
                )
                await context.send_activity(
                    "I'm sorry, but your organization is not authorized to use this bot. "
                    "Please contact your administrator for access."
                )
                return
            else:
                logger.info(f"Tenant {user_tenant_id} authorized successfully")
    
    # ========================================
    # AZURE OPENAI STREAMING RESPONSE
    # ========================================
    # Use streaming response for better UX
    context.streaming_response.set_feedback_loop(True)
    context.streaming_response.set_generated_by_ai_label(True)
    
    try:
        # Call Azure OpenAI with streaming enabled
        streamed_response = await CLIENT.chat.completions.create(
            model=environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful AI assistant. Respond naturally and helpfully to user queries."
                },
                {"role": "user", "content": user_message}
            ],
            stream=True,
        )
        
        # Stream the response chunks back to the user
        async for chunk in streamed_response:
            if chunk.choices and chunk.choices[0].delta.content:
                context.streaming_response.queue_text_chunk(chunk.choices[0].delta.content)
                
        logger.info(f"Successfully sent streaming response to {conversation_id}")
        
    except Exception as e:
        logger.error(f"Error during Azure OpenAI streaming: {e}", exc_info=True)
        context.streaming_response.queue_text_chunk(
            "An error occurred while processing your message. Please try again later."
        )
    finally:
        # Always end the stream
        await context.streaming_response.end_stream()