from app.config import INITIAL_BALANCE
from app.database import SessionLocal
from app.migrations import init_db
from app.models import User
from app.referral_service import ensure_referral_code


SEED_USERS = [
    {"telegram_id": "1001", "username": "demo_user", "first_name": "Demo"},
    {"telegram_id": "1002", "username": "alina", "first_name": "Алина"},
    {"telegram_id": "1003", "username": "maxim", "first_name": "Максим"},
    {"telegram_id": "1004", "username": "vera", "first_name": "Вера"},
    {"telegram_id": "1005", "username": "timur", "first_name": "Тимур"},
    {"telegram_id": "1006", "username": "sofia", "first_name": "София"},
]

# Stage 6 future-token note: do not seed this automatically until a real
# Jetton Master address exists. It documents the intended Asset shape for devs.
FUTURE_TUDA_ASSET_EXAMPLE = {
    "symbol": "TUDA",
    "name": "Tuda Token",
    "asset_type": "jetton",
    "network": "ton_testnet",
    "contract_address": "<Jetton Master address>",
    "decimals": 9,
    "is_active": True,
}


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        created = 0
        for item in SEED_USERS:
            user = db.query(User).filter(User.telegram_id == item["telegram_id"]).first()
            if user:
                continue
            user = User(
                telegram_id=item["telegram_id"],
                username=item["username"],
                first_name=item["first_name"],
                balance=INITIAL_BALANCE,
                karma=0,
                total_sent=0,
                total_received=0,
            )
            db.add(user)
            db.flush()
            ensure_referral_code(db, user)
            created += 1
        db.commit()
        print(f"Seed complete. Created users: {created}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
