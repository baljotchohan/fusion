# core/firestore_profile.py
"""
Firestore user profile helpers — uses the firebase-admin SDK already
initialized in core/auth.py. No extra dependencies needed.

Collection: users/{uid}
Fields: displayName, email, photoURL, lastSeen, totalDeals, createdAt
"""
import logging
from typing import Optional

logger = logging.getLogger("fusion.firestore")


def _db():
    from firebase_admin import firestore
    return firestore.client()


def upsert_user(uid: str, name: Optional[str], email: Optional[str], photo: Optional[str]) -> None:
    """Create or update user doc on login / deal trigger."""
    try:
        from firebase_admin import firestore
        db = _db()
        ref = db.collection("users").document(uid)
        doc = ref.get()
        data = {
            "displayName": name,
            "email": email,
            "photoURL": photo,
            "lastSeen": firestore.SERVER_TIMESTAMP,
        }
        if not doc.exists:
            data["createdAt"] = firestore.SERVER_TIMESTAMP
            data["totalDeals"] = 0
        ref.set(data, merge=True)
    except Exception as e:
        logger.warning(f"Firestore upsert_user failed (non-fatal): {e}")


def increment_deal_count(uid: str) -> None:
    """Increment totalDeals counter when a deal is triggered."""
    try:
        from firebase_admin import firestore
        _db().collection("users").document(uid).set(
            {"totalDeals": firestore.Increment(1)}, merge=True
        )
    except Exception as e:
        logger.warning(f"Firestore increment_deal_count failed (non-fatal): {e}")


def get_user(uid: str) -> Optional[dict]:
    """Fetch user profile doc. Returns None if not found or Firestore unavailable."""
    try:
        doc = _db().collection("users").document(uid).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.warning(f"Firestore get_user failed (non-fatal): {e}")
        return None
