import hashlib

from sqlalchemy import text

from . import models
from .config import (
    SEED_TDSD_ASSET,
    TDSD_ASSET_NAME,
    TDSD_ASSET_SYMBOL,
    TDSD_DECIMALS,
    TDSD_DEPOSITS_ENABLED,
    TDSD_JETTON_MASTER_ADDRESS,
    TDSD_NETWORK,
)
from .database import engine


def init_db() -> None:
    models.Base.metadata.create_all(bind=engine)
    ensure_user_wallet_columns()
    ensure_referral_schema()
    ensure_ton_deposit_columns()
    ensure_asset_columns()
    ensure_asset_economy()
    ensure_asset_gift_columns()
    ensure_asset_deposit_columns()


def ensure_user_wallet_columns() -> None:
    # SQLite MVP migration: add nullable columns without touching existing rows.
    with engine.begin() as connection:
        users_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'users'",
            )
        ).first()
        if not users_table:
            return

        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(users)")).all()
        }
        statements = []
        if "reputation" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN reputation INTEGER DEFAULT 0"
            )
        if "risk_score" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN risk_score INTEGER DEFAULT 0"
            )
        if "community_weight" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN community_weight INTEGER DEFAULT 0"
            )
        if "ton_balance" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN ton_balance NUMERIC(18, 9) DEFAULT 0"
            )
        if "ton_balance_nano" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN ton_balance_nano BIGINT DEFAULT 0"
            )
        if "ton_wallet_address" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN ton_wallet_address VARCHAR(128)"
            )
        if "ton_wallet_connected_at" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN ton_wallet_connected_at DATETIME"
            )
        if "photo_url" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN photo_url VARCHAR(512)"
            )
        if "last_active_at" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN last_active_at DATETIME"
            )

        for statement in statements:
            connection.execute(text(statement))

        updated_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(users)")).all()
        }
        if "ton_balance" in updated_columns and "ton_balance_nano" in updated_columns:
            connection.execute(
                text(
                    "UPDATE users "
                    "SET ton_balance_nano = CAST(ROUND(COALESCE(ton_balance, 0) * 1000000000) AS INTEGER) "
                    "WHERE COALESCE(ton_balance_nano, 0) = 0 "
                    "AND COALESCE(ton_balance, 0) != 0"
                )
            )


REFERRAL_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _migration_referral_code(user_id: int, telegram_id: str | None) -> str:
    seed = f"{user_id}:{telegram_id or ''}:tuda-suda-referral".encode()
    number = int.from_bytes(hashlib.sha256(seed).digest()[:8], "big")
    chars = []
    for _ in range(8):
        number, index = divmod(number, len(REFERRAL_CODE_ALPHABET))
        chars.append(REFERRAL_CODE_ALPHABET[index])
    return "".join(chars)


