"""
saved_products_routes.py — FIXED: Alert on ANY price drop (even ₹1) via WhatsApp + Email
"""

from flask import Blueprint, request, jsonify
from pymongo import MongoClient, ASCENDING
from apscheduler.schedulers.background import BackgroundScheduler
import os, uuid, re, requests, logging, smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority",
)
_client   = MongoClient(MONGO_URI)
_db       = _client["facefit_ai"]
saved_col = _db["saved_products"]
users_col = _db["users"]

try:
    saved_col.create_index([("userId", ASCENDING), ("active", ASCENDING)])
    saved_col.create_index([("product_id", ASCENDING)], unique=True)
except Exception:
    pass

SERPER_KEYS = [
    os.getenv("SERPER_API_KEY_1", "4155943b29f00e53da61bc5c94bb9e7192ae8ef4"),
    os.getenv("SERPER_API_KEY_2", "f6110be0a8db43231ccb3d7760579ba5a01132aa"),
]

TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM  = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
GMAIL_USER   = os.getenv("GMAIL_USER", "")
GMAIL_PASS   = os.getenv("GMAIL_APP_PASSWORD", "")

log = logging.getLogger("price_drop")
saved_products_bp = Blueprint("saved_products", __name__)


def _parse_price(raw) -> float | None:
    if raw is None:
        return None
    s = str(raw).replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    try:
        return float(re.sub(r"[^\d.]", "", s))
    except Exception:
        return None


def _fetch_current_price(title: str, platform: str) -> float | None:
    url = "https://google.serper.dev/shopping"
    for key in SERPER_KEYS:
        try:
            resp = requests.post(
                url,
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": title, "gl": "in", "hl": "en", "num": 5},
                timeout=12,
            )
            if resp.status_code in (402, 429):
                continue
            resp.raise_for_status()
            items = resp.json().get("shopping", [])
            for item in items:
                price = _parse_price(item.get("price"))
                if price and price > 0:
                    return price
        except Exception as e:
            log.warning(f"Serper price check error: {e}")
    return None


def _send_whatsapp_alert(phone: str, user_name: str, product: dict, new_price: float):
    if not TWILIO_SID or not TWILIO_TOKEN:
        log.warning("Twilio not configured — skipping WhatsApp alert")
        return False
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        original = product.get("original_price", 0)
        drop_amt = int(original - new_price)
        drop_pct = round((original - new_price) / original * 100, 1) if original > 0 else 0

        body = (
            f"🔔 *Price Drop Alert — FaceFit*\n\n"
            f"Hi {user_name}! Great news — a price just dropped!\n\n"
            f"📦 *{product['title'][:60]}*\n"
            f"💰 Was: ₹{int(original)}  →  Now: ₹{int(new_price)}\n"
            f"💸 You save: ₹{drop_amt} ({drop_pct}% off)\n\n"
            f"🛍 Shop now: {product['url']}\n\n"
            f"_FaceFit — AI Style Intelligence_"
        )

        # Normalize phone
        to_phone = phone if phone.startswith("+") else f"+91{phone.lstrip('91')}"
        to_wa = f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone

        msg = client.messages.create(body=body, from_=TWILIO_FROM, to=to_wa)
        log.info(f"✅ WhatsApp alert sent to {phone} — SID: {msg.sid}")
        return True
    except Exception as e:
        log.error(f"WhatsApp alert failed: {e}")
        return False


