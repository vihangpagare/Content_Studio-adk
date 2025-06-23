from google import genai
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
# from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters
# from custom_adk_patches import CustomMCPToolset as MCPToolset
load_dotenv()
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
import uuid


genai_client = genai.Client()
llm = AzureChatOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    model="gpt4o",
)

# Enhanced Tweet Creation Prompt
ENHANCED_TWEET_CREATION_PROMPT = """
You are a viral Twitter/X content strategist specializing in high-engagement tweets. Create a compelling, platform-optimized tweet that drives maximum engagement across professional and general audiences.

📌 CONTEXT & INPUTS
• Topic: {topic}
• Company Profile: {user_profile}
• Competitor Insights: {competitor_insights}
• Article Insights: {article_insights}
• Viral Insights: {viral_insights}

🎯 TWITTER/X OPTIMIZATION FRAMEWORK

1. **CHARACTER LIMIT MASTERY (280 characters max)**
   - Every character counts - be ruthlessly concise
   - Use abbreviations strategically (w/, &, etc.)
   - Leverage line breaks for visual impact

2. **HOOK OPTIMIZATION (First 25 characters)**
   - Start with power words: "BREAKING:", "🚨", "REVEALED:"
   - Use numbers: "3 reasons", "In 2024"  
   - Ask provocative questions
   - Create pattern interrupts

3. **ENGAGEMENT TRIGGERS**
   - End with discussion questions
   - Use "Agree or disagree?" 
   - Include "RT if you..."
   - Add "Your thoughts? 👇"

4. **TWITTER-SPECIFIC ELEMENTS**
   - Strategic emoji use (2-3 max)
   - Relevant hashtags (2-3 trending + niche)
   - Mention handles when appropriate (@username)
   - Use threads indicator if needed (1/n)

5. **VIRAL MECHANICS**
   - Controversial but professional takes
   - Counter-narrative insights
   - Industry predictions
   - Personal experience angles

🔥 CONTENT STRUCTURE
Line 1: Hook (compelling opener)
Line 2-3: Core insight/value
Line 4: Call-to-action/question
Line 5: Hashtags

OUTPUT: Single tweet text ready for X/Twitter (under 280 characters)
"""

# Tweet Optimization Prompt
TWEET_OPTIMIZATION_PROMPT = """
You are a Twitter/X engagement optimization expert. Transform the provided tweet into a viral-potential post that maximizes retweets, replies, and engagement.

**Original Tweet**: {content}

**OPTIMIZATION CHECKLIST:**

**1. Character Efficiency**
- Current count: {char_count}/280
- Optimize word choice for maximum impact
- Remove unnecessary words while preserving meaning

**2. Viral Elements**
- Hook strength (first 25 chars)
- Emotional trigger inclusion
- Shareability factor
- Discussion potential

**3. Platform Mechanics**
- Optimal hashtag placement
- Strategic emoji usage
- Line break utilization
- Mention opportunities

**4. Engagement Amplifiers**
- Question integration
- Opinion solicitation  
- Action prompts (RT, reply)
- Community building language

**5. Algorithm Optimization**
- Trending topic alignment
- Peak engagement timing considerations
- Cross-platform adaptation potential

**FINAL INSTRUCTION:**
🚫 HARD LIMIT:
Your final tweet MUST be **under 280 characters**. Return **ONLY** the optimized tweet (no bullet points, no formatting, no explanations). Do NOT exceed the limit.
Return ONLY the optimized tweet text (under 280 characters). No explanations or formatting.
"""

