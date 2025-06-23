from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os
import json
import base64
from PIL import Image
from io import BytesIO
import uuid
from datetime import datetime
from google import genai
from google.genai import types
from google.adk.tools.base_tool import BaseTool
from typing import Optional, Dict, Any


load_dotenv()



# Initialize clients
llm = AzureChatOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    model="gpt4o",
)


genai_client = genai.Client()

# Gemini 2.5 Flash Image Analysis + Caption Creation Prompt
INSTAGRAM_MULTIMODAL_CAPTION_PROMPT = """
You are an expert Instagram caption writer using Gemini 2.5 Flash's advanced image analysis capabilities. Create engaging Instagram captions based on the provided image(s) and user context.

**USER CONTEXT:** {user_context}
**COMPANY PROFILE:** {company_profile}

**CAPTION CREATION INSTRUCTIONS:**

**1. ANALYZE THE IMAGE(S):**
- Identify key visual elements, colors, objects, people, and settings
- Understand the mood, atmosphere, and emotional tone
- Recognize any text, brands, or specific details in the image
- Assess the overall composition and visual story

**2. INTEGRATE USER CONTEXT:**
- Combine image insights with the user's provided context
- Ensure the caption reflects both what's seen and what the user wants to communicate
- Maintain consistency with the company's brand voice and personality

**3. CRAFT INSTAGRAM-OPTIMIZED CAPTION:**
- **Hook (first line):** Start with something that stops the scroll
- **Story/Context:** Connect the image to a relatable story or insight
- **Value/Message:** Deliver the key message or takeaway
- **Engagement:** Include a question or call-to-action to encourage comments
- **Hashtags:** Add 5-8 relevant hashtags based on image content and context

**4. INSTAGRAM BEST PRACTICES:**
- Keep it authentic and conversational
- Use line breaks for mobile readability
- Include 2-3 relevant emojis
- Length: 150-300 words (optimal for engagement)
- End with a question to drive comments

**5. VISUAL-TEXT SYNERGY:**
- Reference specific elements visible in the image naturally
- Don't over-describe what's obvious
- Use the image as a springboard for deeper conversation
- Create curiosity about details not immediately apparent

**OUTPUT FORMAT:**
Create a complete Instagram caption that seamlessly blends image analysis with user context, optimized for maximum engagement.

**EXAMPLE STRUCTURE:**
[Hook based on image + context]

[Story that connects image to user's message]

[Key insight or value proposition]

[Call-to-action question]

#hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5
"""

# Topic-based Instagram Content Creation (when no images provided)
INSTAGRAM_TOPIC_CONTENT_PROMPT = """
You are an Instagram content creator. Create engaging Instagram content based on the provided topic and company profile.

**TOPIC:** {topic}
**COMPANY PROFILE:** {company_profile}

**CONTENT CREATION GUIDELINES:**

**1. INSTAGRAM-SPECIFIC APPROACH:**
- Create content that works well with visual storytelling
- Focus on engagement and community building
- Use Instagram's casual, authentic tone

**2. CAPTION STRUCTURE:**
- Hook: Attention-grabbing opening
- Context: Brief setup or background
- Value: Main message or insight
- Engagement: Question or call-to-action
- Hashtags: 5-8 relevant tags


Create a complete Instagram caption with hashtags, optimized for engagement.
"""


async def create_caption_from_images(tool_context: ToolContext) -> Dict[str, Any]:
    """Create Instagram caption using Gemini 2.5 Flash image analysis"""
    print(f"--- Tool: create_caption_from_images called ---")
    
    user_images = tool_context.state.get("instagram_user_images", [])
    user_context = tool_context.state.get("instagram_user_context", "")
    company_profile = tool_context.state.get("Company_Profile", {})
    
    if not user_images:
        return {
            "action": "create_caption_from_images",
            "message": "No user images found for analysis",
            "caption": ""
        }
    
    try:
        # Prepare content for Gemini 2.5 Flash
        contents = []
        
        # Add the prompt
        caption_prompt = INSTAGRAM_MULTIMODAL_CAPTION_PROMPT.format(
            user_context=user_context,
            company_profile=json.dumps(company_profile, indent=2)
        )
        contents.append(types.Part.from_text(caption_prompt))
        
        # Add all user images
        for img_info in user_images:
            try:
                image_artifact = await tool_context.load_artifact(filename=img_info["filename"])
                if image_artifact and image_artifact.inline_data:
                    contents.append(image_artifact)
            except Exception as e:
                print(f"Error loading image {img_info['filename']}: {e}")
                continue
        
        # Call Gemini 2.5 Flash for multimodal analysis + caption creation
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.7,  # Creative but consistent
                max_output_tokens=2000,
                response_modalities=['TEXT']
            )
        )
        
        caption = response.candidates[0].content.parts[0].text.strip()
        
        # Store the caption
        tool_context.state["instagram_caption_draft"] = caption
        tool_context.state["caption_source"] = "image_analysis"
        
        return {
            "action": "create_caption_from_images",
            "message": f"✅ Created Instagram caption from {len(user_images)} image(s) using Gemini 2.5 Flash",
            "caption": caption,
            "images_analyzed": len(user_images),
            "caption_length": len(caption)
        }
        
    except Exception as e:
        error_msg = f"Error creating caption from images: {str(e)}"
        print(error_msg)
        return {
            "action": "create_caption_from_images",
            "message": error_msg,
            "error": str(e),
            "caption": ""
        }

