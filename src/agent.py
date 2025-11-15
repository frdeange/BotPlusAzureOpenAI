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
    RestChannelServiceClientFactory,
)
from microsoft_agents.hosting.core.authorization.auth_types import AuthTypes
from microsoft_agents.hosting.core.connector.client import UserTokenClient

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

# OAuth connection name configured in Azure Bot Service
OAUTH_CONNECTION_NAME = environ.get("OAUTH_CONNECTION_NAME", "SharePointConnection")

# Client factory for creating UserTokenClient (requires CONNECTION_MANAGER)
CLIENT_FACTORY = RestChannelServiceClientFactory(connection_manager=CONNECTION_MANAGER)

async def _get_user_token_client(context: TurnContext, state: TurnState) -> UserTokenClient:
    """
    Create a UserTokenClient for OAuth operations.
    """
    # Get the claims identity from TurnState
    # The claims identity is set by the authorization middleware
    claims_identity = state.get("ClaimsIdentity")
    
    if not claims_identity:
        # Fallback: try to get it from turn_state dict
        claims_identity = context.turn_state.get("ClaimsIdentity")
    
    if not claims_identity:
        # Last resort: create an empty one (though this shouldn't be needed with proper middleware)
        logger.warning("ClaimsIdentity not found in state, creating anonymous identity")
        from microsoft_agents.hosting.core.authorization import ClaimsIdentity
        claims_identity = ClaimsIdentity(claims=[], is_authenticated=False)
    
    # Create the user token client
    return await CLIENT_FACTORY.create_user_token_client(context, claims_identity)

@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState):
    """
    Handle new members joining the conversation.
    Sends a welcome message when users are added to the conversation.
    """
    await context.send_activity(
        "👋 Welcome! I'm your AI assistant powered by Azure OpenAI.\n\n"
        "**What I can do:**\n"
        "- Answer general questions\n"
        "- Access your Microsoft 365 files (with your permission)\n"
        "- Search your SharePoint and OneDrive\n\n"
        "**Commands:**\n"
        "- `/login` - Sign in to access your files\n"
        "- `/logout` - Sign out\n"
        "- Just ask naturally! I'll request authentication when needed.\n\n"
        "Try: *'What is Azure?'* or *'Show my recent files'*"
    )

