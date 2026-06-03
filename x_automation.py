import base64
import binascii
import json
import os
import re
import time
from urllib.parse import quote

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

POST_CHAR_LIMIT = 260
POST_CONFIRMATION_WAIT_MS = 5000
POST_BUTTON_TIMEOUT_MS = 60000
HIDDEN_CHAR_PATTERN = re.compile(r"[\s\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
OUTPUT_IMAGE_FILENAME = "x_card.png"

# Default fallbacks if user secrets are missing
DEFAULT_TWEET_TEXT = (
    "🔥 New AI automation drop for creators.\n\n"
    "→ Build faster workflows\n"
    "→ Save hours weekly\n\n"
    "Try it today 👇\n\n"
    "#AI #Automation #CreatorTools"
)

DEFAULT_IMAGE_PROMPT = (
    "Dark blue/purple background, bold white text, gold/green accent color, "
    "clean minimal professional design, 16:9 ratio, no faces, no robots."
)


def normalize_auth_header(api_key):
    if not api_key:
        return None
    if api_key.lower().startswith("bearer "):
        return api_key
    return "Bearer " + api_key


def sanitize_env_value(value):
    if value is None:
        return None
    cleaned = HIDDEN_CHAR_PATTERN.sub("", value)
    return cleaned or None


def clean_json_response(text):
    cleaned = text.strip()
    if "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1]
        if "```" in cleaned:
            cleaned = cleaned.split("```", 1)[0]
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    return cleaned.strip()


def fallback_with_error(label, exc):
    print(f"{label}: {type(exc).__name__}")
    return DEFAULT_TWEET_TEXT, DEFAULT_IMAGE_PROMPT


def normalize_same_site(value):
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "strict":
            return "Strict"
        elif normalized == "lax":
            return "Lax"
        elif normalized == "none":
            return "None"
    return "Lax"


def decode_base64_json(payload):
    try:
        decoded_bytes = base64.b64decode(payload)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            "The X_COOKIES environment variable is not valid base64 encoding."
        ) from exc
    try:
        decoded = decoded_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("X_COOKIES base64 payload must be UTF-8 JSON.") from exc
    try:
        return json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ValueError("X_COOKIES base64 payload must contain valid JSON.") from exc


def parse_cookie_json(cookies_json):
    if not cookies_json:
        return []
    try:
        data = json.loads(cookies_json)
    except json.JSONDecodeError:
        data = decode_base64_json(cookies_json)
    if isinstance(data, dict) and "cookies" in data:
        data = data["cookies"]
    if not isinstance(data, list):
        raise ValueError("X_COOKIES must be a JSON array of cookie objects.")
    return data


def has_cookie_scope(cookie):
    return "url" in cookie or "domain" in cookie


def sanitize_cookies(raw_cookies):
    allowed_keys = {
        "name",
        "value",
        "domain",
        "path",
        "expires",
        "httpOnly",
        "secure",
        "sameSite",
        "url",
    }
    sanitized = []
    for cookie in raw_cookies:
        if not isinstance(cookie, dict):
            continue
        clean_cookie = {key: cookie[key] for key in allowed_keys if key in cookie}
        if "name" not in clean_cookie or "value" not in clean_cookie:
            continue
        if "expires" not in clean_cookie and "expirationDate" in cookie:
            clean_cookie["expires"] = cookie["expirationDate"]
        if "sameSite" in clean_cookie:
            clean_cookie["sameSite"] = normalize_same_site(clean_cookie["sameSite"])
        else:
            clean_cookie["sameSite"] = "Lax"
        if "expires" in clean_cookie:
            try:
                expires_value = float(clean_cookie["expires"])
            except (TypeError, ValueError):
                clean_cookie.pop("expires", None)
            else:
                if expires_value < 0:
                    clean_cookie.pop("expires", None)
                else:
                    clean_cookie["expires"] = int(expires_value)
        if not has_cookie_scope(clean_cookie):
            continue
        if "path" not in clean_cookie:
            clean_cookie["path"] = "/"
        sanitized.append(clean_cookie)
    return sanitized


