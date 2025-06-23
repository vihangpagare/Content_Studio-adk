# Add this to the imports section of your sub_agents/Article_Fetcher/agent.py file
from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext
from langchain_anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from google.adk.models.lite_llm import LiteLlm
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

import os
import json

from exa_py import Exa

load_dotenv()

exa = Exa(api_key=os.environ.get("EXA_API_KEY"))

model = LiteLlm(
    model="anthropic/claude-3-haiku-20240307",
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

from langchain_google_genai import ChatGoogleGenerativeAI
llm  = AzureChatOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    model="gpt4o",
)
# Article Evaluation Prompt
ARTICLE_EVALUATION_PROMPT = """
You are an AI evaluator tasked with assessing the quality of articles for Multi-platform posts. Your goal is to determine if an article is useful/insightful or not, based on its potential to engage a professional audience with valuable insights.

{article}

# Evaluation Criteria:

### Good Articles:
Insightful and Unique: Offer deep insights, unique perspectives, or actionable takeaways that are not widely available elsewhere.
Engaging and Thought-Provoking: Present in-depth analysis, identify trends, or introduce innovative ideas likely to spark meaningful professional discussions.
Professionally Relevant: Address topics of high relevance to a LinkedIn audience, delivering value beyond basic news or announcements.

### Bad Articles:
Purely Informational: Merely report news or announcements without added insights, critical analysis, or actionable takeaways.
Lacks Depth or Originality: Contain generic, surface-level content or redundant information readily available elsewhere.
Low Relevance: Do not contribute significantly to professional networks, discussions, or personal development.

# Instructions for Classification:
Classify the article as either Good or Bad based on the evaluation criteria.
Output Format - Return a json object
Example - {{"evaluation": "good"}}
STRICTLY FOLLOW THIS SCHEMA AND DO NOT RETURN ANYTHING ELSE
"""