def create_caption_from_topic(tool_context: ToolContext) -> Dict[str, Any]:
    """Create Instagram caption from topic (when no images provided)"""
    print(f"--- Tool: create_caption_from_topic called ---")
    
    topic = tool_context.state.get("topic", {})
    company_profile = tool_context.state.get("Company_Profile", {})
    
    topic_str = topic.get("topic", "") if isinstance(topic, dict) else str(topic)
    
    if not topic_str:
        return {
            "action": "create_caption_from_topic",
            "message": "No topic available for caption creation",
            "caption": ""
        }
    
    # Create caption from topic
    caption_prompt = INSTAGRAM_TOPIC_CONTENT_PROMPT.format(
        topic=topic_str,
        company_profile=json.dumps(company_profile, indent=2)
    )
    
    caption_response = llm.invoke(caption_prompt)
    caption = caption_response.content.strip()
    
    # Store the caption
    tool_context.state["instagram_caption_draft"] = caption
    tool_context.state["caption_source"] = "topic_based"
    
    return {
        "action": "create_caption_from_topic",
        "message": f"Created Instagram caption from topic: {topic_str}",
        "caption": caption,
        "topic": topic_str,
        "caption_length": len(caption)
    }

def optimize_instagram_caption(tool_context: ToolContext) -> Dict[str, Any]:
    """Optimize the Instagram caption for maximum engagement"""
    print(f"--- Tool: optimize_instagram_caption called ---")
    
    draft = tool_context.state.get("instagram_caption_draft", "")
    
    if not draft:
        return {
            "action": "optimize_instagram_caption",
            "message": "No caption draft found to optimize",
            "optimized_caption": ""
        }
    
    # Simple optimization prompt
    optimization_prompt = f"""
    Optimize this Instagram caption for maximum engagement:
    
    {draft}
    
    Improve:
    - Hook strength (first line)
    - Engagement triggers
    - Hashtag strategy
    - Call-to-action effectiveness
    - Mobile readability
    
    Return only the optimized caption.DO NOT GIVE ANY PRO-TIPS OR ANYTHING ELSE LIKE THAT
    """
    
    optimized_response = llm.invoke(optimization_prompt)
    optimized_caption = optimized_response.content.strip()
    
    # Store optimized caption
    tool_context.state["optimized_instagram_caption"] = optimized_caption
    
    return {
        "action": "optimize_instagram_caption",
        "message": f"Optimized Instagram caption ({len(optimized_caption)} characters)",
        "optimized_caption": optimized_caption,
        "original_length": len(draft),
        "optimized_length": len(optimized_caption)
    }