def _send_email_alert(email: str, user_name: str, product: dict, new_price: float):
    if not GMAIL_USER or not GMAIL_PASS:
        log.warning("Gmail not configured — skipping email alert")
        return False
    try:
        original = product.get("original_price", 0)
        drop_amt = int(original - new_price)
        drop_pct = round((original - new_price) / original * 100, 1) if original > 0 else 0
        old_p    = int(original)
        new_p    = int(new_price)

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f8f4ef;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="padding:32px 16px;">
<table width="520" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.10);">
  <tr><td style="background:#1a1208;padding:22px 28px;">
    <div style="font-size:10px;letter-spacing:.3em;color:#c8a96e;text-transform:uppercase;margin-bottom:5px;">FaceFit — Price Intelligence</div>
    <div style="font-size:22px;color:#f5ede0;font-weight:300;">🔔 Price Drop Alert</div>
  </td></tr>
  <tr><td style="padding:28px;">
    <p style="margin:0 0 6px;font-size:15px;color:#1a1208;">Hi <strong>{user_name}</strong>!</p>
    <p style="margin:0 0 20px;font-size:13px;color:#5a4a3a;line-height:1.7;">
      A product you're tracking just dropped in price. Grab it before it goes back up!
    </p>
    <div style="background:#fffbf5;border:1px solid #e8ddd0;border-radius:10px;padding:20px;margin-bottom:20px;">
      <div style="font-size:14px;font-weight:600;color:#1a1208;margin-bottom:12px;line-height:1.4;">{product['title'][:80]}</div>
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
        <span style="font-size:13px;color:#888;text-decoration:line-through;">₹{old_p}</span>
        <span style="font-size:26px;font-weight:700;color:#2d7a4f;">₹{new_p}</span>
        <span style="background:#eafaf1;color:#2d7a4f;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;">
          ↓ ₹{drop_amt} off ({drop_pct}%)
        </span>
      </div>
    </div>
    <a href="{product['url']}" style="display:inline-block;background:#1a1208;color:#c8a96e;padding:14px 28px;border-radius:8px;text-decoration:none;font-size:11px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;">
      Shop Now →
    </a>
    <p style="color:#aaa;font-size:11px;margin-top:20px;line-height:1.6;">
      You saved this product on FaceFit AI. Alerts fire for every price drop — even ₹1.<br/>
      Remove it from your saved products to stop alerts.
    </p>
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔔 Price Drop! ₹{drop_amt} off — {product['title'][:45]}"
        msg["From"]    = f"FaceFit AI <{GMAIL_USER}>"
        msg["To"]      = email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, email, msg.as_string())
        log.info(f"✅ Email alert sent to {email}")
        return True
    except Exception as e:
        log.error(f"Email alert failed: {e}")
        return False


# ── PRICE DROP CHECK — triggers on ANY drop (even ₹1) ────────────────────────

def check_all_price_drops():
    log.info("⏰ Price drop check starting...")
    products = list(saved_col.find({"active": True}))
    log.info(f"   Checking {len(products)} saved products")

    for p in products:
        try:
            new_price = _fetch_current_price(p["title"], p.get("platform", ""))
            if new_price is None:
                continue

            original  = p.get("original_price") or 0
            last_seen = p.get("last_checked_price") or original

            update = {
                "last_checked_price": new_price,
                "last_checked_at":    datetime.utcnow(),
                "lowest_seen_price":  min(new_price, p.get("lowest_seen_price", new_price)),
            }

            # Reset alert_sent if price recovered above last alerted price
            if p.get("alert_sent") and new_price >= (p.get("alert_sent_price") or 0):
                update["alert_sent"]       = False
                update["alert_sent_price"] = None

            saved_col.update_one({"product_id": p["product_id"]}, {"$set": update})

            if original <= 0:
                continue

            # ── FIRE ALERT ON ANY PRICE DROP (even ₹1) ───────────────────────
            # Compare against last_seen (not original) to catch any new drop
            if new_price >= last_seen:
                continue  # price went up or stayed same — no alert

            # Already alerted for this exact price? Skip
            if p.get("alert_sent") and p.get("alert_sent_price") == new_price:
                continue

            drop_amt = last_seen - new_price
            if drop_amt < 1:
                continue  # less than ₹1 — ignore floating point noise

            log.info(f"💸 Price drop: {p['title'][:50]} — ₹{int(last_seen)} → ₹{int(new_price)} (₹{int(drop_amt)} off)")

            user = users_col.find_one({"userId": p["userId"]})
            if not user:
                continue

            user_name = p.get("userId", "Friend")
            alerted   = False

            if user.get("email"):
                sent = _send_email_alert(user["email"], user_name, {**p, "original_price": last_seen}, new_price)
                if sent:
                    alerted = True

            if user.get("phone"):
                sent = _send_whatsapp_alert(user["phone"], user_name, {**p, "original_price": last_seen}, new_price)
                if sent:
                    alerted = True

            if alerted:
                saved_col.update_one(
                    {"product_id": p["product_id"]},
                    {"$set": {
                        "alert_sent":       True,
                        "alert_sent_price": new_price,
                        "alert_sent_at":    datetime.utcnow(),
                    }},
                )

        except Exception as e:
            log.error(f"Price check error for {p.get('title', '?')}: {e}")

    log.info("✅ Price drop check complete")


# ── Scheduler — every hour during daytime ─────────────────────────────────────
_scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
# Run every hour from 8 AM to 11 PM IST so users get alerts throughout the day
for hour in range(8, 24):
    _scheduler.add_job(
        check_all_price_drops,
        trigger="cron",
        hour=hour,
        minute=0,
        id=f"price_check_{hour}",
        replace_existing=True,
    )
