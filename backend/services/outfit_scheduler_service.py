"""
outfit_scheduler_service.py — FaceFit Outfit Reminder Engine v6
═══════════════════════════════════════════════════════════════
FIXES in v6:
  1. WhatsApp: Log Twilio SID + status — catch silent delivery failures
  2. WhatsApp: Sandbox opt-in guard with clear error message
  3. Images: Removed fake Imgur Client IDs — only use real one from env
  4. Images: cloudinary fallback added (set CLOUDINARY_URL in env)
  5. Images: If no host available, skip media and send text-only (no crash)
  6. WhatsApp: Return False on any Twilio error instead of silently passing

TWILIO SANDBOX SETUP (MUST DO ONCE PER 72 HRS):
  User must WhatsApp "join <your-keyword>" to +14155238886
  Find keyword: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
"""

import os, base64, smtplib, logging
import requests as _req
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pymongo import MongoClient
from bson import ObjectId
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority"
)

# ── Imgur — ONLY use the real Client ID from env, no fake fallbacks ──────────
_IMGUR_REAL = os.getenv("IMGUR_CLIENT_ID", "")
IMGUR_CLIENT_IDS = [c for c in [_IMGUR_REAL] if c]

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

# Smart path resolution — works from services/ or root
_here = os.path.dirname(os.path.abspath(__file__))
_up   = os.path.join(_here, "..", "uploads")
_cwd  = os.path.join(os.getcwd(), "uploads")
FLASK_UPLOAD_DIR = _up if os.path.isdir(_up) else (_cwd if os.path.isdir(_cwd) else _up)

client        = MongoClient(MONGO_URI)
db            = client["facefit_ai"]
users_col     = db["users"]
reminders_col = db["outfit_reminders"]

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
scheduler.start()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("outfit_scheduler")

SLOT_EMOJI = {"top": "👕", "bottom": "👖", "shoes": "👟", "accessories": "💍", "ethnic": "🧣"}
_imgur_cache: dict = {}


# ════════════════════════════════════════════════════════════════════
#  IMAGE HOSTING — Imgur → Cloudinary → PUBLIC_BASE_URL fallback
# ════════════════════════════════════════════════════════════════════

def _local_path_from_url(image_url: str) -> str | None:
    """Resolve a /uploads/<file> URL to an absolute local path."""
    if not image_url:
        return None
    if image_url.startswith("/uploads/"):
        fname = image_url.split("/uploads/", 1)[-1]
        p = os.path.join(FLASK_UPLOAD_DIR, fname)
        return p if os.path.isfile(p) else None
    if os.path.isfile(image_url):
        return image_url
    return None


