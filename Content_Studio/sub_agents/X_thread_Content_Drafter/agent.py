from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

llm = AzureChatOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    model="gpt4o",
)

# Thread Creation Prompt
ENHANCED_THREAD_CREATION_PROMPT = """
You are an expert Twitter/X thread strategist. Create a compelling, high-engagement thread that breaks down complex topics into digestible, viral-worthy segments.

📌 CONTEXT & INPUTS
• Topic: {topic}
• Company Profile: {user_profile}  
• Competitor Insights: {competitor_insights}
• Article Insights: {article_insights}
• Viral Insights: {viral_insights}

🧵 THREAD OPTIMIZATION FRAMEWORK

**1. THREAD STRUCTURE (5-8 tweets optimal)**
   - Hook Tweet (1/n): Grab attention + thread preview
   - Context Tweet (2/n): Set up the problem/opportunity  
   - Main Content (3-6/n): Core insights, examples, data
   - Conclusion Tweet: Summary + CTA
   - Final Tweet: Engagement ask + RT request

**2. INDIVIDUAL TWEET RULES**
   - Each tweet: 240-270 characters (leave room for numbering)
   - Start each with tweet number: "2/n"
   - Maintain flow between tweets
   - End tweets with cliffhangers when possible

**3. ENGAGEMENT MECHANICS**
   - Hook tweet with strong opener
   - Include 1-2 data points per thread
   - Add personal anecdotes/examples
   - Use strategic emoji placement
   - Build to a strong conclusion

**4. THREAD-SPECIFIC ELEMENTS**
   - Clear numbering system (1/7, 2/7, etc.)
   - Logical progression of ideas
   - Strategic line breaks for readability
   - Hashtags only in first and last tweets
   - Mention relevant accounts where appropriate

**5. VIRAL THREAD PATTERNS**
   - "Here's what I learned..."
   - "X things nobody tells you about Y"  
   - "The framework that changed everything"
   - "Why everyone is wrong about X"

🎯 OUTPUT FORMAT

Create exactly 5-7 numbered tweets with ONLY the tweet content:

1/n: [tweet content here]
2/n: [tweet content here]  
3/n: [tweet content here]
...

IMPORTANT: 
- Each tweet should be on a separate line
- Start each line with only the number/total format (1/7, 2/7, etc.)
- No additional formatting, headers, or explanatory text
- Keep each tweet under 270 characters
- Focus only on the actual thread content

"""

# Thread Optimization Prompt
THREAD_OPTIMIZATION_PROMPT = """
You are a Twitter/X thread optimization expert. Enhance the provided thread for maximum viral potential and engagement.

**Original Thread**: {content}

**THREAD OPTIMIZATION CHECKLIST:**

**1. Hook Enhancement**
- First tweet must stop the scroll
- Include compelling statistics or questions
- Add emotional triggers or controversy

**2. Flow Optimization**
- Smooth transitions between tweets
- Logical progression of ideas
- Cliffhangers to encourage reading

**3. Individual Tweet Polish**
- Character count optimization (240-270 each)
- Strategic emoji placement
- Power word integration
- Readability improvements

**4. Engagement Amplification**
- Stronger calls-to-action
- Discussion-provoking questions
- Community-building language
- Strategic hashtag placement

**5. Thread Mechanics**
- Consistent numbering format
- Clear thread indicators
- Optimal thread length (5-7 tweets)
- Strong conclusion and RT ask

**FINAL INSTRUCTION:**
🎯 OUTPUT FORMAT

Create exactly 5-7 numbered tweets with ONLY the tweet content:

1/n: [tweet content here]
2/n: [tweet content here]  
3/n: [tweet content here]
...

IMPORTANT: 
- Each tweet should be on a separate line
- Start each line with only the number/total format (1/7, 2/7, etc.)
- No additional formatting, headers, or explanatory text
- Keep each tweet under 270 characters
- Focus only on the actual thread content

"""

def create_thread_content(tool_context: ToolContext) -> Dict[str, Any]:
    """Create Twitter/X thread content"""
    print(f"--- Tool: create_thread_content called ---")
    
    # Get all necessary data from state
    company_profile = tool_context.state.get("Company_Profile", {})
    topic = tool_context.state.get("topic", {})
    competitor_insights = tool_context.state.get("Competitor_Analysis", "")
    viral_insights = tool_context.state.get("Viral_Content_Analysis", "")
    good_articles = tool_context.state.get("good_articles", [])
    
    topic_str = topic.get("topic", "") if isinstance(topic, dict) else str(topic)
    
    if not topic_str:
        return {
            "action": "create_thread_content",
            "message": "No topic available for thread creation",
            "thread_draft": ""
        }
    
    # Prepare article insights
    if good_articles:
        article_insights = "Key insights from articles:\n" + "\n".join([
            f"• {article['title']}: {article['summary'][:100]}..."
            for article in good_articles[:3]
        ])
    else:
        article_insights = "Focus on original insights and competitor analysis."
    
    # Create thread using the enhanced prompt
    thread_prompt = ENHANCED_THREAD_CREATION_PROMPT.format(
        topic=topic_str,
        user_profile=json.dumps(company_profile, indent=2),
        competitor_insights=competitor_insights,
        article_insights=article_insights,
        viral_insights=viral_insights
    )
    
    thread_response = llm.invoke(thread_prompt)
    draft = thread_response.content.strip()
    
    # Store the draft in state
    tool_context.state["thread_draft"] = draft
    
    # Count individual tweets in thread
    tweet_count = len([line for line in draft.split('\n') if line.strip() and ('/' in line and line.strip().split('/')[0].strip().isdigit())])
    
    return {
        "action": "create_thread_content",
        "message": f"Created thread draft with {tweet_count} tweets",
        "thread_draft": draft,
        "tweet_count": tweet_count
    }