_scheduler.start()
log.info("✅ Price drop scheduler started — runs HOURLY 8AM–11PM IST (triggers on any ₹1+ drop)")


# ── ROUTES ────────────────────────────────────────────────────────────────────

@saved_products_bp.route("/products/save", methods=["POST"])
def save_product():
    data = request.json
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    user_id   = data.get("userId", "").strip()
    title     = data.get("title", "").strip()
    url       = data.get("url", "").strip()
    platform  = data.get("platform", "").strip()
    raw_price = data.get("price")
    thumbnail = data.get("thumbnail", "")

    if not user_id or not title or not url:
        return jsonify({"error": "userId, title and url are required"}), 400

    price = _parse_price(raw_price)

    existing = saved_col.find_one({"userId": user_id, "url": url})
    if existing:
        return jsonify({"success": True, "product_id": existing["product_id"], "already_saved": True}), 200

    product_id = uuid.uuid4().hex
    doc = {
        "product_id":         product_id,
        "userId":             user_id,
        "title":              title,
        "url":                url,
        "thumbnail":          thumbnail,
        "platform":           platform,
        "original_price":     price,
        "last_checked_price": price,
        "lowest_seen_price":  price,
        "saved_at":           datetime.utcnow(),
        "last_checked_at":    datetime.utcnow(),
        "alert_sent":         False,
        "alert_sent_price":   None,
        "active":             True,
    }
    saved_col.insert_one(doc)

    return jsonify({
        "success":    True,
        "product_id": product_id,
        "message":    "Product saved! You'll get WhatsApp + email alerts for any price drop — even ₹1.",
    }), 201


@saved_products_bp.route("/products/saved/<user_id>", methods=["GET"])
def get_saved(user_id):
    docs = list(saved_col.find(
        {"userId": user_id, "active": True},
        {"_id": 0},
        sort=[("saved_at", -1)],
    ))
    for d in docs:
        orig = d.get("original_price") or 0
        curr = d.get("last_checked_price") or orig
        d["drop_pct"]  = round((orig - curr) / orig * 100, 1) if orig > 0 else 0
        d["drop_amount"] = int(orig - curr) if orig > curr else 0
        for f in ("saved_at", "last_checked_at", "alert_sent_at"):
            if d.get(f):
                d[f] = d[f].isoformat()
    return jsonify({"products": docs, "total": len(docs)}), 200


@saved_products_bp.route("/products/saved/<product_id>", methods=["DELETE"])
def unsave_product(product_id):
    result = saved_col.update_one(
        {"product_id": product_id},
        {"$set": {"active": False}},
    )
    if result.modified_count:
        return jsonify({"success": True}), 200
    return jsonify({"error": "Product not found"}), 404


@saved_products_bp.route("/products/price-check", methods=["POST"])
def manual_price_check():
    product_id = (request.json or {}).get("product_id")
    if not product_id:
        return jsonify({"error": "product_id required"}), 400

    p = saved_col.find_one({"product_id": product_id})
    if not p:
        return jsonify({"error": "Product not found"}), 404

    new_price = _fetch_current_price(p["title"], p.get("platform", ""))
    if new_price is None:
        return jsonify({
            "message": "Could not fetch current price",
            "current_price": p.get("last_checked_price"),
        }), 200

    orig      = p.get("original_price") or 0
    last_seen = p.get("last_checked_price") or orig
    drop_amt  = int(last_seen - new_price) if last_seen > new_price else 0
    drop_pct  = round((last_seen - new_price) / last_seen * 100, 1) if last_seen > 0 else 0

    saved_col.update_one(
        {"product_id": product_id},
        {"$set": {
            "last_checked_price": new_price,
            "last_checked_at":    datetime.utcnow(),
            "lowest_seen_price":  min(new_price, p.get("lowest_seen_price", new_price)),
        }},
    )

    # Fire alert immediately if price dropped
    if drop_amt >= 1 and not (p.get("alert_sent") and p.get("alert_sent_price") == new_price):
        user = users_col.find_one({"userId": p["userId"]})
        if user:
            if user.get("email"):
                _send_email_alert(user["email"], p["userId"], {**p, "original_price": last_seen}, new_price)
            if user.get("phone"):
                _send_whatsapp_alert(user["phone"], p["userId"], {**p, "original_price": last_seen}, new_price)

    return jsonify({
        "original_price": orig,
        "last_seen_price": last_seen,
        "current_price":  new_price,
        "drop_amount":    drop_amt,
        "drop_pct":       drop_pct,
        "alert_fired":    drop_amt >= 1 ,
    }), 200