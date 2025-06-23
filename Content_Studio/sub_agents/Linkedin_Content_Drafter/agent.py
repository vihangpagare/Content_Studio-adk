from google.adk.agents import LlmAgent,Agent,SequentialAgent
from google.adk.tools.tool_context import ToolContext
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from google.adk.models.lite_llm import LiteLlm
from datetime import datetime
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os
from PIL import Image
from io import BytesIO
import json
from Content_Studio.sub_agents.Linkedin_Content_Drafter.image_content import ImageGenerator
load_dotenv()

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
ENHANCED_CONTENT_CREATION_PROMPT = """
You are a professional, strategic LinkedIn content creator. Your mission is to craft a scroll-stopping, high-engagement post that reflects the user's voice, expertise, and unique insights—while leveraging competitor intelligence and vetted article data. The final output should feel authentic, actionable, and distinctly valuable to a professional, technically fluent LinkedIn audience.

————————————
📌 CONTEXT & INPUTS
————————————
• Topic: {topic}
• User Profile: {user_profile}
• Competitor Insights: {competitor_insights}
• Article Insights: {article_insights}
• Viral  Insights: {viral_insights}

————————————
🎯 PRIMARY OBJECTIVE
————————————
1. SYNTHESIZE competitor and article insights into a cohesive narrative.
2. DIFFERENTIATE the user's post by injecting personal POV, practical anecdotes, and actionable guidance.
3. DELIVER a professional yet approachable tone (no jargon-overload, no buzzwords).
4. DRIVE meaningful engagement (comments, shares, saves) with an authentic CTA.

————————————
🧠 STRUCTURE & CONTENT GUIDELINES
————————————
1. **HOOK (First 2 Lines)**
   – Begin with a striking statistic, question, or bold statement derived from "Article Insights."
   – Tie it immediately to a real challenge or opportunity in the industry or professional context.
   – Avoid generic openers (e.g., "In today's world…").

2. **TENSION or "WHY NOW?" (Next 2–3 Lines)**
   – Explain what makes this topic urgent: new regulation, high-impact research, competitor gap, or industry event.
   – Cite one precise stat or trend (paraphrased) from Article Insights to reinforce urgency.

3. **COMPETITOR CONTRAST & GAP (Next 2–3 Lines)**
   – Reference a key insight from "Competitor Insights" (e.g., their most engaging format or angle).
   – Point out a gap or missed angle that the user can fill.
   – Keep this contrast concise—focus on real differentiation.

4. **USER'S UNIQUE INSIGHT + STORY (3–4 Sentences)**
   – Share a specific example from the user's work.
   – Explain how the user's experience validates, challenges, or expands upon the Article Insights.
   – Use concrete details.

5. **ACTIONABLE VALUE & TAKEAWAY (2–3 Bullet Points or Numbered List)**
   – Provide 2–3 clear, actionable recommendations or mindset shifts.
   – Each bullet should be concise, practical, and tied back to the user's domain.
   – Use parallel structure (e.g., all begin with a verb: "Audit…," "Document…," "Advocate…").

6. **ENGAGEMENT & CALL-TO-ACTION (Final 1–2 Lines)**
   – Pose an open-ended question that invites peers to share their experiences or disagree.
   – Alternatively, issue a challenge or ask for a specific example from readers.
   – Encourage at least one concrete action (comment, share a resource, tag a colleague).

————————————
📐 FORMATTING & TONE
————————————
• **Length**: Under 3000 characters (approximately 350–400 words).
• **Paragraphs**: 2–3 sentences max per paragraph; use line breaks liberally.
• **Lists**: Use a bullet (•) or numbered list for "Actionable Value" section.
• **Language**:
  – Professional but approachable—write as if explaining to a respected peer over coffee.
  – Avoid vague terms ("very important," "nice to have"). Be precise ("X% improvement in performance").
  – Use first person sparingly to establish authenticity (e.g., "In my experience…").
• **Credibility**: Reference statistics/trends with brief context (e.g., "According to a 2025 survey by XYZ, 68% of teams…"). Paraphrase, don't copy.
• **Hashtags**: Include 2–3 niche, high-value hashtags at the end. Avoid overly generic tags (#tech, #business).

🎯 FINAL OUTPUT
————————————
Produce the fully formatted LinkedIn post as described—ready for copy-paste into the LinkedIn composer. Do not include any commentary or extra explanation. Only output the post text itself.
"""

