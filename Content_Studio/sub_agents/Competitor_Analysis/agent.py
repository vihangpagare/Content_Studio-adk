from google.adk.agents import ParallelAgent,Agent,LlmAgent
from google.adk.tools.tool_context import ToolContext
from langchain_anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field
from typing import List, Optional,Dict,Any
from google.adk.models.lite_llm import LiteLlm
from datetime import datetime

from dateutil.relativedelta import relativedelta

from enum import Enum

from dotenv import load_dotenv
load_dotenv()
import os 

from Content_Studio.prompts import COMPETITOR_CONTENT_ANALYSIS_PROMPT,viral_content_analysis_prompt

from exa_py import Exa
exa= Exa(api_key=os.environ.get("EXA_API_KEY"))




    
    
    
model = LiteLlm(
    model="anthropic/claude-3-haiku-20240307",  # or latest anthopic model
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)





from langchain_google_genai import ChatGoogleGenerativeAI
llm  = AzureChatOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    model="gpt4o",
)
competitor_analysis_system_prompt = """
You are an expert LinkedIn competitor analysis agent specializing in social media competitive intelligence and viral content analysis.

**MANDATORY EXECUTION WORKFLOW:**
1. **FIRST**: Always call `analyze_competitor_content()` tool to analyze competitor strategies
2. **SECOND**:Only after analyze_competitor_content() is completed call `find_viral_linkedin_posts()` tool to analyze viral content patterns  
3. **THIRD**: Generate comprehensive report using the results from both tools

**IMPORTANT EXECUTION RULES:**
- **ALWAYS execute both tools in sequence** before generating any analysis
- **DO NOT generate reports without calling tools first**
- **ACCESS tool results from state variables**: `Competitor_Analysis` and `Viral_Content_Analysis`
- **INCORPORATE actual tool outputs** into your final comprehensive report
- If tools fail, mention the failure and provide general recommendations

**AVAILABLE TOOLS:**

1. `analyze_competitor_content()`
   - Use this to analyze competitor LinkedIn content strategy
   - Results stored in state['Competitor_Analysis']
   - Must be called FIRST

2. `find_viral_linkedin_posts()`  
   - Use this to find and analyze viral posts on specific topics
   - Results stored in state['Viral_Content_Analysis']
   - Must be called SECOND after the completion of `analyze_competitor_content()`

**AFTER CALLING BOTH TOOLS:**

- After successfully completing both tool calls **immediately transfer back to Content_Studio**
- If the user request is **not** about competitor analysis, do **not** call any tools. Just transfer back to the Content_Studio.

Always provide actionable insights based on actual tool outputs, not template responses.
"""



def analyze_competitor_content(tool_context: ToolContext) :
    """
    Analyze what competitors are posting on LinkedIn and derive strategic insights

    Args:
        tool_context: Context for accessing and updating session state
    Returns:
        Comprehensive analysis of competitor's LinkedIn content strategy
    """
    
    company_profile = tool_context.state.get("Company_Profile")
    
    competitor_companies = exa.search_and_contents(
            f"Find competitors of {company_profile}",
            text = True,
            summary = True,
            num_results = 1
   ).results
    
    competitors = competitor_companies[0].summary  if competitor_companies else ""
    
    
    competitor_queries = [
        f'"{competitors}" LinkedIn viral posts high engagement',
        
    ]
    
    competitor_content = []
    today = datetime.today().date()
    prev = today - relativedelta(months=6)

    for query in competitor_queries:
        try:
            resp = exa.search_and_contents(
                query,
                num_results=8,
                use_autoprompt=True,
                start_published_date=prev.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                end_published_date=today.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                include_domains=["linkedin.com"],
                summary=True
            ).results
            competitor_content.extend(resp)
        except Exception:
            continue

    competitor_text = "\n\n".join([
        f"Title: {c.title}\nSummary: {c.summary}"
        for c in competitor_content
    ])
    
    
    
    analysis_prompt = COMPETITOR_CONTENT_ANALYSIS_PROMPT.format(
        topic=tool_context.state.get("topic"),
        competitor_content=competitor_text,
        
    )
    
    analysis_response = llm.invoke(analysis_prompt)
    tool_context.state["Competitor_Analysis"] = analysis_response.content 
    return {
        "action": "analyze_competitor_content",
        "message": "✅ Step 1/2 Complete: Analyzed competitor content strategies",
        "analysis": analysis_response.content,
        "next_step": "Proceeding to viral content analysis"
    }


def find_viral_linkedin_posts(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Find and analyze viral LinkedIn posts related to a specific topic

    Args:
        tool_context: Context for accessing session state

    Returns:
        Analysis of viral posts and what makes them successful
    """
    print(f"--- Tool: find_viral_linkedin_posts called for topic:---")
    company_profile = tool_context.state.get("Company_Profile", {})
    
    topic = tool_context.state.get("topic", "")
    
    search_queries = [
            f"site:linkedin.com {topic} posts recent",
            f"{topic} LinkedIn content viral",
            f"{topic} LinkedIn strategy social media"
        ]

    viral_content = []
    today = datetime.today().date()
    prev = today - relativedelta(months=6)

    for query in search_queries:
        
        resp = exa.search_and_contents(
                query,
                num_results=2,
                use_autoprompt=True,
                start_published_date=prev.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                end_published_date=today.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                include_domains=["linkedin.com"],
                summary=True
            ).results
        # Use Exa's neural search for better semantic understanding
        
        viral_content.extend(resp)
    viral_text = "\n\n".join([
        f"Title: {c.title}\nSummary: {c.summary}"
        for c in viral_content
    ])
    
    
    
    analysis_prompt = viral_content_analysis_prompt.format(
        topic=topic,
        viral_content=viral_text,
        company_profile=company_profile
    )
    analysis_response = llm.invoke(analysis_prompt)
    tool_context.state["Viral_Content_Analysis"] = analysis_response.content
    
    return {
        "action": "find_viral_linkedin_posts",
        "message": "✅ Step 2/2 Complete: Analyzed viral LinkedIn content patterns", 
        "analysis_summary": analysis_response.content,
        "final_status": "Both analyses complete - ready to generate comprehensive report"
    }
    

    
    
        
        
    
        
    
                         
     
                    












Competitor_Analysis = Agent(
    name="Competitor_Analysis",
    model="gemini-2.0-flash",
    description="An agent that does competitor analysis of the given company",
    instruction = competitor_analysis_system_prompt,
    tools = [analyze_competitor_content,find_viral_linkedin_posts]
    
    
)



# fetch_articles = LlmAgent(
#     name="fetch_articles",
#     model="gemini-2.0-flash",
#     description="An agent that fetches articles on the given topic ",
#     instruction = "You should output just one line article fetching done",
    
    
# )