async def generate_image_if_needed(tool_context: ToolContext) -> Dict[str, Any]:
    """Generate image"""
    print(f"--- Tool: generate_image_if_needed called ---")
    
    
    
    
    
    # Generate image for topic-based content
    optimized_caption = tool_context.state.get("optimized_instagram_caption", "")
    topic = tool_context.state.get("topic", {})
    
    
    if not optimized_caption:
        return {
            "action": "generate_image_if_needed",
            "message": "No caption found for image generation",
            "image_generated": False
        }
    prompt_builder = f"""
You are a senior visual-branding strategist.

TASK: Write an **image-generation prompt** for Gemini image model that will
pair perfectly with the following Instagram topic post.

--- TOPIC (verbatim) ---
{topic}
---------------------------------------------------------------

Prompt requirements:
• Square format, 1080×1080, high-resolution, social-media ready  
• Capture the mood / emotion expressed by the caption  
• Respect brand's professional, trustworthy corporate-finance identity  
• Describe composition (camera angle, focal subject, supporting details)  
• Specify colour palette (incl. HEX codes), lighting style, depth-of-field  
• • NO TEXT, quotes, or typography in the image.   <-- IMPORTANT!
• End the prompt with:  ###END###
Return only the prompt.
"""
    try:
        prompt_resp = llm.invoke(prompt_builder)
        image_prompt = prompt_resp.content.split("###END###")[0].strip()
        tool_context.state["instagram_image_generation_prompt"] = image_prompt
    except Exception as e:
        return {"action": "generate_image_if_needed",
                "message": f"❌ Prompt-generation error: {e}",
                "image_generated": False}
    try:
        # Create image prompt from caption
        
        
        # Generate image
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=image_prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        # Save image as artifact
        image_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                break
        
        if image_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            artifact_filename = f"instagram_generated_{timestamp}_{unique_id}.png"
            
            image_artifact = types.Part.from_bytes(
                data=image_data,
                mime_type="image/png"
            )
            
            version = await tool_context.save_artifact(
                filename=artifact_filename,
                artifact=image_artifact
            )
            
            tool_context.state["generated_instagram_image"] = artifact_filename
            
            return {
                "action": "generate_image_if_needed",
                "message": f"Generated Instagram image: {artifact_filename}",
                "image_generated": True,
                "artifact_filename": artifact_filename
            }
        
        return {
            "action": "generate_image_if_needed",
            "message": "No image data generated",
            "image_generated": False
        }
        
    except Exception as e:
        return {
            "action": "generate_image_if_needed",
            "message": f"Error generating image: {str(e)}",
            "error": str(e),
            "image_generated": False
        }

async def display_instagram_package(tool_context: ToolContext) -> Dict[str, Any]:
    """Display final Instagram content package"""
    print(f"--- Tool: display_instagram_package called ---")
    
    optimized_caption = tool_context.state.get("optimized_instagram_caption", "")
    
    caption_source = tool_context.state.get("caption_source", "")
    
    generated_image = tool_context.state.get("generated_instagram_image", "")
    
    if not optimized_caption:
        return {
            "action": "display_instagram_package",
            "message": "❌ No Instagram caption found",
            "final_package": ""
        }
    
    # Prepare image information
    
    if generated_image:
        image_info = f"""
**🎨 Generated Image:**
• {generated_image}
- Source: AI-Generated
- Status: ✅ Ready for Instagram
"""
    else:
        image_info = """
**📸 Images:**
- Status: ❌ No images available
"""
    
    formatted_package = f"""
📱 **Instagram Content Package Ready**

**📝 Optimized Instagram Caption:**

{optimized_caption}

{image_info}

**📊 Package Details:**
- Caption length: {len(optimized_caption)} characters
- Content source: {caption_source.replace('_', ' ').title()}

**🚀 Ready for Instagram!**

**📋 Publishing Steps:**
1. ✅ Copy the caption above
2. ✅ Post to Instagram
3. ✅ Engage with comments
"""
    
    return {
        "action": "display_instagram_package",
        "message": "✅ Instagram content package complete",
        "final_package": formatted_package,
    }

# # Create individual agents
# PathDeterminer = LlmAgent(
#     name="PathDeterminer",
#     model="gemini-2.5-flash",
#     description="Determines content creation path based on user input",
#     instruction="""
# You determine the Instagram content creation path. Call determine_content_path immediately.

# **MANDATORY:** Call `determine_content_path()` tool once when activated.
# """,
#     tools=[determine_content_path]
# )

ImageCaptionCreator = LlmAgent(
    name="ImageCaptionCreator", 
    model="gemini-2.5-flash",
    description="Creates captions from user images using Gemini 2.5 Flash",
    instruction="""
You create Instagram captions from user-provided images using Gemini 2.5 Flash multimodal analysis.

**EXECUTION RULES:**
Call the create_caption_from_topic tool Once


""",
    tools=[create_caption_from_topic]
)

CaptionOptimizer = LlmAgent(
    name="CaptionOptimizer",
    model="gemini-2.5-flash", 
    description="Optimizes Instagram captions for engagement",
    instruction="""
You optimize Instagram captions. Call optimize_instagram_caption .
""",
    tools=[optimize_instagram_caption]
)

Instagram_ImageGenerator = LlmAgent(
    name="Instagtam_ImageGenerator",
    model="gemini-2.5-flash",
    description="Generates images when needed (topic-based content only)",
    instruction="""
You generate images .Call generate_image_if_needed only once

""",
    tools=[generate_image_if_needed]
)