article_fetcher_system_prompt = """
You are an expert article research agent specializing in finding and evaluating high-quality articles for multi-platform social media content creation across LinkedIn, Twitter/X, and Instagram.

**MULTI-PLATFORM CONTENT RESEARCH MANDATE:**
- Research articles suitable for LinkedIn (professional insights), Twitter/X (discussion-worthy topics), and Instagram (visually adaptable content)
- Focus on content that can be adapted across all three platforms
- Generate ONE comprehensive analysis rather than platform-specific reports

Your primary responsibilities are:

1. **MULTI-PLATFORM ARTICLE FETCHING**
- Search for articles that work across LinkedIn, Twitter/X, and Instagram
- Find content suitable for professional insights (LinkedIn), real-time discussions (Twitter/X), and visual storytelling (Instagram)
- Ensure articles are recent and relevant to audiences across all three platforms
- Source from authoritative publications that resonate with multi-platform audiences

2. **CROSS-PLATFORM ARTICLE EVALUATION**
- Assess article quality for multi-platform content adaptation
- Evaluate potential for engagement across LinkedIn, Twitter/X, and Instagram
- Filter content based on universal appeal rather than platform-specific criteria
- Identify articles with insights adaptable to professional posts, tweets, and visual content

3. **UNIFIED CONTENT CURATION**
- Curate articles that support content creation across all three platforms
- Organize articles by universal relevance and cross-platform potential
- Provide summaries highlighting adaptability for LinkedIn, Twitter/X, and Instagram
- Recommend articles that align with multi-platform content strategy

**AVAILABLE TOOLS:**

1. `fetch_articles()`
- Searches for articles suitable for LinkedIn, Twitter/X, and Instagram content
- Returns articles with cross-platform adaptation potential

2. `evaluate_articles()`
- Evaluates articles for multi-platform content suitability
- Provides scoring based on universal appeal and adaptability

**OUTPUT FORMAT:**
Provide structured reports that include:
- Summary of articles found with cross-platform potential
- Quality assessment focusing on universal relevance
- Key insights adaptable for LinkedIn, Twitter/X, and Instagram
- Unified recommendations for multi-platform content creation
- Specific articles recommended for cross-platform posts

**EXECUTION WORKFLOW:**
1. Analyze current topic for multi-platform content potential
2. Fetch relevant articles using fetch_articles tool
3. Evaluate article quality for cross-platform adaptation using evaluate_articles tool
4. Provide ONE comprehensive recommendation covering LinkedIn, Twitter/X, and Instagram

Always focus on finding articles that provide value across LinkedIn's professional audience, Twitter/X's discussion-oriented community, and Instagram's visual storytelling format.
"""
def fetch_articles(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Fetch relevant articles for the current topic using Exa API
    
    Args:
        tool_context: Context for accessing session state
        
    Returns:
        Dictionary with fetched articles and status message
    """
    print(f"--- Tool: fetch_articles called ---")
    
    # Get the current topic from state
    topic = tool_context.state.get("topic", {})
    topic_str = topic.get("topic", "") if isinstance(topic, dict) else str(topic)
    
    if not topic_str:
        return {
            "action": "fetch_articles",
            "message": "No topic available for article fetching",
            "articles": []
        }
    
    fetched_articles = []
    today = datetime.today().date()
    prev = today - relativedelta(months=2)
    
    # Create search queries based on the topic
    search_queries = [
        f'"{topic_str}" insights analysis trends',
        f'"{topic_str}" industry news developments',
        f'"{topic_str}" expert opinions research',
        f'"{topic_str}" best practices case studies'
    ]
    
    for query in search_queries:
        try:
            resp = exa.search_and_contents(
                query,
                num_results=5,
                use_autoprompt=True,
                start_published_date=prev.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                end_published_date=today.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                summary=True
            ).results
            fetched_articles.extend(resp)
        except Exception as e:
            print(f"Error fetching articles for query '{query}': {e}")
            continue
    
    # Convert to serializable format
    articles_data = []
    for article in fetched_articles:
        articles_data.append({
            "title": article.title,
            "summary": article.summary,
            "url": article.url,
            "published_date": getattr(article, 'published_date', None)
        })
    
    # Store in state
    tool_context.state["fetched_articles"] = articles_data
    
    return {
        "action": "fetch_articles",
        "message": f"Successfully fetched {len(articles_data)} articles for topic: {topic_str}",
        "articles_count": len(articles_data),
        "articles": articles_data
    }

def evaluate_articles(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Evaluate the quality and relevance of fetched articles
    
    Args:
        tool_context: Context for accessing session state
        
    Returns:
        Dictionary with evaluation results and filtered articles
    """
    print(f"--- Tool: evaluate_articles called ---")
    
    # Get fetched articles from state
    articles_list = tool_context.state.get("fetched_articles", [])
    
    if not articles_list:
        return {
            "action": "evaluate_articles",
            "message": "No articles found to evaluate",
            "evaluated_articles": [],
            "good_articles": []
        }
    
    evaluated_articles = []
    good_articles = []
    
    for article in articles_list:
        # Prepare article snippet for evaluation
        article_snippet = f"Title: {article['title']}\nSummary: {article['summary']}\nURL: {article['url']}"
        
        # Evaluate using LLM
        eval_prompt = ARTICLE_EVALUATION_PROMPT.format(article=article_snippet)
        
        try:
            eval_response = llm.invoke(eval_prompt)
            parsed_response = json.loads(eval_response.content)
            evaluation = parsed_response.get("evaluation", "bad").lower()
        except Exception as e:
            print(f"Error evaluating article: {e}")
            evaluation = "bad"
        
        # Create evaluation entry
        evaluation_entry = {
            "title": article["title"],
            "summary": article["summary"],
            "url": article["url"],
            "published_date": article.get("published_date"),
            "evaluation": evaluation
        }
        
        evaluated_articles.append(evaluation_entry)
        
        # Add to good articles if evaluation is positive
        if evaluation == "good":
            good_articles.append(evaluation_entry)
    
    # Store evaluation results in state
    tool_context.state["evaluated_articles"] = evaluated_articles
    tool_context.state["good_articles"] = good_articles
    
    return {
        "action": "evaluate_articles",
        "message": f"Evaluated {len(evaluated_articles)} articles. Found {len(good_articles)} high-quality articles.",
        "total_evaluated": len(evaluated_articles),
        "good_articles_count": len(good_articles),
        "evaluated_articles": evaluated_articles,
        "good_articles": good_articles
    }

# Create the Article Fetcher sub-agent
Article_Fetcher = LlmAgent(
    name="Article_Fetcher",
    model="gemini-2.0-flash",
    description="An agent that fetches and evaluates articles for LinkedIn content creation",
    instruction=article_fetcher_system_prompt,
    tools=[fetch_articles, evaluate_articles]
)
