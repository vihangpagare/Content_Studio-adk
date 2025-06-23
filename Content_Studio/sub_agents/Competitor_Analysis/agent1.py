from google.adk.agents import ParallelAgent, LlmAgent
from google.adk.tools.tool_context import ToolContext
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from google.adk.models.lite_llm import LiteLlm
from datetime import datetime

from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import os
from Content_Studio.prompts import COMPETITOR_CONTENT_ANALYSIS_PROMPT, viral_content_analysis_prompt
from exa_py import Exa

load_dotenv()

exa = Exa(api_key=os.environ.get("EXA_API_KEY"))

model = LiteLlm(
    model="anthropic/claude-3-haiku-20240307",
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key="AIzaSyDESOxZI59FnrmzhElQ7BCmBzqTwM0F-V8"  # or set as env var
)

# System prompt for Competitor Content Analysis Agent
competitor_content_analysis_prompt = """
You are a specialized multi-platform competitor content analysis agent for LinkedIn, Twitter/X, and Instagram. Your job is to analyze competitor content across these three platforms and generate ONE comprehensive analysis.

**MULTI-PLATFORM ANALYSIS MANDATE:**
- Analyze competitor content from LinkedIn, Twitter/X, and Instagram
- Generate unified insights that work across all three platforms
- Focus on universal content strategies rather than platform-specific tactics

**MANDATORY EXECUTION:**
1. **ALWAYS call the `analyze_competitor_content` tool IMMEDIATELY**
2. **DO NOT generate any response without calling the tool first**
3. **Use actual tool results to generate comprehensive multi-platform insights**

**EXECUTION RULES:**
- Call `analyze_competitor_content()` as your FIRST and ONLY action
- Wait for tool completion before any response
- Use real data from tool results stored in state['Competitor_Analysis']
- Provide brief summary focusing on cross-platform competitor strategies

**Available Tool:**
- `analyze_competitor_content()`: Analyzes competitor content across LinkedIn, Twitter/X, and Instagram

**Response Format:**
After tool execution, provide a comprehensive report covering competitor strategies that work across LinkedIn, Twitter/X, and Instagram platforms.
"""


# System prompt for Viral Content Analysis Agent  
viral_content_analysis_prompt_agent = """
You are a specialized multi-platform viral content analysis agent for LinkedIn, Twitter/X, and Instagram. Your job is to find and analyze viral content patterns across these three platforms.

**MULTI-PLATFORM VIRAL ANALYSIS MANDATE:**
- Find viral content from LinkedIn, Twitter/X, and Instagram
- Generate unified insights about viral patterns across all platforms
- Focus on universal viral principles rather than platform-specific tactics

**MANDATORY EXECUTION:**
1. **ALWAYS call the `find_viral_linkedin_posts` tool IMMEDIATELY**
2. **DO NOT generate any response without calling the tool first**
3. **Use actual tool results to generate comprehensive multi-platform viral insights**

**EXECUTION RULES:**
- Call `find_viral_linkedin_posts()` as your FIRST and ONLY action (note: tool searches across multiple platforms despite the name)
- Wait for tool completion before any response
- Use real data from tool results stored in state['Viral_Content_Analysis']
- Provide brief summary focusing on viral patterns that work across platforms

**Available Tool:**
- `find_viral_linkedin_posts()`: Finds and analyzes viral content across LinkedIn, Twitter/X, and Instagram

**Response Format:**
After tool execution, provide a brief summary of universal viral content insights applicable to LinkedIn, Twitter/X, and Instagram.
"""