PackageDisplayer = LlmAgent(
    name="PackageDisplayer",
    model="gemini-2.5-flash",
    description="Displays final Instagram content package",
    instruction="""
You display the final Instagram package. Call display_instagram_package immediately.

**MANDATORY:** Call `display_instagram_package()` tool immediately when activated.
""",
    tools=[display_instagram_package]
)

# Create the main Sequential Agent
Instagram_Content_Drafter = SequentialAgent(
    name="Instagram_Content_Drafter",
    description="Creates Instagram content from user images+context OR generates image+caption from topic",
    sub_agents=[         
        ImageCaptionCreator,     # Creates captions using Gemini 2.5 Flash OR topic
        CaptionOptimizer,        # Optimizes for Instagram engagement
        Instagram_ImageGenerator,          # Generates image only if needed (topic-based)
        PackageDisplayer         # Shows final package
    ],
    # before_model_callback=instagram_before_callback
)


# Simple callback function to store images as artifacts

# async def bm_capture_images_and_strip(
#     callback_context: CallbackContext,          # ADK gives us LlmRequest + context
#     llm_request: LlmRequest
# ) -> Optional[LlmResponse]:

#     """
#     • Runs before every Gemini call made by Instagram_Content_Drafter
#     • Removes the unsupported `display_name` from all image parts
#     • Stores every image as an ADK artifact and remembers metadata in
#       state['instagram_user_images'].
#     """

#     cleaned_parts = []
#     new_images_meta = callback_context.tool_context.state.get(
#         "instagram_user_images", []
#     )

#     for part in llm_request.contents[-1].parts:              # last user msg
#         if getattr(part, "inline_data", None):
#             # ----- 1) grab bytes & persist as artifact -------------------
#             raw   = part.inline_data.data
#             mt    = part.inline_data.mime_type or "image/png"
#             ext   = "jpg" if mt.endswith("jpeg") else mt.split("/")[-1]
#             fname = f"instagram_{datetime.utcnow():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.{ext}"

#             art   = types.Part.from_bytes(data=raw, mime_type=mt)
#             ver   = await callback_context.tool_context.save_artifact(fname, art)

#             new_images_meta.append({"filename": fname,
#                                     "version":  ver,
#                                     "mime_type": mt})

#             # ----- 2) strip image from prompt (or keep tiny placeholder) --
#             cleaned_parts.append(types.Part(text="[image received]"))
#         else:
#             cleaned_parts.append(part)                       # keep text parts

#     # Replace the original parts with the cleaned ones (no display_name)
#     llm_request.contents[-1].parts = cleaned_parts
#     callback_context.tool_context.state["instagram_user_images"] = new_images_meta
#     return None       


# def process_input(tool_context: ToolContext,user_input : str) -> Dict[str, Any]:
#     """Process user input and stores text input as user_context for an image"""
    
#     user_images = tool_context.state.get("instagram_user_images", [])
#     tool_context.state["instagram_user_context"] = user_input.strip()
    
#     # user_context = tool_context.state.get("user_context", "")
#     # topic = tool_context.state.get("topic", {})
    
#     if user_images :
#         message = "Images processed successfully."
#     else:
#         message = "Image processing failed"
    
    
    
    
    
#     return {
#         "action": "process_input",
#         "message": message,
#     }
    
    

# Instagram_Content_Drafter = LlmAgent(
#     name="Instagram_Content_Drafter",
#     model="gemini-2.5-flash",
#     description="Instagram content creation with image analysis using Gemini 2.5 Flash",
#     instruction="""You are the Instagram Content Drafter. Follow this workflow:

# **STEP 1: ASK FOR CONTENT FIRST**
# When first activated, ask the user:


# What would you like to do? Please share your images and context, or tell me your topic!"

# **STEP 2: PROCESS INPUT**
# - When user provides images + context → Call `process_input()` with their context text

# **STEP 3: CONTENT GENERATION**
# When user says "create content", "generate", or confirms readiness:
# - Call `process_input()` to verify everything is ready
# - If ready → Delegate to `Instagram_Content_Sequential`
# - If not ready → Ask for missing components

# **KEY RULES:**
# - Always ask for content first when activated
# - Use `process_input()` tool to check readiness and store context
# - Only delegate when user confirms they're ready for generation
# - Provide clear guidance about what's needed
# """,
#     tools=[process_input],
#     sub_agents=[Instagram_Content_Sequential],
#     # before_model_callback=bm_capture_images_and_strip
#     #before_tool_callback=process_images_callback  # This does the real work!
# )
