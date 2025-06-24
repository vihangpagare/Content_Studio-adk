from google.adk.tools.tool_context import ToolContext
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field
from typing import List, Optional,Dict,Any
from Content_Studio.prompts import Update_memory_prompt,topic_prompt,custom_topic_prompt
from datetime import datetime
from enum import Enum
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from google.adk.agents import Agent,LlmAgent,ParallelAgent
load_dotenv()
import os 
from google.adk.tools import google_search
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY")  # or set as env var
)

# Enhanced Company Profile Schema
class CompanyProfile(BaseModel):
    """Comprehensive company profile for LinkedIn content generation"""
    
    # Core Company Information
    company_name: str = Field(None, description="Official company name")
    company_work: str= Field(None, description="Work Overview of what the company does")
    linkedin_page_url: str = Field(None, description="Company LinkedIn page URL")
    
    # Business Identity
    tagline: str = Field(None,description="Company tagline/elevator pitch")
    mission_statement: str = Field(None, description="Company mission statement")
    value_proposition: str = Field(None, description="Unique value proposition")
    brand_voice: str = Field(None, description="Brand voice and tone guidelines")
    
    # Industry & Market Position
    primary_industry: str = Field(None, description="Primary industry classification")
    industry_verticals: str = Field(None, description="Target industry verticals")
    business_model: str = Field(None, description="Primary business model (B2B, B2C, B2B2C, etc.)")
    target_market: str = Field(None, description="Primary target market description")
    competitive_landscape: str = Field(None, description="Key competitors")
    market_differentiation: str = Field(None, description="Key differentiators from competitors")
    
    # Company Scale & Structure
    
    employee_count: str = Field(None, description="Approximate number of employees")
    office_location: str = Field(None, description="Office locations worldwide")
    # headquarters: Optional[str] = Field(None, description="Primary headquarters location")
    # remote_policy: Optional[str] = Field(None, description="Remote work policy")

    total_funding: str = Field(None, description="Total funding raised")
    latest_funding_round: str = Field(None, description="Latest funding round details")
    revenue_range: str = Field(None, description="Annual revenue range")
    investors: str = Field(None, description="Key investors")
    brand_keywords: str = Field(None, description="Key brand and industry keywords")
    
    
    





class Topic(BaseModel): 
    topic: Optional[str] = Field(None, description="Generated topic for LinkedIn content generation")
    context : Optional[str] = Field(None, description="Context or background information for the topic relevant to the user's profile")
    topic_keywords: Optional[str] = Field(default_factory=list, description="Relevant keywords")
    content_angle: Optional[str] = Field(None, description="Unique perspective/angle")
    


def update_company_info(info: str, tool_context: ToolContext) -> dict:
    """Update the company's personal information whenever the user provides new information about the company
    Even if you feel the slightest new information call this tool

    Args:
        info: The new personal information for the user
        tool_context: Context for accessing and updating session state

    Returns:
        A confirmation message
    """
    print(f"--- Tool: update_company_info called ---")
    old_info = tool_context.state.get("Company_Profile", "")
    new_info = info  
    
   
    llm_with_schema = llm.with_structured_output(CompanyProfile)
    response = llm_with_schema.invoke(Update_memory_prompt.format(
        old_info=old_info, new_info=new_info))
    
    
    # Update the personal information in state
    tool_context.state["Company_Profile"] = response.model_dump()

    return {
        "action": "update_company_info",
        "info": response.model_dump(),
        "message": f"Updated your personal information.",
    }




def generate_topic(tool_context: ToolContext) ->dict :
    """
    Generate a topic for linkedin content generation based on the user's profile

    Args:
        tool_context (ToolContext): _description_

    Returns:
        dict: _description_
    """
    print(f"--- Tool: generate_topic called ---")
    
    # Get the user's profile information from state
    profile = tool_context.state.get("Company_Profile", {})
    
    # Generate a topic based on the profile information
    llm_with_schema = llm.with_structured_output(Topic)
    
    topic = llm_with_schema.invoke(topic_prompt.format(profile=profile))
    tool_context.state["topic"] = topic.model_dump()
    
    return {
        "action": "generate_topic",
        "topic": topic,
        "message": f"Generated topic: {topic}",
    }

def custom_topic(tool_context: ToolContext, topic: str) -> dict:
    """
    Custom topic given by user for linkedin content generation based on the user's profile

    Args:
        tool_context (ToolContext): _description_
        topic (str): _description_

    Returns:
        dict: _description_
    """
    print(f"--- Tool: custom_topic called with '{topic}' ---")
    llm_with_schema = llm.with_structured_output(Topic)
    response = llm_with_schema.invoke(custom_topic_prompt.format(topic=topic))
    
    
    # Update the topic in state
    tool_context.state["topic"] = response.model_dump() 
    
    
    return {
        "action": "custom_topic",
        "topic": response.model_dump(),
        "message": f"Custom topic set to: {topic}",
    }
    
    
# def display_final_content(tool_context: ToolContext) -> dict:
#     """
#     Display the final optimized LinkedIn content after Linkedin_Content_Drafter completes
#     """
#     print(f"--- Tool: display_final_content called ---")
    
#     # Get content from state
#     optimized_content = tool_context.state.get("optimized_content", "")
#     content_draft = tool_context.state.get("content_draft", "")
#     good_articles = tool_context.state.get("good_articles", [])
    
#     if not optimized_content:
#         return {
#             "action": "display_final_content",
#             "message": "❌ No optimized content found. Please run content creation first.",
#             "final_content": ""
#         }
    
#     # Format the final presentation
#     formatted_content = f"""
# ---
# ## 🎯 Final Optimized LinkedIn Post

# {optimized_content}

# ---
# **Content Metrics:**
# - Character count: {len(optimized_content)} characters
# - Articles incorporated: {len(good_articles)} high-quality articles
# - Competitor insights: ✅ Included
# - Viral patterns: ✅ Applied
# - Engagement optimization: ✅ Complete

# **Ready for publication on LinkedIn!** 🚀
# ---
# """
    
#     return {
#         "action": "display_final_content",
#         "message": "✅ Final optimized LinkedIn content ready for publication",
#         "formatted_content": formatted_content,
#         "character_count": len(optimized_content)
#     }