@AGENT_APP.activity("event")
async def on_event(context: TurnContext, _state: TurnState):
    """
    Handle event activities, including OAuth token/response events.
    This is triggered when the user completes the OAuth sign-in flow.
    """
    if context.activity.name == "token/response":
        logger.info(f"User completed OAuth sign-in: {context.activity.from_property.id}")
        await context.send_activity(
            "✅ Thank you for signing in! I can now access your SharePoint files on your behalf. "
            "You can ask me things like 'list my files' or 'search for documents about X'."
        )
    else:
        logger.info(f"Event activity received: {context.activity.name}")

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
    Implements OAuth user authentication for SharePoint access.
    Uses streaming responses for better user experience.
    """
    user_message = context.activity.text
    conversation_id = context.activity.conversation.id
    
    logger.info(f"Received message from {conversation_id}: {user_message[:50]}...")
    
    # ========================================
    # SPECIAL COMMANDS
    # ========================================
    
    # Handle /login command (Microsoft Teams convention)
    if user_message and user_message.lower().strip() in ["/login", "/signin", "login", "sign in"]:
        logger.info(f"User requested login: {context.activity.from_property.id}")
        
        try:
            # Get UserTokenClient
            user_token_client = await _get_user_token_client(context, _state)
            
            # Check if already authenticated
            user_id = context.activity.from_property.id
            channel_id = context.activity.channel_id
            
            token_response = await user_token_client.user_token.get_token(
                user_id=user_id,
                connection_name=OAUTH_CONNECTION_NAME,
                channel_id=channel_id
            )
            
            if token_response and token_response.token:
                await context.send_activity("✅ You are already signed in!")
            else:
                await context.send_activity(
                    Activity(
                        type=ActivityTypes.message,
                        text="🔐 Please sign in to access your Microsoft 365 data:",
                        attachments=[
                            {
                                "contentType": "application/vnd.microsoft.card.oauth",
                                "content": {
                                    "connectionName": OAUTH_CONNECTION_NAME,
                                    "title": "Sign in",
                                    "text": "Sign in to allow me to access your files on your behalf"
                                }
                            }
                        ]
                    )
                )
        except Exception as e:
            logger.error(f"Error during login: {e}", exc_info=True)
            await context.send_activity("⚠️ An error occurred during sign-in. Please try again.")
        return
    
    # Handle /logout command
    if user_message and user_message.lower().strip() in ["/logout", "/signout", "logout", "signout", "sign out"]:
        try:
            # Get UserTokenClient
            user_token_client = await _get_user_token_client(context, _state)
            
            user_id = context.activity.from_property.id
            channel_id = context.activity.channel_id
            
            await user_token_client.user_token.sign_out(
                user_id=user_id,
                connection_name=OAUTH_CONNECTION_NAME,
                channel_id=channel_id
            )
            
            await context.send_activity("✅ You have been signed out successfully.")
            logger.info(f"User signed out: {context.activity.from_property.id}")
        except Exception as e:
            logger.error(f"Error signing out user: {e}", exc_info=True)
            await context.send_activity("Error signing out. Please try again.")
        return
    
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
    # OAUTH USER AUTHENTICATION
    # ========================================
    # Check if user authentication is required (based on user's request)
    requires_auth = _requires_user_authentication(user_message)
    
    if requires_auth:
        try:
            # Get UserTokenClient
            user_token_client = await _get_user_token_client(context, _state)
            
            user_id = context.activity.from_property.id
            channel_id = context.activity.channel_id
            
            # Try to get the user's OAuth token
            token_response = await user_token_client.user_token.get_token(
                user_id=user_id,
                connection_name=OAUTH_CONNECTION_NAME,
                channel_id=channel_id
            )
            
            if not token_response or not token_response.token:
                # User is not authenticated - send OAuth card
                logger.info(f"User not authenticated, sending OAuth card to {user_id}")
                
                await context.send_activity(
                    Activity(
                        type=ActivityTypes.message,
                        text="🔐 To access your SharePoint files, please sign in:",
                        attachments=[
                            {
                                "contentType": "application/vnd.microsoft.card.oauth",
                                "content": {
                                    "connectionName": OAUTH_CONNECTION_NAME,
                                    "title": "Sign in",
                                    "text": "Please sign in to allow me to access your files on your behalf"
                                }
                            }
                        ]
                    )
                )
                return
            
            # User is authenticated - we have their token
            user_token = token_response.token
            logger.info(f"User {user_id} authenticated successfully for SharePoint access")
            
            # ========================================
            # ACCESS MICROSOFT GRAPH WITH USER TOKEN
            # ========================================
            graph_data = await _call_microsoft_graph(user_token, user_message)
            
            # Include Graph data in the AI context
            system_message = (
                "You are a helpful AI assistant with access to the user's Microsoft 365 data. "
                "Use the following data from Microsoft Graph to help answer the user's question:\n\n"
                f"{graph_data}\n\n"
                "Provide a helpful and natural response based on this data."
            )
        except Exception as e:
            logger.error(f"Error accessing Microsoft Graph: {e}", exc_info=True)
            await context.send_activity(
                "⚠️ I encountered an error accessing your files. Please try again or contact support."
            )
            return
    else:
        # No authentication required - use standard system message
        system_message = "You are a helpful AI assistant. Respond naturally and helpfully to user queries."
    
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
                {"role": "system", "content": system_message},
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


# ========================================
# HELPER FUNCTIONS
# ========================================

def _requires_user_authentication(message: str) -> bool:
    """
    Determine if the user's message requires authentication to access their data.
    Uses keyword detection for fast response.
    You can enhance this with AI classification for more sophisticated detection.
    """
    if not message:
        return False
    
    message_lower = message.lower()
    
    # Explicit commands
    if message_lower.strip() in ["/login", "/signin", "login", "sign in"]:
        return True
    
    # Keywords that indicate the user wants to access their personal data
    auth_keywords = [
        # File operations
        "my files", "my documents", "my sharepoint", "my onedrive",
        "list files", "search files", "find files", "show files",
        "recent files", "shared with me", "my folders",
        "upload", "download", "create file", "delete file",
        
        # SharePoint specific
        "sharepoint site", "team site", "document library",
        
        # Email/Calendar (if you add those scopes)
        "my emails", "my calendar", "my meetings",
        
        # Teams specific
        "my teams", "my channels",
        
        # Generic personal data
        "my data", "my information", "access my",
    ]
    
    # Check for any keyword match
    if any(keyword in message_lower for keyword in auth_keywords):
        return True
    
    # Check for possessive patterns like "show me my..." or "get my..."
    possessive_patterns = ["show me my", "get my", "find my", "search my", "list my"]
    if any(pattern in message_lower for pattern in possessive_patterns):
        return True
    
    return False


async def _call_microsoft_graph(user_token: str, user_query: str) -> str:
    """
    Call Microsoft Graph API with the user's token to access their data.
    This is a simple example that retrieves the user's OneDrive files.
    You can expand this to access SharePoint sites, search, etc.
    """
    import aiohttp
    
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }
    
    graph_data = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # Example 1: Get user's profile
            async with session.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            ) as response:
                if response.status == 200:
                    user_profile = await response.json()
                    graph_data.append(f"User: {user_profile.get('displayName')} ({user_profile.get('mail')})")
            
            # Example 2: Get user's recent OneDrive files
            async with session.get(
                "https://graph.microsoft.com/v1.0/me/drive/recent?$top=10",
                headers=headers
            ) as response:
                if response.status == 200:
                    recent_files = await response.json()
                    files_list = []
                    for item in recent_files.get("value", []):
                        file_name = item.get("name", "Unknown")
                        last_modified = item.get("lastModifiedDateTime", "Unknown")
                        web_url = item.get("webUrl", "")
                        files_list.append(f"- {file_name} (modified: {last_modified})")
                    
                    if files_list:
                        graph_data.append("Recent files:\n" + "\n".join(files_list))
                    else:
                        graph_data.append("No recent files found.")
            
            # Example 3: Search for files based on query (if query contains search intent)
            if any(keyword in user_query.lower() for keyword in ["search", "find", "look for"]):
                search_query = user_query.split("search")[-1].split("find")[-1].strip()
                if search_query:
                    async with session.get(
                        f"https://graph.microsoft.com/v1.0/me/drive/root/search(q='{search_query}')?$top=5",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            search_results = await response.json()
                            results_list = []
                            for item in search_results.get("value", []):
                                file_name = item.get("name", "Unknown")
                                results_list.append(f"- {file_name}")
                            
                            if results_list:
                                graph_data.append(f"Search results for '{search_query}':\n" + "\n".join(results_list))
        
        return "\n\n".join(graph_data) if graph_data else "No data retrieved from Microsoft Graph."
        
    except Exception as e:
        logger.error(f"Error calling Microsoft Graph: {e}", exc_info=True)
        raise