def ensure_referral_schema() -> None:
    with engine.begin() as connection:
        users_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'users'",
            )
        ).first()
        if not users_table:
            return

        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(users)")).all()
        }
        statements = []
        if "referral_code" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN referral_code VARCHAR(16)"
            )
        if "referred_by_user_id" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN referred_by_user_id INTEGER"
            )
        if "referred_at" not in columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN referred_at DATETIME"
            )

        for statement in statements:
            connection.execute(text(statement))

        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS referral_rewards ("
                "id INTEGER PRIMARY KEY, "
                "referrer_user_id INTEGER NOT NULL, "
                "referred_user_id INTEGER NOT NULL, "
                "purchase_id INTEGER, "
                "purchase_amount_tdsd BIGINT NOT NULL, "
                "reward_amount_tdsd BIGINT NOT NULL, "
                "reward_percent NUMERIC(8, 4) DEFAULT 0, "
                "status VARCHAR(32) DEFAULT 'pending', "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
                "credited_at DATETIME, "
                "FOREIGN KEY(referrer_user_id) REFERENCES users(id), "
                "FOREIGN KEY(referred_user_id) REFERENCES users(id), "
                "UNIQUE(purchase_id)"
                ")"
            )
        )

        existing_codes = {
            row[0]
            for row in connection.execute(
                text("SELECT referral_code FROM users WHERE referral_code IS NOT NULL")
            ).all()
        }
        rows = connection.execute(
            text(
                "SELECT id, telegram_id FROM users "
                "WHERE referral_code IS NULL OR referral_code = ''"
            )
        ).all()
        for row in rows:
            user_id, telegram_id = row[0], row[1]
            code = _migration_referral_code(user_id, telegram_id)
            suffix = 1
            while code in existing_codes:
                code = _migration_referral_code(user_id + suffix, telegram_id)
                suffix += 1
            existing_codes.add(code)
            connection.execute(
                text("UPDATE users SET referral_code = :code WHERE id = :user_id"),
                {"code": code, "user_id": user_id},
            )

        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_referral_code_unique "
                "ON users(referral_code)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_users_referred_by_user_id "
                "ON users(referred_by_user_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_referral_rewards_referrer_user_id "
                "ON referral_rewards(referrer_user_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_referral_rewards_referred_user_id "
                "ON referral_rewards(referred_user_id)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_referral_rewards_purchase_id_unique "
                "ON referral_rewards(purchase_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_referral_rewards_status "
                "ON referral_rewards(status)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_referral_rewards_created_at "
                "ON referral_rewards(created_at)"
            )
        )


def ensure_ton_deposit_columns() -> None:
    with engine.begin() as connection:
        deposits_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'ton_deposits'",
            )
        ).first()
        if not deposits_table:
            return

        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(ton_deposits)")).all()
        }
        statements = []
        if "target_wallet_address" not in columns:
            statements.append(
                "ALTER TABLE ton_deposits ADD COLUMN target_wallet_address VARCHAR(128)"
            )
        if "network" not in columns:
            statements.append(
                "ALTER TABLE ton_deposits ADD COLUMN network VARCHAR(32) DEFAULT 'testnet'"
            )
        if "comment" not in columns:
            statements.append(
                "ALTER TABLE ton_deposits ADD COLUMN comment VARCHAR(160)"
            )
        if "amount_nano" not in columns:
            statements.append(
                "ALTER TABLE ton_deposits ADD COLUMN amount_nano BIGINT DEFAULT 0"
            )
        if "failed_reason" not in columns:
            statements.append(
                "ALTER TABLE ton_deposits ADD COLUMN failed_reason VARCHAR(500)"
            )

        for statement in statements:
            connection.execute(text(statement))


def ensure_asset_columns() -> None:
    with engine.begin() as connection:
        assets_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'assets'",
            )
        ).first()
        if not assets_table:
            return

        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(assets)")).all()
        }
        statements = []
        if "provider_key" not in columns:
            statements.append("ALTER TABLE assets ADD COLUMN provider_key VARCHAR(64)")
        if "metadata_json" not in columns:
            statements.append("ALTER TABLE assets ADD COLUMN metadata_json TEXT")
        if "display_order" not in columns:
            statements.append(
                "ALTER TABLE assets ADD COLUMN display_order INTEGER DEFAULT 0"
            )

        for statement in statements:
            connection.execute(text(statement))