def optimize_thread_content(tool_context: ToolContext) -> Dict[str, Any]:
    """Optimize thread for maximum engagement"""
    print(f"--- Tool: optimize_thread_content called ---")
    
    draft = tool_context.state.get("thread_draft", "")
    if not draft:
        return {
            "action": "optimize_thread_content",
            "message": "No thread draft found to optimize",
            "optimized_thread": ""
        }
    
    # Optimize the thread
    optimization_prompt = THREAD_OPTIMIZATION_PROMPT.format(content=draft)
    
    optimized_response = llm.invoke(optimization_prompt)
    optimized_thread = optimized_response.content.strip()
    
    # Store optimized thread
    tool_context.state["optimized_thread"] = optimized_thread
    
    # Count tweets in optimized thread
    tweet_count = len([line for line in optimized_thread.split('\n') if line.strip() and ('/' in line and line.strip().split('/')[0].strip().isdigit())])
    
    return {
        "action": "optimize_thread_content",
        "message": f"Optimized thread with {tweet_count} tweets",
        "optimized_thread": optimized_thread,
        "tweet_count": tweet_count
    }

async def display_final_thread(tool_context: ToolContext) -> Dict[str, Any]:
    """Display final thread with clean formatting for posting agent"""
    print(f"--- Tool: display_final_thread called ---")
    
    optimized_thread = tool_context.state.get("optimized_thread", "")
    good_articles = tool_context.state.get("good_articles", [])
    
    if not optimized_thread:
        return {
            "action": "display_final_thread",
            "message": "❌ No optimized thread found",
            "final_content": ""
        }

    # Clean thread processing - extract only numbered tweets
    thread_lines = [line.strip() for line in optimized_thread.split('\n') if line.strip()]
    clean_tweets = []
    
    for line in thread_lines:
        # Only include lines that start with tweet numbers (1/n, 2/n, etc.)
        if '/' in line and line.split('/')[0].strip().replace('.', '').isdigit():
            clean_tweets.append(line.strip())
    
    # Create clean thread with separators
    clean_thread = "\n---TWEET-SEPARATOR---\n".join(clean_tweets)
    
    # Store clean thread for posting agent
    tool_context.state["clean_thread_for_posting"] = clean_thread
    
    # Display with metrics but clean thread content
    formatted_content = f"""
🧵 **Twitter/X Thread Ready**

{clean_thread}

📊 **Metrics:** {len(clean_tweets)} tweets | {len(good_articles)} articles incorporated
🚀 **Ready for posting!**
    """
    
    return {
        "action": "display_final_thread",
        "message": "✅ Clean thread ready for posting",
        "formatted_content": formatted_content,
        "tweet_count": len(clean_tweets),
        "clean_thread": clean_thread
    }

# Create individual agents
ThreadCreator = LlmAgent(
    name="ThreadCreator", 
    model="gemini-2.0-flash",
    description="Creates Twitter/X thread drafts using comprehensive analysis",
    instruction="""
You are a thread creation specialist. Your ONLY job is to call the create_thread_content tool.

**MANDATORY EXECUTION:**
1. ** call `create_thread_content()` tool **
2. **DO NOT generate any response without calling the tool first**

""",
    tools=[create_thread_content]
)

ThreadOptimizer = LlmAgent(
    name="ThreadOptimizer",
    model="gemini-2.0-flash", 
    description="Optimizes threads for maximum engagement",
    instruction="""
You are a thread optimization specialist. Your job is to call the optimize_thread_content tool.

**MANDATORY EXECUTION:**
1. ** call `optimize_thread_content()` tool **
2. **DO NOT generate any response without calling the tool first**


""",
    tools=[optimize_thread_content]
)

ThreadDisplayer = LlmAgent(
    name="ThreadDisplayer",
    model="gemini-2.0-flash",
    description="Displays final thread content package",
    instruction="""
You are a thread display specialist. Your job is to call the display_final_thread tool.

**MANDATORY EXECUTION:**
1. ** call `display_final_thread()` tool **  
2. **DO NOT generate any response without calling the tool first**


""",
    tools=[display_final_thread]
)

# Import ImageGenerator from existing implementation


# Create the main Sequential Agent  
X_Thread_Content_Drafter = SequentialAgent(
    name="X_Thread_Content_Drafter",
    description="Sequential agent for creating optimized Twitter/X threads with visual content",
    sub_agents=[ThreadCreator, ThreadOptimizer, ThreadDisplayer]
)
