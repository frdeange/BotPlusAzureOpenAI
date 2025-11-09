from os import environ
from microsoft_agents.hosting.core import AgentApplication, AgentAuthConfiguration
from microsoft_agents.hosting.aiohttp import (
    start_agent_process,
    jwt_authorization_middleware,
    CloudAdapter,
)
from aiohttp.web import Request, Response, Application, run_app

def start_server(
    agent_application: AgentApplication, auth_configuration: AgentAuthConfiguration
):
    async def entry_point(req: Request) -> Response:
        agent: AgentApplication = req.app["agent_app"]
        adapter: CloudAdapter = req.app["adapter"]
        return await start_agent_process(
            req,
            agent,
            adapter,
        )

    APP = Application(middlewares=[jwt_authorization_middleware])
    APP.router.add_post("/api/messages", entry_point)
    APP["agent_configuration"] = auth_configuration
    APP["agent_app"] = agent_application
    APP["adapter"] = agent_application.adapter

    # Azure App Service exposes the port via PORT environment variable
    # Default to 8000 if not set (for local development)
    port = int(environ.get("PORT", 8000))
    
    # Use 0.0.0.0 to accept external connections (required in Azure)
    # In production, Azure handles the external routing
    host = "0.0.0.0"

    try:
        run_app(APP, host=host, port=port)
    except Exception as error:
        raise error