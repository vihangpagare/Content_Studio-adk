
import time

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
import base64, os, uuid, tempfile, requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

import tweepy
from google.genai import types
from google.adk.tools.tool_context import ToolContext

import os, tempfile, base64, uuid
from pathlib import Path
from typing import Dict, Any
import asyncio, tempfile, base64
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests                                       # ← HTTP client
from google.genai import types                        # ← for artifacts
from google.adk.tools.tool_context import ToolContext




# ---------------- twitter helper (your original code, trimmed) -------------
class TwitterError(Exception):
    def __init__(self, msg: str, code: str, status: int | None = None):
        super().__init__(msg); self.code, self.status = code, status

def _upload_media(api_v1: tweepy.API, img_bytes: bytes, mime: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(img_bytes); tmp.flush()
        media = api_v1.media_upload(filename=tmp.name)
    Path(tmp.name).unlink(missing_ok=True)
    return media.media_id_string

def _tweet(
    text: str,
    *,
    reply_to_tweet_id: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/png",
) -> Dict[str, Any]:
    
    cfg = {
        "api_key": os.getenv("tw_api_key"),
        "api_secret_key": os.getenv("tw_api_secret_key"),
        "access_token": os.getenv("tw_access_token"),
        "access_token_secret": os.getenv("tw_access_token_secret"),
    }
    if any(v is None for v in cfg.values()):
        raise TwitterError("Missing Twitter creds in env-vars", "config_error")
    # v2 client
    client = tweepy.Client(
        consumer_key = cfg["api_key"],
        consumer_secret= cfg["api_secret_key"],
        access_token= cfg["access_token"],
        access_token_secret= cfg["access_token_secret"],
    )
    media_ids = None
    if image_bytes:
        auth_v1 = tweepy.OAuth1UserHandler(
            consumer_key=cfg["api_key"],
            consumer_secret=cfg["api_secret_key"],
            access_token=cfg["access_token"],
            access_token_secret=cfg["access_token_secret"]
        )
        api_v1  = tweepy.API(auth_v1)
        media_id = _upload_media(api_v1, image_bytes, mime_type)
        media_ids = [media_id]
    resp = client.create_tweet(
        text=text, 
        media_ids=media_ids,
        in_reply_to_tweet_id=reply_to_tweet_id
    )
    return {"id": str(resp.data["id"]), "text": text}
# --------------------------------------------------------------------------------


async def post_tweet(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Publishes the optimised caption + **one** image artifact to Twitter.
    Expects:
      • state['optimized_content']  (or instagram / linkedin fallback)
      • state['generated_image_artifact']
    """
    caption = tool_context.state.get("optimized_tweet") 
        
    if not caption:
        return {"action": "post_tweet", "status": "error",
                "message": "No caption found in state."}

    art_name = tool_context.state.get("generated_image_artifact")
    img_bytes = None
    if art_name:
        art_part = await tool_context.load_artifact(filename=art_name)
        if art_part and art_part.inline_data:
            img_bytes = art_part.inline_data.data
        else:
            return {"action": "post_tweet", "status": "error",
                    "message": f"Image artifact '{art_name}' could not be loaded."}

    try:
        result = _tweet(text = caption[:280], image_bytes = img_bytes)
        return {"action": "post_tweet", "status": "success",
                "message": f"✅ Tweet posted (id: {result['id']})"}
    except TwitterError as e:
        return {"action": "post_tweet", "status": "error",
                "message": f"TwitterError ({e.code}): {e}"}


async def post_thread(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Publishes the clean thread with proper separator handling
    """
    # First try to get clean thread, fallback to optimized_thread
    raw_thread = tool_context.state.get("clean_thread_for_posting")
    
    if not raw_thread:
        return {"action": "post_thread",
                "status": "error", 
                "message": "No thread found in state."}

    # Handle clean separated format
    if "---TWEET-SEPARATOR---" in raw_thread:
        tweet_parts = raw_thread.split("---TWEET-SEPARATOR---")
        tweets = []
        for part in tweet_parts:
            part = part.strip()
            if len(part) > 10 :
                
                tweets.append(part[:280])
    else:
        # Fallback to original parsing
        lines = [ln.strip() for ln in raw_thread.split("\n") if ln.strip()]
        tweets = []
        for ln in lines:
            if "/" in ln and ln.split("/")[0].isdigit():
                ln = ln.split(" ", 1)[1] if " " in ln else ln
                if len(ln) > 50:
                    tweets.append(ln[:280])

    if not tweets:
        return {"action": "post_thread",
                "status": "error",
                "message": "No valid tweets found after processing."}

    # Rest of your posting logic remains the same
    img_bytes = None
    img_art = tool_context.state.get("generated_image_artifact")
    if img_art:
        art_part = await tool_context.load_artifact(filename=img_art)
        if art_part and art_part.inline_data:
            img_bytes = art_part.inline_data.data

    results = []
    reply_to = None
    
    try:
        for idx, tw in enumerate(tweets):
            time.sleep(5.0)
            res = _tweet(
                text=tw,
                reply_to_tweet_id=reply_to,
                image_bytes=img_bytes if idx == 0 else None
            )
            results.append(res)
            reply_to = res["id"]
            if idx < len(tweets)-1:
                await asyncio.sleep(1.1)
                
    except TwitterError as e:
        return {"action": "post_thread",
                "status": "error",
                "message": f"TwitterError ({e.code}): {e}"}

    return {"action": "post_thread",
            "status": "success", 
            "message": f"✅ Thread posted ({len(results)} tweets)",
            "tweet_ids": [r["id"] for r in results]}


# async def post_thread(tool_context: ToolContext) -> Dict[str, Any]:
#     """
#     Publishes the optimised thread stored in
#         state["optimized_thread"]   ← 1/n … 2/n … lines
#     plus (optionally) one image artifact on the first tweet
#         state["generated_image_artifact"]

#     Returns success / error dictionary ADK will stream to user.
#     """
#     raw_thread = tool_context.state.get("optimized_thread", "")
#     if not raw_thread:
#         return {"action": "post_thread",
#                 "status": "error",
#                 "message": "No thread found in state."}

#     # ---- split into ordered list of tweets --------------------
#     lines = [ln.strip() for ln in raw_thread.split("\n") if ln.strip()]
#     tweets: List[str] = []
#     for ln in lines:
#         # remove leading '1/7 ' etc.
#         if "/" in ln and ln.split("/")[0].isdigit():
#             ln = ln.split(" ", 1)[1] if " " in ln else ln
#         if len(ln) <= 50 :
#             continue 
#         else:
#             tweets.append(ln[:280])
           
        

#     # ---- optional image for first tweet -----------------------
#     img_bytes = None
#     img_art   = tool_context.state.get("generated_image_artifact")
#     if img_art:
#         art_part = await tool_context.load_artifact(filename=img_art)
#         if art_part and art_part.inline_data:
#             img_bytes = art_part.inline_data.data

#     results: List[Dict[str, Any]] = []
#     reply_to: Optional[str] = None
#     try:
#         for idx, tw in enumerate(tweets):
#             res = _tweet(
#                 txt:=tw,
#                 reply_to_tweet_id=reply_to,
#                 image_bytes=img_bytes if idx == 0 else None
#             )
#             results.append(res)
#             reply_to = res["id"]
#             if idx < len(tweets)-1:
#                 await asyncio.sleep(1.1)   # <= 1 req/sec guard
#     except TwitterError as e:
#         return {"action": "post_thread",
#                 "status": "error",
#                 "message": f"TwitterError ({e.code}): {e}"}

#     return {"action": "post_thread",
#             "status": "success",
#             "message": f"✅ Thread posted ({len(results)} tweets)",
#             "tweet_ids": [r["id"] for r in results]}
    


LINKEDIN_ACCESS_TOKEN = os.getenv("Linkedin_access_token") # put in env
LINKEDIN_AUTHOR_URN   = os.getenv("Linkedin_person_urn") # e.g. "urn:li:person:abcd…"


def _upload_asset(image_bytes: bytes) -> str:
    """Registers & uploads bytes -> returns `asset_urn`."""
    reg_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    reg_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": LINKEDIN_AUTHOR_URN,
            "serviceRelationships": [
                {"relationshipType": "OWNER",
                 "identifier": "urn:li:userGeneratedContent"}
            ]
        }
    }
    j_headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    r = requests.post(reg_url, headers=j_headers, json=reg_payload)
    r.raise_for_status()

    data        = r.json()
    asset_urn   = data["value"]["asset"]
    upload_url  = data["value"]["uploadMechanism"] \
                     ["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"] \
                     ["uploadUrl"]

    up_headers  = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/octet-stream"
    }
    up = requests.put(upload_url, headers=up_headers, data=image_bytes)
    up.raise_for_status()
    return asset_urn