CONTENT_OPTIMIZATION_PROMPT = """
You are a viral LinkedIn content optimization expert. Transform the provided content into a high-performing LinkedIn post that maximizes engagement and professional value.

**Original Content**: {content}  
**Target Audience**: Professional network, industry peers, potential connections  
**Optimization Goal**: Maximize comments, shares, and professional engagement  

**OPTIMIZATION FRAMEWORK**:

**1. HOOK OPTIMIZATION (First 2 lines)**  
- Start with compelling statistic, question, or bold statement  
- Use power words: "Discover", "Revealed", "Shocking", "Secret"  
- Create curiosity gap or pattern interrupt  
- Test: Would you stop scrolling for this?

**2. STRUCTURE OPTIMIZATION**  
- Line 1-2: Hook (attention grabber)  
- Line 3-5: Context/problem statement  
- Line 6-10: Main insight/solution/story  
- Line 11-12: Key takeaway/lesson  
- Line 13-15: Call-to-action question  

**3. ENGAGEMENT TRIGGERS**  
- Include 2-3 discussion-worthy questions  
- Add controversial but professional viewpoints  
- Include personal experience or vulnerability  
- Use "agree or disagree?" type prompts  
- Add industry-specific insights  

**4. VISUAL FORMATTING**  
- Use line breaks for readability (mobile-optimized)  
- Add relevant emojis (2-4 maximum)  
- **Bold** key points with **text**  
- Use bullet points or numbered lists when appropriate  
- Keep paragraphs to 2-3 lines maximum  

**5. HASHTAG STRATEGY**  
- Include 3-5 relevant hashtags  
- Mix trending and niche hashtags  
- Place hashtags at the end  
- Research current hashtag performance  

**6. CTA OPTIMIZATION**  
- End with specific, actionable question  
- Use "Share your experience" or "What's your take?"  
- Encourage tagging: "Tag someone who needs to see this"  
- Create urgency or exclusivity where appropriate  

**LINKEDIN-SPECIFIC REQUIREMENTS**:  
- Maximum 3,000 characters  
- Professional yet conversational tone  
- Industry credibility and authority  
- Shareable insights and takeaways  
- Connection-building language  

**FINAL INSTRUCTION**:  
ONLY return the **OPTIMIZED LINKEDIN POST - EXACTLY AS IT SHOULD APPEAR ON LINKEDIN**.  
**DO NOT include explanations, headers, formatting comments, or anything else. Output only the final post.**
"""


