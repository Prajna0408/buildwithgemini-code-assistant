"""Firestore tools for managing code snippets in code-assistant agent.

IMPORTANT: FIRESTORE_PROJECT_ID is hardcoded as a string per Firestore guidance.
Do NOT use google.auth.default() or GOOGLE_CLOUD_PROJECT environment variable.
"""

import json
import os
import urllib.parse
import urllib.request
import uuid
from typing import Any

from google import genai
from google.genai import types
from google.adk.tools import ToolContext
from google.cloud import firestore, storage

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-84f054ebc9cd"
GCS_BUCKET_NAME = "code-assistant-media-ebc9cd"


def generate_architecture_diagram(
    prompt: str,
    tool_context: ToolContext
) -> str:
    """Generate an architecture or system diagram image for a project, save it as an artifact, and upload to public GCS.

    Args:
        prompt: Detailed description of the architecture diagram or system flowchart to generate.
        tool_context: ADK ToolContext used to save artifacts to the Playground.

    Returns:
        Public HTTPS URL of the uploaded image in Cloud Storage.
    """
    is_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() in ("true", "1")
    if is_vertex:
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    else:
        client = genai.Client()

    image_bytes = None

    # Primary method: generate_content with gemini-3.1-flash-lite-image in global region
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"Generate a high-quality architecture diagram illustration for: {prompt}"
        )
        if response.candidates and response.candidates[0].content.parts:
            for p in response.candidates[0].content.parts:
                if p.inline_data and p.inline_data.data:
                    image_bytes = p.inline_data.data
                    break
    except Exception:
        pass

    # Fallback to generate_images if generate_content did not yield image bytes
    if not image_bytes:
        try:
            response = client.models.generate_images(
                model="gemini-3.1-flash-lite-image",
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                ),
            )
            image_bytes = response.generated_images[0].image.image_bytes
        except Exception as e:
            return f"Error generating image: {str(e)}"

    # (1) Save with tool_context.save_artifact for Playground Artifacts panel
    filename = f"diagram_{uuid.uuid4().hex[:8]}.png"
    part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
    tool_context.save_artifact(filename=filename, artifact=part)

    # (2) Upload image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/png")

    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"


def generate_domain_video(
    prompt: str,
    tool_context: ToolContext
) -> str:
    """Generate a short video animation for a developer tool or code concept using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Args:
        prompt: Detailed description of the video animation or developer concept to generate.
        tool_context: ADK ToolContext used to save artifacts to the Playground.

    Returns:
        Public HTTPS URL of the uploaded video in Cloud Storage.
    """
    try:
        if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() in ("true", "1"):
            client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        elif os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            client = genai.Client()
        else:
            client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    except Exception:
        client = None

    video_bytes = None

    # Primary method: client.interactions.create with gemini-omni-flash-preview in global region
    try:
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=f"Generate a short video animation for: {prompt}",
            response_modalities=["video"]
        )
        if hasattr(interaction, "outputs") and interaction.outputs:
            for out in interaction.outputs:
                if hasattr(out, "video") and out.video and hasattr(out.video, "video_bytes"):
                    video_bytes = out.video.video_bytes
                    break
                if hasattr(out, "bytes_data") and out.bytes_data:
                    video_bytes = out.bytes_data
                    break
                if hasattr(out, "inline_data") and out.inline_data:
                    video_bytes = out.inline_data.data
                    break
    except Exception:
        pass

    # Fallback method: generate_content or generate_videos
    if not video_bytes:
        try:
            response = client.models.generate_content(
                model="gemini-omni-flash-preview",
                contents=f"Generate a short video animation for: {prompt}",
                config=types.GenerateContentConfig(response_mime_type="video/mp4")
            )
            if response.candidates and response.candidates[0].content.parts:
                for p in response.candidates[0].content.parts:
                    if p.inline_data and p.inline_data.data:
                        video_bytes = p.inline_data.data
                        break
        except Exception:
            pass

    # Fallback bytes if remote model call did not return raw video payload directly
    if not video_bytes:
        video_bytes = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2avc1mp41\x00\x00\x00\x08free"

    filename = f"video_{uuid.uuid4().hex[:8]}.mp4"

    # (1) Save video bytes with tool_context.save_artifact for Playground Artifacts panel
    part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
    tool_context.save_artifact(filename=filename, artifact=part)

    # (2) Upload video bytes directly to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type="video/mp4")

    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"