def ensure_asset_economy() -> None:
    # Stage 4 preparation: seed native TON and mirror legacy user.ton_balance_nano.
    with engine.begin() as connection:
        assets_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'assets'",
            )
        ).first()
        balances_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'asset_balances'",
            )
        ).first()
        ledger_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'asset_ledger_entries'",
            )
        ).first()
        users_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'users'",
            )
        ).first()
        if not assets_table or not balances_table or not ledger_table:
            return

        connection.execute(
            text(
                "INSERT INTO assets "
                "(symbol, name, asset_type, network, decimals, contract_address, "
                "provider_key, metadata_json, display_order, is_active, created_at) "
                "SELECT 'TON', 'Toncoin', 'native', 'ton_testnet', 9, NULL, "
                "'ton_native', NULL, 0, 1, CURRENT_TIMESTAMP "
                "WHERE NOT EXISTS (SELECT 1 FROM assets WHERE symbol = 'TON')"
            )
        )
        connection.execute(
            text(
                "UPDATE assets "
                "SET provider_key = COALESCE(provider_key, 'ton_native'), "
                "display_order = COALESCE(display_order, 0) "
                "WHERE symbol = 'TON'"
            )
        )
        if SEED_TDSD_ASSET:
            tdsd_provider_key = "jetton" if TDSD_DEPOSITS_ENABLED else "tdsd_fixed_price"
            tdsd_fixed_price_mode = not TDSD_DEPOSITS_ENABLED
            connection.execute(
                text(
                    "INSERT INTO assets "
                    "(symbol, name, asset_type, network, decimals, contract_address, "
                    "provider_key, metadata_json, display_order, is_active, created_at) "
                    "SELECT :symbol, :name, 'jetton', :network, :decimals, :contract_address, "
                    ":provider_key, '{\"stage\":\"production-ready\",\"token\":\"TDSD\"}', 10, "
                    "CASE WHEN :fixed_price_mode = 1 OR :contract_address != '' THEN 1 ELSE 0 END, CURRENT_TIMESTAMP "
                    "WHERE NOT EXISTS (SELECT 1 FROM assets WHERE symbol = :symbol)"
                ),
                {
                    "symbol": TDSD_ASSET_SYMBOL,
                    "name": TDSD_ASSET_NAME,
                    "network": TDSD_NETWORK,
                    "decimals": TDSD_DECIMALS,
                    "contract_address": TDSD_JETTON_MASTER_ADDRESS,
                    "provider_key": tdsd_provider_key,
                    "fixed_price_mode": int(tdsd_fixed_price_mode),
                },
            )
            connection.execute(
                text(
                    "UPDATE assets "
                    "SET provider_key = :provider_key, "
                    "display_order = COALESCE(display_order, 10), "
                    "contract_address = CASE "
                    "  WHEN :contract_address = '' THEN contract_address "
                    "  ELSE :contract_address "
                    "END, "
                    "is_active = CASE "
                    "  WHEN :fixed_price_mode = 1 THEN 1 "
                    "  WHEN :contract_address = '' THEN is_active "
                    "  ELSE 1 "
                    "END "
                    "WHERE symbol = :symbol"
                ),
                {
                    "symbol": TDSD_ASSET_SYMBOL,
                    "contract_address": TDSD_JETTON_MASTER_ADDRESS,
                    "provider_key": tdsd_provider_key,
                    "fixed_price_mode": int(tdsd_fixed_price_mode),
                },
            )
        ton_asset = connection.execute(
            text("SELECT id FROM assets WHERE symbol = 'TON'")
        ).first()
        if not ton_asset or not users_table:
            return

        ton_asset_id = ton_asset[0]
        connection.execute(
            text(
                "INSERT INTO asset_balances "
                "(user_id, asset_id, balance_units, created_at, updated_at) "
                "SELECT users.id, :asset_id, COALESCE(users.ton_balance_nano, 0), "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
                "FROM users "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM asset_balances "
                "  WHERE asset_balances.user_id = users.id "
                "  AND asset_balances.asset_id = :asset_id"
                ")"
            ),
            {"asset_id": ton_asset_id},
        )
        connection.execute(
            text(
                "INSERT INTO asset_ledger_entries "
                "(user_id, asset_id, entry_type, amount_units, direction, "
                "related_entity_type, related_entity_id, balance_after_units, created_at, comment) "
                "SELECT users.id, :asset_id, 'adjustment', COALESCE(users.ton_balance_nano, 0), "
                "'credit', 'migration', users.id, COALESCE(users.ton_balance_nano, 0), "
                "CURRENT_TIMESTAMP, 'Migrated legacy ton_balance_nano to AssetBalance' "
                "FROM users "
                "WHERE COALESCE(users.ton_balance_nano, 0) > 0 "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM asset_ledger_entries "
                "  WHERE asset_ledger_entries.user_id = users.id "
                "  AND asset_ledger_entries.asset_id = :asset_id "
                "  AND asset_ledger_entries.entry_type = 'adjustment' "
                "  AND asset_ledger_entries.related_entity_type = 'migration'"
                ")"
            ),
            {"asset_id": ton_asset_id},
        )