def _upload_to_imgur(image_url: str) -> str | None:
    """Upload a local file to Imgur and return a public https:// URL."""
    if not image_url:
        return None
    if image_url in _imgur_cache:
        return _imgur_cache[image_url]

    # Already a public URL — use directly (skip Imgur)
    if image_url.startswith("https://") and "127.0.0.1" not in image_url and "localhost" not in image_url:
        return image_url

    local_path = _local_path_from_url(image_url)
    if not local_path:
        log.warning(f"⚠️  Image not found on disk: {image_url}")
        return None

    if not IMGUR_CLIENT_IDS:
        log.warning("⚠️  No IMGUR_CLIENT_ID set — skipping Imgur upload")
        return None

    try:
        with open(local_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        log.warning(f"⚠️  Cannot read image file: {e}")
        return None

    for cid in IMGUR_CLIENT_IDS:
        try:
            r = _req.post(
                "https://api.imgur.com/3/image",
                headers={"Authorization": f"Client-ID {cid}"},
                data={"image": b64, "type": "base64"},
                timeout=20,
            )
            if r.status_code == 200:
                link = r.json()["data"]["link"].replace("http://", "https://")
                _imgur_cache[image_url] = link
                log.info(f"✅ Imgur upload OK: {os.path.basename(local_path)} → {link}")
                return link
            elif r.status_code == 429:
                log.warning(f"⚠️  Imgur rate-limited (Client-ID {cid[:6]}…)")
                continue
            elif r.status_code == 403:
                log.error(f"❌ Imgur Client-ID rejected (403) — check IMGUR_CLIENT_ID env var")
                continue
            else:
                log.warning(f"⚠️  Imgur error {r.status_code}: {r.text[:100]}")
                continue
        except Exception as e:
            log.warning(f"⚠️  Imgur request failed: {e}")
            continue

    log.warning("⚠️  All Imgur uploads failed")
    return None


def _upload_to_cloudinary(image_url: str) -> str | None:
    """
    Cloudinary fallback. Set CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
    or set CLOUDINARY_CLOUD_NAME + CLOUDINARY_API_KEY + CLOUDINARY_API_SECRET.
    """
    cloud_name  = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key     = os.getenv("CLOUDINARY_API_KEY")
    api_secret  = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        return None

    local_path = _local_path_from_url(image_url)
    if not local_path:
        return None

    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
        result = cloudinary.uploader.upload(local_path, folder="facefit_outfits")
        url = result.get("secure_url")
        if url:
            log.info(f"✅ Cloudinary upload OK: {url}")
            return url
    except Exception as e:
        log.warning(f"⚠️  Cloudinary upload failed: {e}")
    return None


def _get_public_url(image_url: str) -> str | None:
    """Try Imgur → Cloudinary → PUBLIC_BASE_URL in order."""
    if not image_url:
        return None

    # Already public
    if image_url.startswith("https://") and "127.0.0.1" not in image_url and "localhost" not in image_url:
        return image_url

    # Imgur
    r = _upload_to_imgur(image_url)
    if r:
        return r

    # Cloudinary
    r = _upload_to_cloudinary(image_url)
    if r:
        return r

    # PUBLIC_BASE_URL (ngrok / deployed server)
    if PUBLIC_BASE_URL and image_url.startswith("/"):
        fb = f"{PUBLIC_BASE_URL}{image_url}"
        if fb.startswith("https://"):
            log.info(f"ℹ️  Using PUBLIC_BASE_URL fallback: {fb}")
            return fb

    log.warning(f"⚠️  No public URL available for: {image_url}")
    return None


# ════════════════════════════════════════════════════════════════════
#  EMAIL
# ════════════════════════════════════════════════════════════════════

def _build_email_html(user_name, outfit, scheduled_dt, occasion):
    date_str   = scheduled_dt.strftime("%A, %d %B %Y at %I:%M %p")
    ai_tip     = outfit.get("styling_tip", "")
    items_html = items_text = ""

    for slot, item in outfit.get("items", {}).items():
        if not item:
            continue
        name  = item.get("item_name", "")
        color = item.get("color", "")
        emoji = SLOT_EMOJI.get(slot, "👔")
        pub   = _get_public_url(item.get("image_url", ""))

        img_block = (
            f'<img src="{pub}" width="80" height="80" style="width:80px;height:80px;'
            f'object-fit:cover;border-radius:8px;display:block;margin:0 auto 6px;"/>'
        ) if pub else (
            f'<div style="width:80px;height:80px;background:#f0e8d8;border-radius:8px;'
            f'display:inline-flex;align-items:center;justify-content:center;font-size:30px;'
            f'margin:0 auto 6px;">{emoji}</div>'
        )
        items_html += (
            f'<td style="text-align:center;padding:0 10px;vertical-align:top;min-width:90px;">'
            f'{img_block}'
            f'<div style="font-size:10px;color:#8a7a6a;text-transform:capitalize;">{slot}</div>'
            f'<div style="font-size:11px;color:#1a1208;font-weight:600;">{color}</div>'
            f'<div style="font-size:10px;color:#5a4a3a;">{name}</div></td>'
        )
        items_text += (
            f'<tr><td style="padding:3px 12px;font-size:13px;color:#5a4a3a;">'
            f'<b style="text-transform:capitalize">{slot}:</b>&nbsp;{color} {name}</td></tr>'
        )

    tip_html = (
        f'<tr><td style="padding:0 0 20px;">'
        f'<div style="border-left:3px solid #c8a96e;padding:10px 16px;background:#fffbf5;border-radius:0 6px 6px 0;">'
        f'<div style="font-size:10px;letter-spacing:0.15em;color:#c8a96e;text-transform:uppercase;margin-bottom:4px;">AI Styling Tip</div>'
        f'<div style="font-size:13px;color:#1a1208;line-height:1.6;">{ai_tip}</div></div></td></tr>'
    ) if ai_tip else ""

    score = outfit.get("color_score", "–")
    label = outfit.get("color_label", "")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f8f4ef;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td align="center" style="padding:32px 16px;">
<table width="560" cellpadding="0" cellspacing="0" border="0"
       style="background:#fff;border-radius:14px;overflow:hidden;max-width:560px;box-shadow:0 4px 24px rgba(0,0,0,0.10);">
<tr><td style="background:#1a1208;padding:26px 32px;">
  <div style="font-size:10px;letter-spacing:0.3em;color:#c8a96e;text-transform:uppercase;margin-bottom:6px;">FaceFit — AI Style Intelligence</div>
  <div style="font-size:26px;color:#f5ede0;font-weight:300;">Your Outfit Reminder 👔</div>
</td></tr>
<tr><td style="padding:28px 32px;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td style="padding-bottom:20px;">
  <p style="margin:0 0 6px;font-size:15px;color:#1a1208;">Hi <strong>{user_name}</strong>,</p>
  <p style="margin:0;font-size:13px;color:#5a4a3a;line-height:1.7;">Your <strong>{occasion}</strong> outfit for <strong>{date_str}</strong>:</p>
</td></tr>
<tr><td style="padding-bottom:20px;">
  <div style="background:#f8f4ef;border-radius:10px;padding:20px;text-align:center;">
    <div style="font-size:10px;letter-spacing:0.2em;color:#8a7a6a;text-transform:uppercase;margin-bottom:14px;">Your Outfit</div>
    <table cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;"><tr>{items_html}</tr></table>
  </div>
</td></tr>
<tr><td style="padding-bottom:20px;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#fafafa;border:1px solid #e8ddd0;border-radius:8px;padding:4px 0;">
    <tr><td style="padding:8px 12px 4px;"><span style="font-size:10px;letter-spacing:0.15em;color:#8a7a6a;text-transform:uppercase;">Outfit Details</span></td></tr>
    {items_text}
  </table>
</td></tr>
{tip_html}
<tr><td>
  <div style="background:#1a1208;border-radius:10px;padding:16px;text-align:center;">
    <div style="font-size:10px;color:#c8a96e;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:6px;">Color Harmony Score</div>
    <div style="font-size:22px;color:#f5ede0;">{score}/3 <span style="font-size:14px;color:#c8a96e;">{label}</span></div>
  </div>
</td></tr>
<tr><td style="padding-top:20px;text-align:center;"><p style="margin:0;font-size:11px;color:#b0a090;">Styled by FaceFit AI</p></td></tr>
</table></td></tr></table></td></tr></table>
</body></html>"""


def send_outfit_email(to_email, user_name, outfit, scheduled_dt, occasion):
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    if not gmail_user or not gmail_pass:
        log.warning("❌ Gmail not configured (GMAIL_USER / GMAIL_APP_PASSWORD missing)")
        return False
    try:
        msg            = MIMEMultipart("alternative")
        msg["Subject"] = f"👔 FaceFit: Your {occasion} outfit for {scheduled_dt.strftime('%d %b at %I:%M %p')}"
        msg["From"]    = f"FaceFit AI <{gmail_user}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(_build_email_html(user_name, outfit, scheduled_dt, occasion), "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(gmail_user, gmail_pass)
            s.sendmail(gmail_user, to_email, msg.as_string())
        log.info(f"✅ Email sent → {to_email}")
        return True
    except Exception as e:
        log.error(f"❌ Email error: {e}")
        return False


# ════════════════════════════════════════════════════════════════════
#  WHATSAPP  (Twilio Sandbox)
# ════════════════════════════════════════════════════════════════════

def send_outfit_whatsapp(to_phone: str, user_name: str, outfit: dict,
                         scheduled_dt: datetime, occasion: str) -> bool:
    """
    Send outfit reminder via WhatsApp using Twilio Sandbox.

    REQUIREMENTS:
      - TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in env
      - User must have opted in: send "join <keyword>" to +14155238886 on WhatsApp
        (Sandbox opt-in lasts 72 hours)
      - For images: set IMGUR_CLIENT_ID or CLOUDINARY_* env vars, or PUBLIC_BASE_URL
        pointing to a public https:// server

    Returns True only if Twilio accepts the message (SID received).
    Returns False on any error.
    """
    try:
        from twilio.rest import Client as TwilioClient
    except ImportError:
        log.error("❌ twilio package not installed — run: pip install twilio")
        return False

    sid  = os.getenv("TWILIO_ACCOUNT_SID")
    auth = os.getenv("TWILIO_AUTH_TOKEN")
    frm  = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if not sid or not auth:
        log.error("❌ TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not set in env")
        return False

    # Normalise phone → whatsapp:+91XXXXXXXXXX
    to_wa = f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone

    try:
        twilio  = TwilioClient(sid, auth)
        dt_str  = scheduled_dt.strftime("%d %b %Y at %I:%M %p")

        # ── Build text body ───────────────────────────────────────────────────
        lines = []
        for slot, item in outfit.get("items", {}).items():
            if item:
                emoji = SLOT_EMOJI.get(slot, "👔")
                lines.append(f"  {emoji} *{slot.title()}:* {item.get('color', '')} {item.get('item_name', '')}")

        body = (
            f"👔 *FaceFit Outfit Reminder*\n\n"
            f"Hi {user_name}! 🎉\n\n"
            f"Your *{occasion.title()}* outfit for *{dt_str}*:\n\n"
            + "\n".join(lines)
            + f"\n\n🎨 *Color Harmony:* {outfit.get('color_label', 'Good match')} ({outfit.get('color_score', '–')}/3)"
        )
        if outfit.get("styling_tip"):
            body += f"\n\n✨ *Tip:* {outfit['styling_tip']}"
        body += "\n\n_Powered by FaceFit AI_ 🤖"

        # ── Collect public image URLs ─────────────────────────────────────────
        image_urls = []
        for slot, item in outfit.get("items", {}).items():
            if item and item.get("image_url"):
                pub = _get_public_url(item["image_url"])
                if pub:
                    image_urls.append(pub)
            if len(image_urls) >= 3:
                break

        log.info(f"📤 WhatsApp → {to_phone} | {len(image_urls)} public image(s) | body={len(body)} chars")

        # ── Send first message (text + optional first image) ──────────────────
        # Send text first — guaranteed delivery
        msg = twilio.messages.create(body=body, from_=frm, to=to_wa)
        log.info(f"✅ WhatsApp text sent → SID: {msg.sid} | Status: {msg.status}")

        # Send images as separate messages ONLY if URLs are confirmed public
        for url in image_urls[:3]:
            try:
                img_msg = twilio.messages.create(
                    from_     = frm,
                    to        = to_wa,
                    media_url = [url],
                )
                log.info(f"   ↳ Image SID: {img_msg.sid} | Status: {img_msg.status}")
            except Exception as img_err:
                log.warning(f"   ↳ Image send skipped: {img_err}")
                # Don't fail — text already delivered

        log.info(f"✅ WhatsApp queued → SID: {msg.sid} | Status: {msg.status} | To: {to_phone}")

        # ── Send remaining images as separate messages ─────────────────────────
        for url in image_urls[1:]:
            extra = twilio.messages.create(from_=frm, to=to_wa, media_url=[url])
            log.info(f"   ↳ Extra image SID: {extra.sid} | Status: {extra.status}")

        # Warn if status is already failed
        if msg.status in ("failed", "undelivered"):
            log.error(
                f"❌ WhatsApp delivery failed immediately — Status: {msg.status} | "
                f"ErrorCode: {msg.error_code} | ErrorMessage: {msg.error_message}\n"
                f"   ➜ Check if {to_phone} has opted-in to Sandbox "
                f"by sending 'join <keyword>' to +14155238886 on WhatsApp"
            )
            return False

        return True

    except Exception as e:
        err = str(e)

        # Sandbox opt-in error (Error 21608)
        if "21608" in err or "not opted" in err.lower():
            log.error(
                f"❌ SANDBOX OPT-IN REQUIRED for {to_phone}\n"
                f"   ➜ User must send 'join <keyword>' to WhatsApp +14155238886\n"
                f"   ➜ Find keyword: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn\n"
                f"   ➜ Opt-in expires after 72 hours — user must rejoin"
            )
        # Invalid 'From' number (wrong sandbox number)
        elif "21606" in err:
            log.error(
                f"❌ Invalid TWILIO_WHATSAPP_FROM='{frm}'\n"
                f"   ➜ For Sandbox use exactly: whatsapp:+14155238886"
            )
        # Invalid 'To' number
        elif "21211" in err or "21614" in err:
            log.error(
                f"❌ Invalid phone number: {to_phone}\n"
                f"   ➜ Must be in format +91XXXXXXXXXX"
            )
        # Media URL not accessible
        elif "21623" in err or "media" in err.lower():
            log.error(
                f"❌ Media URL not publicly accessible\n"
                f"   ➜ Set IMGUR_CLIENT_ID, CLOUDINARY_* or PUBLIC_BASE_URL (https:// only)\n"
                f"   ➜ Twilio cannot fetch images from localhost or private IPs"
            )
        else:
            log.error(f"❌ WhatsApp error: {e}")

        return False


# ════════════════════════════════════════════════════════════════════
#  GOOGLE CALENDAR
# ════════════════════════════════════════════════════════════════════

def create_google_calendar_event(user_email, user_name, outfit, scheduled_dt, occasion):
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
    except ImportError:
        return None

    SCOPES     = ["https://www.googleapis.com/auth/calendar"]
    token_path = os.getenv("GOOGLE_TOKEN_JSON", "token.json")
    if not os.path.exists(token_path):
        return None

    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    except Exception:
        return None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_path, "w") as f:
                    f.write(creds.to_json())
            except Exception as e:
                log.warning(f"Token refresh failed: {e}")
                return None
        else:
            return None

    try:
        svc  = build("calendar", "v3", credentials=creds)
        desc = (
            f"FaceFit AI — {occasion.title()} Outfit\n\n"
            + "\n".join(
                f"• {s.title()}: {i.get('color', '')} {i.get('item_name', '')}"
                for s, i in outfit.get("items", {}).items() if i
            )
            + f"\n\nColor: {outfit.get('color_label', '')} ({outfit.get('color_score', '–')}/3)"
            + f"\nTip: {outfit.get('styling_tip', '')}"
        )
        if scheduled_dt.tzinfo is None:
            import pytz
            scheduled_dt = pytz.timezone("Asia/Kolkata").localize(scheduled_dt)
        end_dt = scheduled_dt.replace(hour=min(scheduled_dt.hour + 1, 23))
        created = svc.events().insert(
            calendarId   = "primary",
            sendUpdates  = "all",
            body={
                "summary":     f"👔 FaceFit: {occasion.title()} Outfit",
                "description": desc,
                "start": {"dateTime": scheduled_dt.isoformat(), "timeZone": "Asia/Kolkata"},
                "end":   {"dateTime": end_dt.isoformat(),       "timeZone": "Asia/Kolkata"},
                "attendees": [{"email": user_email}],
                "reminders": {"useDefault": False, "overrides": [
                    {"method": "email",  "minutes": 60},
                    {"method": "popup",  "minutes": 30},
                ]},
            }
        ).execute()
        link = created.get("htmlLink")
        log.info(f"✅ Calendar event: {link}")
        return link
    except Exception as e:
        if "accessNotConfigured" in str(e):
            log.error("❌ Enable Google Calendar API at: https://console.developers.google.com")
        else:
            log.error(f"❌ Calendar error: {e}")
        return None


# ════════════════════════════════════════════════════════════════════
#  SCHEDULER ENGINE
# ════════════════════════════════════════════════════════════════════

def _fire_reminder(reminder_id: str):
    doc = reminders_col.find_one({"_id": ObjectId(reminder_id)})
    if not doc:
        log.warning(f"Reminder {reminder_id} not found in DB")
        return

    results      = {"email": False, "whatsapp": False, "calendar": None}
    email        = doc.get("email")
    phone        = doc.get("phone")
    outfit       = doc["outfit"]
    occasion     = doc.get("occasion", "event")
    scheduled_dt = doc["scheduled_at"]
    user_name    = doc["user_name"]

    if email:
        results["email"]    = send_outfit_email(email, user_name, outfit, scheduled_dt, occasion)
        results["calendar"] = create_google_calendar_event(email, user_name, outfit, scheduled_dt, occasion)

    if phone:
        results["whatsapp"] = send_outfit_whatsapp(phone, user_name, outfit, scheduled_dt, occasion)

    reminders_col.update_one(
        {"_id": ObjectId(reminder_id)},
        {"$set": {"fired": True, "fired_at": datetime.utcnow(), "results": results}},
    )
    log.info(f"✅ Reminder fired {reminder_id}: email={results['email']} | whatsapp={results['whatsapp']} | calendar={results['calendar']}")


def schedule_outfit_reminder(user_id, user_name, email, phone, outfit, occasion, scheduled_at):
    import pytz
    ist = pytz.timezone("Asia/Kolkata")
    if scheduled_at.tzinfo is None:
        scheduled_at = ist.localize(scheduled_at)

    doc = {
        "user_id": user_id, "user_name": user_name, "email": email, "phone": phone,
        "outfit": outfit, "occasion": occasion, "scheduled_at": scheduled_at,
        "created_at": datetime.utcnow(), "fired": False,
    }
    result = reminders_col.insert_one(doc)
    rid    = str(result.inserted_id)

    cal_link = None
    if email:
        try:
            cal_link = create_google_calendar_event(email, user_name, outfit, scheduled_at, occasion)
            if cal_link:
                reminders_col.update_one(
                    {"_id": result.inserted_id},
                    {"$set": {"calendar_link": cal_link}},
                )
        except Exception as e:
            log.error(f"Calendar (non-fatal): {e}")

    now = datetime.now(ist)
    if scheduled_at > now:
        scheduler.add_job(
            _fire_reminder,
            trigger        = DateTrigger(run_date=scheduled_at),
            args           = [rid],
            id             = f"outfit_{rid}",
            replace_existing = True,
        )
        log.info(f"✅ Scheduled for {scheduled_at} IST (id: {rid})")
    else:
        log.info(f"ℹ️  scheduled_at is in the past — firing immediately (id: {rid})")
        _fire_reminder(rid)

    return {
        "reminder_id":  rid,
        "calendar_link": cal_link,
        "scheduled_at":  scheduled_at.isoformat(),
        "status":        "scheduled",
    }


def get_user_reminders(user_id: str) -> list:
    docs = list(reminders_col.find({"user_id": user_id}, sort=[("scheduled_at", -1)]).limit(50))
    for d in docs:
        d["_id"] = str(d["_id"])
        for f in ("scheduled_at", "created_at", "fired_at"):
            if isinstance(d.get(f), datetime):
                d[f] = d[f].isoformat()
    return docs


def delete_reminder(reminder_id: str) -> bool:
    try:
        try:
            scheduler.remove_job(f"outfit_{reminder_id}")
        except Exception:
            pass
        return reminders_col.delete_one({"_id": ObjectId(reminder_id)}).deleted_count > 0
    except Exception as e:
        log.error(f"Delete error: {e}")
        return False


def save_user_contact(user_id, email, phone):
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"email": email, "phone": phone, "updated_at": datetime.utcnow()}},
        upsert=True,
    )


def get_user_contact(user_id):
    doc = users_col.find_one({"user_id": user_id})
    return {"email": doc.get("email", ""), "phone": doc.get("phone", "")} if doc else {"email": "", "phone": ""}