def create_content(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Create LinkedIn content incorporating company profile, topic, competitor insights, and article research
    
    Args:
        tool_context: Context for accessing session state
        
    Returns:
        Dictionary with created content draft and status message
    """
    print(f"--- Tool: create_content called ---")
    
    # Get all necessary data from state
    company_profile = tool_context.state.get("Company_Profile", {})
    topic = tool_context.state.get("topic", {})
    competitor_insights = tool_context.state.get("Competitor_Analysis", "")
    viral_insights = tool_context.state.get("Viral_Content_Analysis", "")
    good_articles = tool_context.state.get("good_articles", [])
    
    # Handle topic format (could be dict or string)
    topic_str = topic.get("topic", "") if isinstance(topic, dict) else str(topic)
    
    if not topic_str:
        return {
            "action": "create_content",
            "message": "No topic available for content creation",
            "content_draft": ""
        }
    
    # Prepare article insights
    if good_articles:
        article_insights = "Key insights from quality articles:\n"
        for i, article in enumerate(good_articles[:3], 1):
            article_insights += f"{i}. {article['title']}: {article['summary']}...\n"
    else:
        article_insights = "No high-quality articles found. Focus on original insights and competitor analysis."
    
    # Create content using the enhanced prompt
    content_prompt = ENHANCED_CONTENT_CREATION_PROMPT.format(
        topic=topic_str,
        user_profile=json.dumps(company_profile, indent=2),
        competitor_insights=competitor_insights,
        article_insights=article_insights,
        viral_insights= viral_insights
    )
    
    content_response = llm.invoke(content_prompt)
    draft = content_response.content.strip()
    
    # Store the draft in state
    tool_context.state["content_draft"] = draft
    
    return {
        "action": "create_content",
        "message": f"Created LinkedIn content draft incorporating {len(good_articles)} quality articles and competitor insights",
        "content_draft": draft,
        "articles_used": len(good_articles)
    }

def optimize_content(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Optimize existing content draft for maximum LinkedIn engagement
    
    Args:
        tool_context: Context for accessing session state
        
    Returns:
        Dictionary with optimized content and status message
    """
    print(f"--- Tool: optimize_content called ---")
    
    # Get the content draft from state
    draft = tool_context.state.get("content_draft", "")
    
    if not draft:
        return {
            "action": "optimize_content",
            "message": "No content draft found to optimize",
            "optimized_content": ""
        }
    
    # Optimize the content using the optimization prompt
    optimization_prompt = CONTENT_OPTIMIZATION_PROMPT.format(content=draft)
    optimized_response = llm.invoke(optimization_prompt)
    optimized_content = optimized_response.content.strip()
    
    # Store the optimized content in state
    tool_context.state["optimized_content"] = optimized_content
    
    return {
        "action": "optimize_content",
        "message": "Successfully optimized LinkedIn content for maximum engagement",
        "optimized_content": optimized_content,
        "original_length": len(draft),
        "optimized_length": len(optimized_content)
    }

# Create the LinkedIn Content Drafter sub-agent

# Create separate agents for each tool
ContentCreator = LlmAgent(
    name="ContentCreator",
    model="gemini-2.0-flash",
    description="Creates LinkedIn content drafts using comprehensive data analysis",
    instruction="""
You are a content creation specialist. Your ONLY job is to call the create_content tool.

**MANDATORY EXECUTION:**
1. **ALWAYS call `create_content()` tool IMMEDIATELY**
2. **DO NOT generate any response without calling the tool first**
3. **DO NOT provide explanations or conversation**

**SUCCESS CRITERIA:**
- Call the tool as your FIRST and ONLY action
- Wait for tool completion before any response
- Provide brief confirmation of content creation

Call the tool immediately when activated.
""",
    tools=[create_content]
)

ContentOptimizer = LlmAgent(
    name="ContentOptimizer", 
    model="gemini-2.0-flash",
    description="Optimizes LinkedIn content for maximum engagement and viral potential",
    instruction="""
You are a content optimization specialist. Your  job is to call the optimize_content tool.

**MANDATORY EXECUTION:**
1. **ALWAYS call `optimize_content()` tool IMMEDIATELY**
2. **DO NOT generate any response without calling the tool first**
3. **DO NOT provide explanations or conversation**

**SUCCESS CRITERIA:**
- Call the tool as your FIRST and ONLY action
- Wait for tool completion before any response
- Provide brief confirmation of content optimization

Call the tool immediately when activated.
""",
    tools=[optimize_content]
)

# def display_final_content(tool_context: ToolContext) -> Dict[str, Any]:
#     """
#     Display the final optimized LinkedIn content with generated image information
    
#     Args:
#         tool_context: Context for accessing session state
    
#     Returns:
#         Dictionary with formatted final content including image details
#     """
#     print(f"--- Tool: display_final_content called ---")
    
#     # Get all content from state
#     optimized_content = tool_context.state.get("optimized_content", "")
#     #content_draft = tool_context.state.get("content_draft", "")
#     good_articles = tool_context.state.get("good_articles", [])
#     image_path = tool_context.state.get("generated_image_path", "")
#     image_filename = tool_context.state.get("image_filename", "")
#     image_prompt = tool_context.state.get("image_prompt", "")
    
#     if not optimized_content:
#         return {
#             "action": "display_final_content",
#             "message": "❌ No optimized content found. Please run content creation first.",
#             "final_content": ""
#         }
    
#     # Check if image was generated
#     image_status = "✅ Generated" if image_path else "❌ Not generated"
    
#     # Format the final presentation
#     formatted_content = f"""
# 🎯 **Final Optimized LinkedIn Post**

# {optimized_content}

# 📸 **Generated Visual Content**
# - Image Status: {image_status}
# - Image File: {image_filename if image_filename else 'No image generated'}
# - Location: {image_path if image_path else 'N/A'}
# - Image Prompt: {image_prompt if image_prompt else 'N/A'}

# ---

# **Content Metrics:**
# - Character count: {len(optimized_content)} characters
# - Articles incorporated: {len(good_articles)} high-quality articles
# - Competitor insights: ✅ Included
# - Viral patterns: ✅ Applied
# - Engagement optimization: ✅ Complete
# - Visual content: {image_status}

# **Ready for publication on LinkedIn!** 🚀

# **Publishing Checklist:**
# 1. ✅ Copy the text content above
# 2. {'✅ Upload the generated image from: ' + image_path if image_path else '❌ No image to upload'}
# 3. ✅ Add any additional hashtags if needed
# 4. ✅ Schedule or publish immediately

# ---
# """

#     # Try to display image if available (for development/testing)
#     if image_path and os.path.exists(image_path):
#         try:
#             from PIL import Image
#             image = Image.open(image_path)
#             # You could save a thumbnail or show basic image info
#             image_info = f"Image dimensions: {image.size[0]}x{image.size[1]} pixels"
#             formatted_content += f"\n**Image Details:** {image_info}\n"
#         except Exception as e:
#             formatted_content += f"\n**Image Error:** Could not load image - {str(e)}\n"
    
#     return {
#         "action": "display_final_content",
#         "message": "✅ Final optimized LinkedIn content with image ready for publication",
#         "formatted_content": formatted_content,
#         "character_count": len(optimized_content),
#         "image_path": image_path,
#         "image_filename": image_filename,
#         "has_image": bool(image_path)
#     }

# def display_final_content(tool_context: ToolContext) -> Dict[str, Any]:
#     """
#     Display the final optimized LinkedIn content with generated image artifact
    
#     Args:
#         tool_context: Context for accessing session state and artifacts
    
#     Returns:
#         Dictionary with formatted final content including image artifact details
#     """
#     print(f"--- Tool: display_final_content called ---")
    
#     # Get all content from state
#     optimized_content = tool_context.state.get("optimized_content", "")
#     content_draft = tool_context.state.get("content_draft", "")
#     good_articles = tool_context.state.get("good_articles", [])
#     image_artifact_filename = tool_context.state.get("generated_image_artifact", "")
#     image_prompt = tool_context.state.get("image_prompt", "")
    
#     if not optimized_content:
#         return {
#             "action": "display_final_content",
#             "message": "❌ No optimized content found. Please run content creation first.",
#             "final_content": ""
#         }
    
#     # Load and display image artifact if available
#     image_info = ""
#     image_status = "❌ Not generated"
    
#     if image_artifact_filename:
#         try:
#             # Load the image artifact
#             image_artifact = tool_context.load_artifact(filename=image_artifact_filename)
            
#             if image_artifact and image_artifact.inline_data:
#                 # Get image details
#                 image_data = image_artifact.inline_data.data
#                 image_size = len(image_data)
                
#                 # Try to get image dimensions
#                 try:
#                     image = Image.open(BytesIO(image_data))
#                     dimensions = f"{image.size[0]}x{image.size[1]} pixels"
#                 except:
#                     dimensions = "Unknown dimensions"
                
#                 image_status = "✅ Generated and loaded from artifact"
#                 image_info = f"""
# **Image Artifact Details:**
# - Artifact Name: {image_artifact_filename}
# - File Size: {image_size:,} bytes
# - Dimensions: {dimensions}
# - MIME Type: {image_artifact.inline_data.mime_type}
# - Status: Ready for LinkedIn upload

# **Image Prompt Used:**
# {image_prompt}

# **Access Instructions:**
# The image is stored as an ADK artifact and can be accessed programmatically or downloaded for manual upload to LinkedIn.
# """
#             else:
#                 image_status = "❌ Artifact found but no image data"
                
#         except Exception as e:
#             image_status = f"❌ Error loading artifact: {str(e)}"
    
#     # Format the final presentation
#     formatted_content = f"""
# 🎯 **Final LinkedIn Post Package**

# **📝 Optimized LinkedIn Post:**
# {optimized_content}

# **📸 Generated Visual Content:**
# - Image Status: {image_status}
# - Artifact File: {image_artifact_filename if image_artifact_filename else 'No image generated'}

# {image_info}

# ---

# **📊 Content Metrics:**
# - Character count: {len(optimized_content)} characters
# - Articles incorporated: {len(good_articles)} high-quality articles
# - Competitor insights: ✅ Included
# - Viral patterns: ✅ Applied
# - Engagement optimization: ✅ Complete
# - Visual content: {image_status}

# **🚀 Ready for LinkedIn Publication!**

# **📋 Publishing Checklist:**
# 1. ✅ Copy the optimized post text above
# 2. {'✅ Load and upload the image artifact: ' + image_artifact_filename if image_artifact_filename else '❌ No image to upload'}
# 3. ✅ Add any additional hashtags if needed
# 4. ✅ Schedule or publish immediately

# ---
# """

#     return {
#         "action": "display_final_content",
#         "message": "✅ Final LinkedIn content package ready with artifact-based image",
#         "formatted_content": formatted_content,
#         "character_count": len(optimized_content),
#         "image_artifact": image_artifact_filename,
#         "has_image": bool(image_artifact_filename)
#     }

async def display_final_content(tool_context: ToolContext) -> Dict[str, Any]:
    """Display final content with support for both artifact and local storage"""
    print(f"--- Tool: display_final_content called ---")
    
    optimized_content = tool_context.state.get("optimized_content", "")
    good_articles = tool_context.state.get("good_articles", [])
    storage_method = tool_context.state.get("image_storage_method", "none")
    
    if not optimized_content:
        return {
            "action": "display_final_content",
            "message": "❌ No optimized content found",
            "final_content": ""
        }
    
    # Handle different storage methods
    image_info = ""
    image_status = "❌ Not generated"
    
    if storage_method == "artifact":
        # Handle artifact storage
        artifact_filename = tool_context.state.get("generated_image_artifact", "")
        if artifact_filename:
            try:
                image_artifact = await tool_context.load_artifact(filename=artifact_filename)
                if image_artifact and image_artifact.inline_data:
                    image_size = len(image_artifact.inline_data.data)
                    image_status = "✅ Generated (Artifact Storage)"
                    image_info = f"""
**Image Artifact Details:**
- Artifact Name: {artifact_filename}
- Storage: ADK Artifact Service
- File Size: {image_size:,} bytes
- Status: Ready for LinkedIn upload
"""
            except Exception as e:
                image_status = f"❌ Error loading artifact: {str(e)}"
    
    elif storage_method == "local":
        # Handle local storage
        local_path = tool_context.state.get("generated_image_path", "")
        filename = tool_context.state.get("image_filename", "")
        if local_path and os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            image_status = "✅ Generated (Local Storage)"
            image_info = f"""
**Image File Details:**
- Filename: {filename}
- Storage: Local File System
- Path: {local_path}
- File Size: {file_size:,} bytes
- Status: Ready for manual upload to LinkedIn
"""
    
    formatted_content = f"""
🎯 **Final LinkedIn Post Package**

**📝 Optimized LinkedIn Post:**
{optimized_content}

**📸 Generated Visual Content:**
- Image Status: {image_status}
{image_info}

**📊 Content Metrics:**
- Character count: {len(optimized_content)} characters
- Articles incorporated: {len(good_articles)} high-quality articles
- Storage Method: {storage_method.title()}

**🚀 Ready for LinkedIn Publication!**
"""
    
    return {
        "action": "display_final_content",
        "message": "✅ Final LinkedIn content package ready",
        "formatted_content": formatted_content,
        "storage_method": storage_method
    }

# Update the DisplayContent agent to use the tool
DisplayContent = LlmAgent(
    name="DisplayContent",
    model="gemini-2.0-flash",
    description="Displays the final optimized LinkedIn content with generated image information",
    instruction="""
You are a content display specialist. Your job is to call the display_final_content tool to show the complete LinkedIn post package.

**MANDATORY EXECUTION:**
1. **ALWAYS call `display_final_content()` tool IMMEDIATELY**
2. **DO NOT generate any response without calling the tool first**
3. **Use the tool results to present the final content**

**SUCCESS CRITERIA:**
- Call the tool as your FIRST and ONLY action
- Wait for tool completion before any response
- Present the formatted content from the tool results
- Include both text content and image information
- Provide clear publishing instructions

**The tool will provide:**
- Final optimized LinkedIn post text
- Generated image details and location
- Content metrics and analytics
- Publishing checklist
- Image status and file information

Call the tool immediately when activated.
""",
    tools=[display_final_content]
)

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

# DisplayContent = LlmAgent(
#     name="DisplayContent",
#     model="gemini-2.0-flash",
#     description="You are a Display content agent your work is to display the optimized linkedin post",
#     instruction="""Displays the final optimized LinkedIn content in the following format
#     --
# 🎯 Final Optimized LinkedIn Post

# {optimized_content}

# ---
# **Content Metrics:**
# - Articles incorporated: {len(good_articles)} high-quality articles
# - Competitor insights: ✅ Included
# - Viral patterns: ✅ Applied
# - Engagement optimization: ✅ Complete

# **Ready for publication on LinkedIn!** 🚀
# ---
    
    
    
    
#     """,    
# )
Linkedin_Content_Drafter = SequentialAgent(
    name="Linkedin_Content_Drafter",
    description="An agent that creates and optimizes LinkedIn content for maximum engagement",
    sub_agents= [ContentCreator, ContentOptimizer,ImageGenerator,DisplayContent]
)