def create_tweet_content(tool_context: ToolContext) -> Dict[str, Any]:
    """Create Twitter/X content incorporating all available insights"""
    print(f"--- Tool: create_tweet_content called ---")
    
    # Get all necessary data from state
    company_profile = tool_context.state.get("Company_Profile", {})
    topic = tool_context.state.get("topic", {})
    competitor_insights = tool_context.state.get("Competitor_Analysis", "")
    viral_insights = tool_context.state.get("Viral_Content_Analysis", "")
    good_articles = tool_context.state.get("good_articles", [])
    
    topic_str = topic.get("topic", "") if isinstance(topic, dict) else str(topic)
    
    if not topic_str:
        return {
            "action": "create_tweet_content",
            "message": "No topic available for tweet creation",
            "tweet_draft": ""
        }
    
    # Prepare article insights
    if good_articles:
        article_insights = "Key insights: " + "; ".join([
            f"{article['title'][:50]}..." for article in good_articles[:2]
        ])
    else:
        article_insights = "Focus on original insights and competitor analysis."
    
    # Create tweet using the enhanced prompt
    tweet_prompt = ENHANCED_TWEET_CREATION_PROMPT.format(
        topic=topic_str,
        user_profile=json.dumps(company_profile, indent=2),
        competitor_insights=competitor_insights,
        article_insights=article_insights,
        viral_insights=viral_insights
    )
    
    tweet_response = llm.invoke(tweet_prompt)
    draft = tweet_response.content.strip()
    
    # Store the draft in state
    tool_context.state["tweet_draft"] = draft
    
    return {
        "action": "create_tweet_content",
        "message": f"Created tweet draft ({len(draft)} chars)",
        "tweet_draft": draft,
        "character_count": len(draft)
    }

def optimize_tweet_content(tool_context: ToolContext) -> Dict[str, Any]:
    """Optimize tweet for maximum engagement"""
    print(f"--- Tool: optimize_tweet_content called ---")
    
    draft = tool_context.state.get("tweet_draft", "")
    if not draft:
        return {
            "action": "optimize_tweet_content",
            "message": "No tweet draft found to optimize",
            "optimized_tweet": ""
        }
    
    # Optimize the tweet
    optimization_prompt = TWEET_OPTIMIZATION_PROMPT.format(
        content=draft,
        char_count=len(draft)
    )
    
    optimized_response = llm.invoke(optimization_prompt)
    optimized_tweet = optimized_response.content.strip()
    
    # Store optimized tweet
    tool_context.state["optimized_tweet"] = optimized_tweet
    
    return {
        "action": "optimize_tweet_content",
        "message": f"Optimized tweet ({len(optimized_tweet)}/280 chars)",
        "optimized_tweet": optimized_tweet,
        "character_count": len(optimized_tweet)
    }

async def display_final_tweet(tool_context: ToolContext) -> Dict[str, Any]:
    """Display final tweet with image information"""
    print(f"--- Tool: display_final_tweet called ---")
    
    optimized_tweet = tool_context.state.get("optimized_tweet", "")
    good_articles = tool_context.state.get("good_articles", [])
    storage_method = tool_context.state.get("image_storage_method", "none")
    
    if not optimized_tweet:
        return {
            "action": "display_final_tweet",
            "message": "❌ No optimized tweet found",
            "final_content": ""
        }
    
    # Handle image information
    image_info = ""
    image_status = "❌ Not generated"
    
    if storage_method == "artifact":
        artifact_filename = tool_context.state.get("generated_image_artifact", "")
        if artifact_filename:
            image_status = "✅ Generated (Artifact Storage)"
            image_info = f"Image Artifact: {artifact_filename}"
    elif storage_method == "local":
        local_path = tool_context.state.get("generated_image_path", "")
        if local_path:
            image_status = "✅ Generated (Local Storage)"
            image_info = f"Image Path: {local_path}"
    
    formatted_content = f"""
🐦 **Final Twitter/X Post Package**

**📝 Optimized Tweet:**
{optimized_tweet}

**📸 Visual Content:**
- Image Status: {image_status}
{image_info}

**📊 Tweet Metrics:**
- Character count: {len(optimized_tweet)}/280
- Articles incorporated: {len(good_articles)}
- Optimization: ✅ Complete

**🚀 Ready for Twitter/X Publication!**
"""
    
    return {
        "action": "display_final_tweet",
        "message": "✅ Final Twitter/X content package ready",
        "formatted_content": formatted_content,
        "character_count": len(optimized_tweet)
    }