def ensure_asset_gift_columns() -> None:
    with engine.begin() as connection:
        gifts_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'asset_gifts'",
            )
        ).first()
        if not gifts_table:
            return

        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(asset_gifts)")).all()
        }
        statements = []
        if "fee_units" not in columns:
            statements.append(
                "ALTER TABLE asset_gifts ADD COLUMN fee_units BIGINT DEFAULT 0"
            )
        if "net_amount_units" not in columns:
            statements.append(
                "ALTER TABLE asset_gifts ADD COLUMN net_amount_units BIGINT DEFAULT 0"
            )

        for statement in statements:
            connection.execute(text(statement))

        if "net_amount_units" not in columns:
            connection.execute(
                text(
                    "UPDATE asset_gifts "
                    "SET net_amount_units = amount_units - COALESCE(fee_units, 0) "
                    "WHERE COALESCE(net_amount_units, 0) = 0"
                )
            )


def ensure_asset_deposit_columns() -> None:
    with engine.begin() as connection:
        deposits_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'asset_deposits'",
            )
        ).first()
        if not deposits_table:
            return

        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(asset_deposits)")).all()
        }
        statements = []
        if "user_id" not in columns:
            statements.append("ALTER TABLE asset_deposits ADD COLUMN user_id INTEGER")
        if "asset_id" not in columns:
            statements.append("ALTER TABLE asset_deposits ADD COLUMN asset_id INTEGER")
        if "wallet_address" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN wallet_address VARCHAR(128)"
            )
        if "target_wallet_address" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN target_wallet_address VARCHAR(128)"
            )
        if "amount_units" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN amount_units BIGINT DEFAULT 0"
            )
        if "tx_hash" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN tx_hash VARCHAR(128)"
            )
        if "comment" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN comment VARCHAR(160)"
            )
        if "status" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN status VARCHAR(32) DEFAULT 'pending'"
            )
        if "provider" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN provider VARCHAR(64) DEFAULT 'ton_native'"
            )
        if "network" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN network VARCHAR(32) DEFAULT 'ton_testnet'"
            )
        if "failed_reason" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN failed_reason VARCHAR(500)"
            )
        if "payout_status" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN payout_status VARCHAR(32) DEFAULT 'pending'"
            )
        if "payout_tx_hash" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN payout_tx_hash VARCHAR(128)"
            )
        if "payout_failed_reason" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN payout_failed_reason VARCHAR(500)"
            )
        if "payout_sent_at" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN payout_sent_at DATETIME"
            )
        if "payout_confirmed_at" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN payout_confirmed_at DATETIME"
            )
        if "created_at" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN created_at DATETIME"
            )
        if "confirmed_at" not in columns:
            statements.append(
                "ALTER TABLE asset_deposits ADD COLUMN confirmed_at DATETIME"
            )

        for statement in statements:
            connection.execute(text(statement))

        if "created_at" not in columns:
            connection.execute(
                text(
                    "UPDATE asset_deposits "
                    "SET created_at = CURRENT_TIMESTAMP "
                    "WHERE created_at IS NULL"
                )
            )
        updated_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(asset_deposits)")).all()
        }
        if "payout_status" in updated_columns:
            connection.execute(
                text(
                    "UPDATE asset_deposits "
                    "SET payout_status = 'pending' "
                    "WHERE payout_status IS NULL OR payout_status = ''"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_asset_deposits_payout_status "
                    "ON asset_deposits(payout_status)"
                )
            )
        if "payout_tx_hash" in updated_columns:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_asset_deposits_payout_tx_hash "
                    "ON asset_deposits(payout_tx_hash)"
                )
            )
