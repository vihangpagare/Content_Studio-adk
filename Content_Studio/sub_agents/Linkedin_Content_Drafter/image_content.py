# Add to imports in Linkedin_Content_Drafter/agent.py
from google import genai
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
import json

load_dotenv()
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
import uuid


# Initialize Gemini client
genai_client = genai.Client()
llm  = AzureChatOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    model="gpt4o",
)



# Enhanced directional image generation prompt
IMAGE_PROMPT_GENERATION = """
You are an expert visual content strategist specializing in creating precise, directional image generation prompts. Analyze the LinkedIn post content and systematically construct a detailed visual prompt focusing on key directional elements.

**LinkedIn Post Content:**
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
    optimized_content = tool_context.state.get("optimized_content", "")
    company_profile = tool_context.state.get("Company_Profile", {})
    
    if not optimized_content:
        return {
            "action": "generate_image_prompt",
            "message": "No optimized content found for image prompt generation",
            "image_prompt": ""
        }
    
    # Generate image prompt using LLM
    prompt_generation = IMAGE_PROMPT_GENERATION.format(
        optimized_content=optimized_content,
        company_profile=company_profile
    )
    
    prompt_response = llm.invoke(prompt_generation)
    image_prompt = prompt_response.content.strip()
    
    # Store in state
    tool_context.state["image_prompt"] = image_prompt
    
    return {
        "action": "generate_image_prompt",
        "message": "Successfully generated image prompt based on optimized content",
        "image_prompt": image_prompt
    }

# def generate_and_save_image(tool_context: ToolContext) -> Dict[str, Any]:
#     """
#     Generate image using Gemini and save it with unique ID
    
#     Args:
#         tool_context: Context for accessing session state
    
#     Returns:
#         Dictionary with image generation status and file path
#     """
#     print(f"--- Tool: generate_and_save_image called ---")
    
#     # Get image prompt from state
#     image_prompt = tool_context.state.get("image_prompt", "")
    
#     if not image_prompt:
#         return {
#             "action": "generate_and_save_image",
#             "message": "No image prompt found for image generation",
#             "image_path": ""
#         }
    
#     try:
#         # Generate image using Gemini
#         response = genai_client.models.generate_content(
#             model="gemini-2.0-flash-preview-image-generation",
#             contents=image_prompt,
#             config=types.GenerateContentConfig(
#                 response_modalities=['TEXT', 'IMAGE']
#             )
#         )
        
#         # Create images directory if it doesn't exist
#         images_dir = "generated_images"
#         os.makedirs(images_dir, exist_ok=True)
        
#         # Generate unique filename
#         unique_id = str(uuid.uuid4())
#         image_filename = f"linkedin_post_{unique_id}.png"
#         image_path = os.path.join(images_dir, image_filename)
        
#         # Save the image
#         image_saved = False
#         for part in response.candidates[0].content.parts:
#             if part.inline_data is not None:
#                 image = Image.open(BytesIO(part.inline_data.data))
#                 image.save(image_path)
#                 image_saved = True
#                 break
        
#         if not image_saved:
#             return {
#                 "action": "generate_and_save_image",
#                 "message": "No image data found in response",
#                 "image_path": ""
#             }
        
#         # Store image path in state
#         tool_context.state["generated_image_path"] = image_path
#         tool_context.state["image_filename"] = image_filename
        
#         return {
#             "action": "generate_and_save_image",
#             "message": f"Successfully generated and saved image: {image_filename}",
#             "image_path": image_path,
#             "image_filename": image_filename
#         }
        
#     except Exception as e:
#         error_msg = f"Error generating image: {str(e)}"
#         print(error_msg)
#         return {
#             "action": "generate_and_save_image",
#             "message": error_msg,
#             "error": str(e),
#             "image_path": ""
#         }

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
    image_prompt = tool_context.state.get("image_prompt", "")
    if not image_prompt:
        return {
            "action": "generate_and_save_image_artifact",
            "message": "No image prompt found for image generation", 
            "artifact_filename": ""
        }
    
    try:
        # Generate image using Gemini
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=image_prompt,
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
        artifact_filename = f"linkedin_post_image_{timestamp}_{unique_id}.png"
        
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

        
    # except ValueError as e:
    #     error_msg = f"Artifact service error: {str(e)}"
    #     print(error_msg)
    #     return {
    #         "action": "generate_and_save_image_artifact",
    #         "message": error_msg,
    #         "error": str(e),
    #         "artifact_filename": ""
    #     }
    # except Exception as e:
    #     error_msg = f"Error generating image: {str(e)}"
    #     print(error_msg)
    #     return {
    #         "action": "generate_and_save_image_artifact",
    #         "message": error_msg,
    #         "error": str(e),
    #         "artifact_filename": ""
    #     }
# Create ImageGenerator agent
ImageGenerator = LlmAgent(
    name="ImageGenerator",
    model="gemini-2.0-flash",
    description="Generates visual content for LinkedIn posts using Gemini image generation",
    instruction="""
You are an image generation specialist for LinkedIn content. Your job is to:

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