# Create individual agents
TweetCreator = LlmAgent(
    name="TweetCreator",
    model="gemini-2.0-flash",
    description="Creates Twitter/X content drafts using comprehensive analysis",
    instruction="""
You are a tweet creation specialist. Your ONLY job is to call the create_tweet_content tool.
CALL THE TOOL ONLY ONCE

1. **DO NOT generate any response without calling the tool first**


""",
    tools=[create_tweet_content]
)

TweetOptimizer = LlmAgent(
    name="TweetOptimizer",
    model="gemini-2.0-flash",
    description="Optimizes tweets for maximum engagement",
    instruction="""
You are a tweet optimization specialist. Your job is to call the optimize_tweet_content tool.

CALL THE TOOL ONLY ONCE 
1. **DO NOT generate any response without calling the tool first**

""",
    tools=[optimize_tweet_content]
)

TweetDisplayer = LlmAgent(
    name="TweetDisplayer",
    model="gemini-2.0-flash",
    description="Displays final tweet content package",
    instruction="""
You are a tweet display specialist. Your job is to call the display_final_tweet tool.

CALL THE TOOL ONLY ONCE
1. **DO NOT generate any response without calling the tool first**

""",
    tools=[display_final_tweet]
)
IMAGE_PROMPT_GENERATION = """
You are an expert visual content strategist specializing in creating precise, directional image generation prompts. Analyze the Twitter tweet content and systematically construct a detailed visual prompt focusing on key directional elements.

**Twitter/X Post Content:**
{optimized_content}

**Company Profile Context:**
{company_profile}

**SYSTEMATIC ANALYSIS FRAMEWORK:**

**Step 1: Content Deconstruction**
- Extract the core message/value proposition
- Identify primary industry/business context
- Determine emotional tone (inspiring, analytical, innovative, etc.)
- Spot key concepts that need visual representation

**Step 2: Visual Strategy Selection**
Choose ONE primary visual approach:
- **Human-Centered**: Professional interactions, workplace scenarios
- **Conceptual**: Abstract representations of ideas, metaphors
- **Product/Service Focus**: Technology, tools, processes in action
- **Industry-Specific**: Relevant professional environments

**Step 3: Directional Element Construction**
Build your prompt using these MANDATORY components in order:

**COMPOSITION & LAYOUT:**
- Specify exact viewpoint (overhead, side view, 3/4 angle, close-up)
- Define focal point placement (center, rule of thirds, foreground/background)
- Describe visual hierarchy (what draws attention first, second, third)

**PRIMARY SUBJECT:**
- Main visual element (specific object, person, concept, data visualization)
- Exact positioning and scale within frame
- Interaction or action being performed

**SUPPORTING ELEMENTS:**
- Secondary visual components that reinforce the message
- Background context that supports but doesn't distract
- Specific details that add credibility and relevance

**TECHNICAL SPECIFICATIONS:**
- Color palette (2-3 primary colors max, specify hex codes when possible)
- Lighting style (soft natural, professional studio, dramatic accent)
- Texture and material specifications (matte, glossy, transparent, metallic)
- Typography style if text is included (sans-serif, modern, minimal)

**PROFESSIONAL CONTEXT:**
- Industry-appropriate setting and props
- Professional dress code and environments
- Technology and tools relevant to the business context

**OUTPUT FORMAT REQUIREMENTS:**
Construct a single, detailed paragraph following this structure:
"Create a [COMPOSITION] showing [PRIMARY SUBJECT] with [SUPPORTING ELEMENTS], featuring [COLOR PALETTE], [LIGHTING STYLE], and [PROFESSIONAL CONTEXT], designed in a [VISUAL STYLE] that emphasizes [KEY MESSAGE]."

**ENHANCED EXAMPLES:**

*For a data-driven post about AI analytics:*
"Create a clean overhead view showing a modern dashboard interface displaying real-time AI analytics charts and metrics, with a professional's hands typing on a sleek laptop keyboard in the foreground, featuring a blue and white color scheme (#2E86C1, #FFFFFF, #F8F9FA), soft natural lighting from the left, and a minimalist office environment with subtle tech elements, designed in a contemporary infographic style that emphasizes data-driven decision making."

*For a leadership post about team collaboration:*
"Create a dynamic 3/4 angle view showing diverse professionals in business casual attire engaged in an active brainstorming session around a glass conference table, with digital sticky notes and strategy diagrams visible on a large wall-mounted screen, featuring warm professional colors (#4A90E2, #F5A623, #FFFFFF), soft diffused lighting creating gentle shadows, and a modern office space with plants and natural elements, designed in a human-centered documentary style that emphasizes collaborative innovation."

**QUALITY CHECKLIST:**
Before finalizing, ensure your prompt includes:
✓ Specific composition angle and framing
✓ Clear primary focal point
✓ Relevant supporting visual elements
✓ Defined color palette (2-3 colors max)
✓ Appropriate lighting direction and quality
✓ Industry-relevant professional context
✓ Visual style that matches content tone
✓ Connection to the core LinkedIn post message

**FINAL INSTRUCTION:**
Generate ONE comprehensive image prompt paragraph that incorporates all directional elements above. Be specific, technical, and focused on creating a professional LinkedIn-appropriate visual that directly supports the post's key message.
"""