def call_premium_ai():
    # Public Setup: Dynamically load configurations from user's GitHub Secrets
    api_endpoint = os.getenv("PREMIUM_API_URL", "https://api.xiaomimimo.com/anthropic/v1/messages").strip()
    api_key = os.getenv("PREMIUM_API_KEY", "").strip()
    model_name = os.getenv("PREMIUM_MODEL", "claude-3-5-sonnet-20240620").strip()
    
    # Custom prompts provided by the user, or generic defaults
    system_prompt = os.getenv("SYSTEM_PROMPT", "You are a professional X content creator. Write an engaging English post under 260 characters total, including hashtags. Return JSON format with 'tweet_text' and 'image_prompt' keys.").strip()
    user_prompt = os.getenv("USER_PROMPT", "Generate the JSON response now.").strip()

    if not api_key:
        raise ValueError("PREMIUM_API_KEY is missing in GitHub Secrets.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Handle Anthropic headers if endpoint matches
    if "anthropic" in api_endpoint.lower():
        headers["anthropic-version"] = "2023-06-01"

    # Dynamic payload adapting to user configuration
    payload = {
        "model": model_name,
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": user_prompt}]
    }
    
    if "anthropic" in api_endpoint.lower():
        payload["system"] = system_prompt
    else:
        # Standard OpenAI formatting fallback
        payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(api_endpoint, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    
    if "anthropic" in api_endpoint.lower():
        return response.json()["content"][0]["text"]
    else:
        return response.json()["choices"][0]["message"]["content"]


def normalize_tweet_text(post_text):
    post_text = post_text.replace("\r\n", "\n").strip()
    if not post_text:
        post_text = DEFAULT_TWEET_TEXT
    if len(post_text) > POST_CHAR_LIMIT:
        post_text = post_text[:POST_CHAR_LIMIT].rstrip()
    return post_text


def generate_post():
    try:
        content = call_premium_ai()
        parsed = json.loads(clean_json_response(content))
        post_text = parsed.get("tweet_text")
        image_prompt = parsed.get("image_prompt")
        if not isinstance(post_text, str):
            post_text = DEFAULT_TWEET_TEXT
        if not isinstance(image_prompt, str):
            image_prompt = DEFAULT_IMAGE_PROMPT
    except Exception as exc:
        print(f"AI Generation fell back to default layout due to: {exc}")
        return DEFAULT_TWEET_TEXT, DEFAULT_IMAGE_PROMPT

    post_text = normalize_tweet_text(post_text)
    image_prompt = image_prompt.strip() or DEFAULT_IMAGE_PROMPT
    return post_text, image_prompt


def download_pollinations_image(image_prompt, output_path):
    prompt = image_prompt.strip() or DEFAULT_IMAGE_PROMPT
    encoded_prompt = quote(prompt, safe="")
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true"
    
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with open(output_path, "wb") as file:
        file.write(response.content)
    return output_path


def click_post_button(page):
    # Aggressive UI Injection to forcefully publish on X across different viewport configurations
    try:
        page.keyboard.press("Control+Enter")
        time.sleep(2)
    except Exception:
        pass
        
    try:
        page.evaluate('''
            const selectors = [
                'button[data-testid="tweetButtonInline"]', 
                'div[data-testid="tweetButtonInline"]', 
                'button[data-testid="tweetButton"]'
            ];
            for (let sel of selectors) {
                let elements = document.querySelectorAll(sel);
                for (let el of elements) {
                    el.click();
                }
            }
        ''')
        time.sleep(2)
    except Exception:
        pass
        
    try:
        selectors = "button[data-testid='tweetButtonInline'], div[data-testid='tweetButtonInline'], button[data-testid='tweetButton']"
        page.locator(selectors).first.click(force=True, timeout=10000)
        return True
    except Exception:
        pass
        
    try:
        page.locator('//span[contains(text(), "Post")]').first.click(force=True, timeout=10000)
        return True
    except Exception:
        return False


def post_to_x(post_text, image_path):
    cookies_json = os.getenv("X_COOKIES")
    headless = os.getenv("X_HEADLESS", "true").lower() != "false"

    if not cookies_json:
        print("X_COOKIES missing; skipping X post.")
        return False

    try:
        cookies = sanitize_cookies(parse_cookie_json(cookies_json))
    except Exception as exc:
        print(f"Cookie parsing exception: {exc}")
        return False
        
    if not cookies:
        print("No usable cookies detected.")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        try:
            context.add_cookies(cookies)
            page = context.new_page()
            page.goto("https://x.com/home", wait_until="domcontentloaded")

            try:
                page.wait_for_selector("div[data-testid='tweetTextarea_0']", timeout=15000)
            except PlaywrightTimeoutError:
                print("Session verification failed; cookies might be invalid.")
                return False

            page.click("div[data-testid='tweetTextarea_0']")
            page.keyboard.type(post_text)

            if image_path and os.path.exists(image_path):
                page.set_input_files("input[data-testid='fileInput']", image_path)

            page.wait_for_timeout(1000)
            if not click_post_button(page):
                return False
            page.wait_for_timeout(POST_CONFIRMATION_WAIT_MS)
            return True
        finally:
            context.close()
            browser.close()


def main():
    post_text, image_prompt = generate_post()
    image_path = None
    try:
        image_path = download_pollinations_image(image_prompt, OUTPUT_IMAGE_FILENAME)
    except Exception as exc:
        print(f"Media pipeline skipped: {exc}")
        
    try:
        posted = post_to_x(post_text, image_path)
        if not posted:
            print("X deployment aborted.")
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)


if __name__ == "__main__":
    main()
  