async def post_to_linkedin(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Publishes the *optimized* LinkedIn caption plus **one** image artifact
    that was produced by Linkedin/Instagram generators.

    Expected state keys
    -------------------
    optimized_content          : str   –  final caption
    generated_image_artifact   : str   –  filename of PNG/JPEG artifact
    """
    caption   = tool_context.state.get("optimized_content") 

    if not caption:
        return {"action": "post_to_linkedin",
                "status": "error",
                "message": "No caption found in state (optimized_content)."}

    art_name  = tool_context.state.get("generated_image_artifact")
    if not art_name:
        return {"action": "post_to_linkedin",
                "status": "error",
                "message": "No image artifact found in state."}

    # 1.  Load artifact bytes
    art_part  = await  tool_context.load_artifact(filename=art_name)
    if art_part is None or art_part.inline_data is None:
        return {"action": "post_to_linkedin",
                "status": "error",
                "message": f"Artifact {art_name} not accessible."}

    img_bytes = art_part.inline_data.data

    try:
        # 2.  LinkedIn upload → asset URN
        asset_urn = _upload_asset(img_bytes)

        # 3.  Create post
        post_url  = "https://api.linkedin.com/v2/ugcPosts"
        j_headers = {
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        payload   = {
            "author": LINKEDIN_AUTHOR_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption},
                    "shareMediaCategory": "IMAGE",
                    "media": [{
                        "status": "READY",
                        "media": asset_urn,
                        "description": {"text": " "},
                        "title": {"text": " "}
                    }]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        resp = requests.post(post_url, headers=j_headers, json=payload)
        resp.raise_for_status()

        post_id = resp.headers.get("x-restli-id", "unknown")
        return {
            "action": "post_to_linkedin",
            "status": "success",
            "message": f"✅ Posted to LinkedIn (post id: {post_id})",
            "asset_urn": asset_urn,
            "post_id": post_id
        }

    except requests.HTTPError as e:
        return {"action": "post_to_linkedin",
                "status": "error",
                "message": f"LinkedIn API error: {e.response.status_code} – {e.response.text}"}

    except Exception as e:
        return {"action": "post_to_linkedin",
                "status": "error",
                "message": f"Unexpected error: {e}"}


Posting_Agent= LlmAgent(
    name="Posting_Agent",
    model="gemini-2.0-flash",
    description="Posts the final optimized  content",
    instruction="""
You are the Posting Agent.

1. Ask: “Where should I post – LinkedIn, single Tweet, or Twitter Thread?”
2. Wait for explicit user answer.
3. Map answer:
   • "LinkedIn"   → call `post_to_linkedin`
   • "Tweet" / "X post" → call `post_tweet`
   • "Thread" / "Twitter thread" → call `post_thread`
4. If platform unsupported → apologise & finish.
NEVER post without clear confirmation.
""",
    tools=[
        # MCPToolset(
        #     connection_params=StdioServerParameters(
        #         command="npx",
        #         args=["-y", "@enescinar/twitter-mcp"],
        #         env={"API_KEY": "JY70YvdvsLZ9gvwin861qlQWH",
        #             "API_SECRET_KEY": "tNLMMn5l0W1mf5glIWu4BewhctGbZc5iGCgWURmVHEQPPr6JvE",
        #             "ACCESS_TOKEN": "1697332135898877952-FiiNUkKVKtUPr1wpXEDJ1Iaiv17VGs",
        #             "ACCESS_TOKEN_SECRET": "EAbgB8pEMqYuoR52HnfCo6LABHNvLUD7AdbLhSGdKj8on"},
        #     )
        # ),
        post_to_linkedin,
        post_tweet,
        post_thread,
    ],
    )