def generate_image_prompt(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Generate an image prompt based on the optimized LinkedIn content
    
    Args:
        tool_context: Context for accessing session state
    
    Returns:
        Dictionary with generated image prompt
    """
    print(f"--- Tool: generate_image_prompt called ---")
    
    # Get optimized content and company profile from state
    optimized_tweet= tool_context.state.get("optimized_tweet", "")
    company_profile = tool_context.state.get("Company_Profile", {})
    
    if not optimized_tweet:
        return {
            "action": "generate_image_prompt",
            "message": "No optimized content found for image prompt generation",
            "image_prompt": ""
        }
    
    # Generate image prompt using LLM
    prompt_generation = IMAGE_PROMPT_GENERATION.format(
        optimized_content=optimized_tweet,
        company_profile=company_profile
    )
    
    prompt_response = llm.invoke(prompt_generation)
    X_image_prompt = prompt_response.content.strip()
    
    # Store in state
    tool_context.state["X_image_prompt"] = X_image_prompt
    
    return {
        "action": "generate_image_prompt",
        "message": "Successfully generated image prompt based on optimized content",
        "X_image_prompt": X_image_prompt
    }

async def generate_and_save_image_artifact(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Generate image using Gemini and save as ADK artifact
    
    Args:
        tool_context: Context for accessing session state and artifact service
    
    Returns:
        Dictionary with image generation status and artifact details
    """
    print(f"--- Tool: generate_and_save_image_artifact called ---")
    
    # Get image prompt from state
    X_image_prompt = tool_context.state.get("X_image_prompt", "")
    if not X_image_prompt:
        return {
            "action": "generate_and_save_image_artifact",
            "message": "No image prompt found for image generation", 
            "artifact_filename": ""
        }
    
    try:
        # Generate image using Gemini
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=X_image_prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        # Extract image data from response
        image_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                break
        
        if not image_data:
            return {
                "action": "generate_and_save_image_artifact",
                "message": "No image data found in Gemini response",
                "artifact_filename": ""
            }
        
        # Create artifact filename with timestamp and unique ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        artifact_filename = f"X_post_image_{timestamp}_{unique_id}.png"
        
        # Create artifact Part object
        image_artifact = types.Part.from_bytes(
            data=image_data,
            mime_type="image/png"
        )
        
        # Save as artifact using ADK artifact service
        version = await tool_context.save_artifact(
            filename=artifact_filename,
            artifact=image_artifact
        )
        
        # Store artifact info in state
        tool_context.state["generated_image_artifact"] = artifact_filename
        tool_context.state["image_artifact_version"] = version
        tool_context.state["image_storage_method"] = "artifact"
        
        
        return {
            "action": "generate_and_save_image_artifact",
            "message": f"Successfully generated and saved image artifact: {artifact_filename} (v{version})",
            "artifact_filename": artifact_filename,
            "version": version,
            "size_bytes": len(image_data)
        }
        
    except (ValueError, AttributeError) as e:
            # Artifact service not available - fallback to local storage
            print(f"Artifact service not available: {e}. Falling back to local storage.")
            
            # Create local images directory
            images_dir = "generated_images"
            os.makedirs(images_dir, exist_ok=True)
            local_path = os.path.join(images_dir, artifact_filename)
            
            # Save locally
            image = Image.open(BytesIO(image_data))
            image.save(local_path)
            
            # Store local path info
            tool_context.state["generated_image_path"] = local_path
            tool_context.state["image_filename"] = artifact_filename
            tool_context.state["image_storage_method"] = "local"
            
            return {
                "action": "generate_and_save_image_with_fallback",
                "message": f"✅ Successfully saved image locally: {local_path}",
                "artifact_filename": artifact_filename,
                "local_path": local_path,
                "storage_method": "local"
            }
            
    except Exception as e:
        error_msg = f"Error generating image: {str(e)}"
        print(error_msg)
        return {
            "action": "generate_and_save_image_with_fallback",
            "message": error_msg,
            "error": str(e),
            "artifact_filename": ""
        }

Tweet_ImageGenerator = LlmAgent(
    name="Tweet_ImageGenerator",
    model="gemini-2.0-flash",
    description="Generates visual content for X posts using Gemini image generation",
    instruction="""
You are an image generation specialist for X content. Your job is to:

1. **FIRST**: Call `generate_image_prompt()` to create a detailed image prompt based on the optimized content
2. **SECOND**: Call `generate_and_save_image()` to generate and save the image

**MANDATORY EXECUTION:**
- Always call both tools in sequence
- Wait for each tool completion before proceeding
- Provide brief confirmation after both tools complete

**SUCCESS CRITERIA:**
- Image prompt successfully generated based on content
- Image successfully created and saved with unique ID
- Confirm both steps completed successfully

Execute both tools immediately when activated.
""",
    tools=[generate_image_prompt, generate_and_save_image_artifact]
)

# Tweet_Poster= LlmAgent(
#     name="Tweet_Poster",
#     model="gemini-2.0-flash",
#     description="Posts the final optimized tweet with visual content",
#     instruction="""
# You are a Twitter/X posting specialist responsible for publishing the final optimized tweet.

# **STEP-BY-STEP BEHAVIOR:**

# 1. Ask the user: "✅ Your tweet is ready. Do you want to post it to Twitter/X now?"
#    - Wait for the user's response.
#    - Accept responses like "yes", "sure", "go ahead", or "post it" as confirmation.
#    - Accept "no", "not now", or "cancel" to skip posting.

# 2. If the user says YES:
#    - Call the Twitter MCP server tool to post the tweet.
#    - Confirm back with a message like "🚀 Tweet posted successfully!"

# 3. If the user says NO:
#    - Respond with a simple message: "✅ Tweet creation complete. Post skipped as per your request."

# **RESTRICTIONS:**
# - DO NOT auto-post without asking the user first.
# - DO NOT assume user wants to post unless explicitly confirmed.

# You MUST follow this flow and await confirmation before calling any tool.
# """,
#     tools=[
#         MCPToolset(
#             connection_params=StdioServerParameters(
#                 command="npx",
#                 args=["-y", "@enescinar/twitter-mcp"],
#                 env={"API_KEY": "JY70YvdvsLZ9gvwin861qlQWH",
#                     "API_SECRET_KEY": "tNLMMn5l0W1mf5glIWu4BewhctGbZc5iGCgWURmVHEQPPr6JvE",
#                     "ACCESS_TOKEN": "1697332135898877952-FiiNUkKVKtUPr1wpXEDJ1Iaiv17VGs",
#                     "ACCESS_TOKEN_SECRET": "EAbgB8pEMqYuoR52HnfCo6LABHNvLUD7AdbLhSGdKj8on"},
#             )
#         ),
#     ],
#     )

# Create the main Sequential Agent
X_Tweet_Content_Drafter = SequentialAgent(
    name="X_Tweet_Content_Drafter",
    description="Sequential agent for creating optimized Twitter/X tweets with visual content",
    sub_agents=[TweetCreator, TweetOptimizer, Tweet_ImageGenerator]
)
