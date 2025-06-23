from google.adk.agents import Agent,LlmAgent,ParallelAgent
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel, Field
from typing import Optional, List
from Content_Studio.prompts import Model_System_Message
from Content_Studio.tools import update_company_info,generate_topic,custom_topic
from langchain_anthropic import ChatAnthropic
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv
from .sub_agents.Competitor_Analysis.agent1 import Competitor_Analysis 
from .sub_agents.Article_Fetcher.agent import Article_Fetcher
from .sub_agents.Linkedin_Content_Drafter.agent import Linkedin_Content_Drafter
from .sub_agents.X_Tweet_Content_Drafter.agent import X_Tweet_Content_Drafter
from .sub_agents.X_thread_Content_Drafter.agent import X_Thread_Content_Drafter
from .sub_agents.Instagram_Content_Drafter.agent import Instagram_Content_Drafter
from .sub_agents.Posting_Agent.agent import Posting_Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from google.adk.tools.agent_tool import AgentTool
# from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters
# from custom_adk_patches import CustomMCPToolset as MCPToolset
load_dotenv()


import os 
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key="AIzaSyDESOxZI59FnrmzhElQ7BCmBzqTwM0F-V8"  # or set as env var
)

# model = LiteLlm(
#     model="anthropic/claude-3-haiku-20240307",  # or latest anthopic model
#     api_key=os.environ.get("ANTHROPIC_API_KEY")
# )
# Create a simple persistent agent



root_agent = LlmAgent(
    name="Content_Studio",
    model="gemini-2.0-flash",
    description="A smart content creator agent",
    instruction=Model_System_Message,
    tools=[
        update_company_info,
        generate_topic,
        custom_topic,
        
        
    ],
    sub_agents=[
        Competitor_Analysis,
        Article_Fetcher,
        Linkedin_Content_Drafter,
        X_Tweet_Content_Drafter,
        X_Thread_Content_Drafter,
        Posting_Agent,
        Instagram_Content_Drafter,
    ],
)