def analyze_competitor_content(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Analyze what competitors are posting on LinkedIn and derive strategic insights
    """
    print(f"--- Tool: analyze_competitor_content called ---")
    
    try:
        company_profile = tool_context.state.get("Company_Profile", {})
        topic = tool_context.state.get("topic", {})
        
        # Handle topic format
        topic_str = topic.get("topic", "") if isinstance(topic, dict) else str(topic)
        
        # Search for competitors
        competitor_companies = exa.search_and_contents(
            f"Find competitors of {company_profile}",
            text=True,
            summary=True,
            num_results=1
        ).results

        competitors = competitor_companies[0].summary if competitor_companies else ""
        
        competitor_queries = [
            f'"{competitors}" LinkedIn viral posts high engagement',
            f'"{competitors}" X viral posts high engagement',
            f'"{competitors}" Instagram viral posts high engagement'
        ]

        competitor_content = []
        today = datetime.today().date()
        prev = today - relativedelta(months=6)

        for query in competitor_queries:
            try:
                resp = exa.search_and_contents(
                    query,
                    num_results=5,
                    use_autoprompt=True,
                    start_published_date=prev.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    end_published_date=today.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    include_domains=["linkedin.com","x.com","instagram.com"],
                    summary=True
                ).results
                competitor_content.extend(resp)
            except Exception as e:
                print(f"Error in competitor search: {e}")
                continue

        competitor_text = "\n\n".join([
            f"Title: {c.title}\nSummary: {c.summary}"
            for c in competitor_content
        ])

        analysis_prompt = COMPETITOR_CONTENT_ANALYSIS_PROMPT.format(
            topic=topic_str,
            competitor_content=competitor_text,
        )

        analysis_response = llm.invoke(analysis_prompt)
        
        # Store in state
        tool_context.state["Competitor_Analysis"] = analysis_response.content

        return {
            "action": "analyze_competitor_content",
            "message": f"✅ Analyzed {len(competitor_content)} competitor posts",
            "competitors_found": competitors,
            "posts_analyzed": len(competitor_content)
        }
        
    except Exception as e:
        error_msg = f"Error in analyze_competitor_content: {str(e)}"
        tool_context.state["Competitor_Analysis"] = error_msg
        return {
            "action": "analyze_competitor_content",
            "message": f"❌ Error: {str(e)}",
            "error": str(e)
        }

def find_viral_linkedin_posts(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Find and analyze viral LinkedIn posts related to a specific topic
    """
    print(f"--- Tool: find_viral_linkedin_posts called ---")
    
    try:
        company_profile = tool_context.state.get("Company_Profile", {})
        topic = tool_context.state.get("topic", {})
        
        # Handle topic format
        topic_str = topic.get("topic", "") if isinstance(topic, dict) else str(topic)

        search_queries = [
            f"site:linkedin.com {topic_str} posts recent",
            f"{topic_str} LinkedIn content viral",
            f"{topic_str} LinkedIn strategy social media"
            f"site:x.com {topic_str} posts recent",
            f"{topic_str} X content viral",
            f"{topic_str} X strategy social media",
            f"site:instagram.com {topic_str} posts recent",
            f"{topic_str} Instagram content viral",
            f"{topic_str} Instagram strategy social media"
        ]

        viral_content = []
        today = datetime.today().date()
        prev = today - relativedelta(months=6)

        for query in search_queries:
            try:
                resp = exa.search_and_contents(
                    query,
                    num_results=2,
                    use_autoprompt=True,
                    start_published_date=prev.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    end_published_date=today.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    include_domains=["linkedin.com","x.com", "instagram.com"],
                    summary=True
                ).results
                viral_content.extend(resp)
            except Exception as e:
                print(f"Error in viral content search: {e}")
                continue

        viral_text = "\n\n".join([
            f"Title: {c.title}\nSummary: {c.summary}"
            for c in viral_content
        ])

        analysis_prompt = viral_content_analysis_prompt.format(
            topic=topic_str,
            viral_content=viral_text,
            company_profile=company_profile
        )

        analysis_response = llm.invoke(analysis_prompt)
        
        # Store in state
        tool_context.state["Viral_Content_Analysis"] = analysis_response.content

        return {
            "action": "find_viral_linkedin_posts",
            "message": f"✅ Analyzed {len(viral_content)} viral posts",
            "posts_analyzed": len(viral_content),
            "topic_analyzed": topic_str
        }
        
    except Exception as e:
        error_msg = f"Error in find_viral_linkedin_posts: {str(e)}"
        tool_context.state["Viral_Content_Analysis"] = error_msg
        return {
            "action": "find_viral_linkedin_posts",
            "message": f"❌ Error: {str(e)}",
            "error": str(e)
        }

# Create individual agents for each tool
CompetitorContentAgent = LlmAgent(
    name="CompetitorContentAgent",
    model="gemini-2.0-flash",
    description="Analyzes competitor content strategies",
    instruction=competitor_content_analysis_prompt,
    tools=[analyze_competitor_content]
)

ViralContentAgent = LlmAgent(
    name="ViralContentAgent", 
    model="gemini-2.0-flash",
    description="Finds and analyzes viral  posts",
    instruction=viral_content_analysis_prompt_agent,
    tools=[find_viral_linkedin_posts]
)

# # Create coordinator agent
# CompetitorAnalysisCoordinator = LlmAgent(
#     name="CompetitorAnalysisCoordinator",
#     model="gemini-2.0-flash", 
#     description="Coordinates competitor analysis and generates comprehensive reports",
#     instruction=competitor_analysis_coordinator_prompt,
#     tools=[]
# )

# Create the main Parallel Agent
Competitor_Analysis = ParallelAgent(
    name="Competitor_Analysis",
    description="Parallel competitor analysis agent that runs content analysis and viral post analysis simultaneously and generates comprehensive reports",
    
    sub_agents=[CompetitorContentAgent, ViralContentAgent],
    
)