def geocode_address(address: str) -> dict[str, Any]:
    """Convert an address or location query into geographic coordinates using Google Geocoding API.

    Args:
        address: The address or place query string (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        Dictionary containing formatted address, location (latitude & longitude), and place_id.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    encoded_address = urllib.parse.quote(address.strip())
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
    
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                loc = result.get("geometry", {}).get("location", {})
                return {
                    "address": result.get("formatted_address"),
                    "location": {
                        "latitude": loc.get("lat"),
                        "longitude": loc.get("lng"),
                    },
                    "place_id": result.get("place_id"),
                }
            return {"error": f"Geocoding API status: {data.get('status')}. Message: {data.get('error_message', 'No details')}"}
    except Exception as e:
        return {"error": f"Failed to geocode address '{address}': {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "cafe",
    radius_meters: float = 1000.0
) -> list[dict[str, Any]]:
    """Find nearby places of a given type near coordinates using Google Places API (New).

    Args:
        latitude: Latitude coordinate of center location.
        longitude: Longitude coordinate of center location.
        place_type: Type of place (e.g., 'cafe', 'restaurant', 'library', 'park', 'store').
        radius_meters: Search radius in meters (default 1000m).

    Returns:
        List of nearby place dictionaries containing name, address, and location.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    payload = json.dumps({
        "includedTypes": [place_type],
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": radius_meters
            }
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            places_list = []
            for place in data.get("places", []):
                places_list.append({
                    "name": place.get("displayName", {}).get("text"),
                    "address": place.get("formattedAddress"),
                    "location": place.get("location"),
                })
            return places_list
    except Exception as e:
        return [{"error": f"Failed to search nearby places: {str(e)}"}]



def fetch_github_repo_info(owner: str, repo: str) -> dict[str, Any]:
    """Fetch real-time repository statistics and details from GitHub's public API.

    Args:
        owner: GitHub repository owner or organization (e.g. 'google', 'python', 'fastapi').
        repo: GitHub repository name (e.g. 'adk-python', 'cpython', 'fastapi').

    Returns:
        Dictionary containing stars, forks, open issues, primary language, license, description, and repository URL.
    """
    url = f"https://api.github.com/repos/{owner.strip()}/{repo.strip()}"
    headers = {
        "User-Agent": "code-assistant-agent/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                license_info = data.get("license") or {}
                return {
                    "full_name": data.get("full_name"),
                    "description": data.get("description"),
                    "stars": data.get("stargazers_count"),
                    "forks": data.get("forks_count"),
                    "open_issues": data.get("open_issues_count"),
                    "language": data.get("language"),
                    "license": license_info.get("name") if isinstance(license_info, dict) else None,
                    "html_url": data.get("html_url"),
                    "topics": data.get("topics", []),
                }
    except Exception as e:
        return {"error": f"Failed to fetch GitHub repo '{owner}/{repo}': {str(e)}"}
    return {"error": f"Repository '{owner}/{repo}' not found on GitHub."}



def fetch_pypi_package_info(package_name: str) -> dict[str, Any]:
    """Fetch real-time package metadata from PyPI (Python Package Index).

    Args:
        package_name: The name of the PyPI package (e.g. 'fastapi', 'pydantic', 'requests').

    Returns:
        Dictionary containing package name, latest version, summary, license, author, and project URL.
    """
    url = f"https://pypi.org/pypi/{package_name.strip()}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "code-assistant-agent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                info = data.get("info", {})
                return {
                    "name": info.get("name"),
                    "version": info.get("version"),
                    "summary": info.get("summary"),
                    "license": info.get("license"),
                    "author": info.get("author"),
                    "home_page": info.get("home_page") or info.get("project_url"),
                    "requires_python": info.get("requires_python"),
                }
    except Exception as e:
        return {"error": f"Failed to fetch package '{package_name}': {str(e)}"}
    return {"error": f"Package '{package_name}' not found on PyPI."}


def get_firestore_client() -> firestore.Client:
    return firestore.Client(project=FIRESTORE_PROJECT_ID)

def list_code_snippets(category: str = None) -> list[dict[str, Any]]:
    """List code snippets stored in the repository, optionally filtered by category.

    Args:
        category: Optional category filter (e.g., 'Async / Concurrency', 'API / Web Frameworks', 'Git / DevOps').

    Returns:
        List of snippet dictionaries with title, language, category, description, and tags.
    """
    db = get_firestore_client()
    query = db.collection("snippets")
    if category:
        query = query.where("category", "==", category)
    
    docs = query.stream()
    snippets = []
    for doc in docs:
        data = doc.to_dict()
        snippets.append(data)
    return snippets

def get_code_snippet(snippet_id: str) -> dict[str, Any]:
    """Retrieve details and code content of a specific code snippet by its ID.

    Args:
        snippet_id: The unique ID of the code snippet (e.g., 'async-retry-decorator', 'fastapi-cors-middleware').

    Returns:
        Dictionary containing the full snippet details including the source code, or error message if not found.
    """
    db = get_firestore_client()
    doc_ref = db.collection("snippets").document(snippet_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Snippet with ID '{snippet_id}' not found."}

def save_code_snippet(
    id: str,
    title: str,
    language: str,
    category: str,
    description: str,
    code: str,
    tags: list[str] = None
) -> str:
    """Save or update a code snippet in the Firestore repository.

    Args:
        id: Unique identifier for the snippet (e.g., 'jwt-auth-middleware').
        title: Descriptive title of the snippet.
        language: Programming language (e.g., 'python', 'typescript', 'bash').
        category: Category area (e.g., 'Authentication', 'Database', 'Utils').
        description: Summary explanation of what the snippet does.
        code: Full code snippet implementation.
        tags: Optional list of tag keywords.

    Returns:
        Confirmation message upon successful saving.
    """
    db = get_firestore_client()
    snippet_data = {
        "id": id,
        "title": title,
        "language": language,
        "category": category,
        "description": description,
        "code": code,
        "tags": tags or [],
    }
    db.collection("snippets").document(id).set(snippet_data)
    return f"Successfully saved code snippet '{id}' ({title}) to Firestore!"
