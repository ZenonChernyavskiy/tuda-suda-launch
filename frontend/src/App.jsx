import { useEffect, useMemo, useState } from "react";
import { useTonConnectUI, useTonWallet } from "@tonconnect/ui-react";

import { api, setAccessToken } from "./api";
import {
  TEST_USERS,
  getMockUser,
  getTelegramInitData,
  getTelegramStartParam,
  getTelegramUserPhotoUrl,
  getTelegramWebApp,
  initTelegramWebApp,
  isTelegramMode,
  setMockUser,
} from "./telegram";
import { encodeTonTextCommentPayload } from "./tonPayload";

const IS_PRODUCTION = import.meta.env.PROD;
const ENABLE_MOCK_AUTH =
  import.meta.env.VITE_ENABLE_MOCK_AUTH === "true" ||
  (!IS_PRODUCTION && import.meta.env.VITE_ENABLE_MOCK_AUTH !== "false");
const MENU = [
  { id: "home", label: "Главная" },
  { id: "all", label: "Все" },
  { id: "referrals", label: "Рефералы" },
  { id: "profile", label: "Профиль" },
];

const AMOUNTS = [1, 5, 10, 25];
const USER_ASSET_SYMBOL = "TDSD";

const LEADERBOARD_TABS = [
  { id: "karma", label: "Карма", value: "karma" },
  { id: "senders", label: "Отправили", value: "total_sent" },
  { id: "receivers", label: "Получили", value: "total_received" },
];

const DEFAULT_FEE_CONFIG = {
  buy_commission_percent: "1",
  transfer_commission_percent: "10",
  purchase_fee_percent: "1",
  purchase_min_fee_ton: "0",
  tdsd_fixed_price_ton: "0.1",
  tdsd_per_ton: "10",
  transfer_fee_percent: "10",
  transfer_fee_asset_symbol: "TDSD",
  payment_address: "",
  treasury_wallet_address: "",
  hot_wallet_address: "",
  tdsd_jetton_master_address: "",
};

const RANKS = [
  {
    name: "Новичок",
    condition: "стартовый ранг",
    description: "Профиль только начинает накапливать историю.",
  },
  {
    name: "Добряк",
    condition: "карма от 50",
    description: "Пользователь регулярно участвует в жизни проекта.",
  },
  {
    name: "Меценат",
    condition: "карма от 200",
    description: "Заметная активность и стабильное участие.",
  },
  {
    name: "Легенда",
    condition: "карма от 500",
    description: "Высокая активность и вклад в сообщество.",
  },
  {
    name: "Титан",
    condition: "карма от 1000",
    description: "Максимальный уровень активности.",
  },
];

function displayName(user) {
  if (!user) return "Пользователь";
  if (user.username) return `@${user.username}`;
  return user.first_name || `ID ${user.telegram_id || user.id}`;
}

function revealTargetKey(target) {
  if (!target) return "";
  return `${target.context_type}:${target.context_id}:${target.target_role}`;
}

function shortenAddress(address) {
  if (!address) return "";
  if (address.length <= 12) return address;
  return `${address.slice(0, 4)}...${address.slice(-4)}`;
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

function buildTelegramShareUrl(url) {
  const params = new URLSearchParams({
    url,
    text: "Присоединяйтесь к Tuda Suda",
  });
  return `https://t.me/share/url?${params.toString()}`;
}

function userAssets(items) {
  return (items || []).filter((item) => item?.symbol === USER_ASSET_SYMBOL);
}

function userDepositMessage(message) {
  if (!message) return "";
  if (/Jetton deposits are disabled|contract deployment|TDSD_PROJECT_JETTON_WALLET/i.test(message)) {
    return "Пополнение TDSD временно недоступно";
  }
  if (/TON Center API/i.test(message)) {
    return "Не удалось проверить пополнение. Попробуйте позже.";
  }
  return message
    .replace(/\bTON Connect\b/g, "кошелек")
    .replace(/\bTON wallet\b/gi, "кошелек")
    .replace(/\bTON deposits\b/gi, "пополнения")
    .replace(/\bnative TON\b/gi, "этого актива")
    .replace(/\bTON deposit\b/gi, "пополнение")
    .replace(/\bJetton deposit\b/gi, "пополнение TDSD")
    .replace(/\bJetton\b/g, "TDSD")
    .replace(/\bTON-кошелек\b/g, "кошелек")
    .replace(/\bTON кошелек\b/g, "кошелек")
    .replace(/\btestnet\b/gi, "")
    .trim();
}

function formatTonFromNano(amountNano) {
  const nano = BigInt(String(amountNano || "0"));
  const whole = nano / 1000000000n;
  const fraction = (nano % 1000000000n).toString().padStart(9, "0").slice(0, 6);
  const trimmedFraction = fraction.replace(/0+$/, "");
  return trimmedFraction ? `${whole}.${trimmedFraction}` : whole.toString();
}

function tonToNanoString(amount) {
  const [wholeRaw, fractionRaw = ""] = String(amount).trim().replace(",", ".").split(".");
  const whole = wholeRaw || "0";
  const fraction = fractionRaw.padEnd(9, "0").slice(0, 9);
  return (BigInt(whole) * 1000000000n + BigInt(fraction || "0")).toString();
}

function displayAmountToUnits(amount, decimals) {
  const normalized = String(amount).trim().replace(",", ".");
  if (!/^\d+(\.\d*)?$/.test(normalized)) {
    throw new Error("Введите корректную сумму");
  }
  const [wholeRaw, fractionRaw = ""] = normalized.split(".");
  const whole = wholeRaw || "0";
  const fraction = decimals > 0
    ? fractionRaw.padEnd(decimals, "0").slice(0, decimals)
    : "";
  const scale = 10n ** BigInt(decimals);
  return (BigInt(whole) * scale + BigInt(fraction || "0")).toString();
}

function unitsToDisplay(amountUnits, decimals) {
  const amount = BigInt(String(amountUnits || "0"));
  const sign = amount < 0n ? "-" : "";
  const absolute = amount < 0n ? -amount : amount;
  if (!decimals) {
    return `${sign}${absolute}`;
  }
  const scale = 10n ** BigInt(decimals);
  const whole = absolute / scale;
  const fraction = (absolute % scale).toString().padStart(decimals, "0").replace(/0+$/, "");
  return fraction ? `${sign}${whole}.${fraction}` : `${sign}${whole}`;
}

function percentToBasisPoints(percent) {
  const normalized = String(percent || "0").trim().replace(",", ".");
  const [wholeRaw, fractionRaw = ""] = normalized.split(".");
  const whole = wholeRaw || "0";
  const fraction = fractionRaw.padEnd(2, "0").slice(0, 2);
  return BigInt(whole) * 100n + BigInt(fraction || "0");
}

function calculateRecipientDisplay(amountDisplay, asset, feePercent) {
  if (!asset) return "";
  try {
    const amountUnits = BigInt(displayAmountToUnits(amountDisplay || "0", asset.decimals));
    const feeUnits = amountUnits * percentToBasisPoints(feePercent) / 10000n;
    const recipientUnits = amountUnits - feeUnits;
    if (recipientUnits < 0n) return "";
    return unitsToDisplay(recipientUnits, asset.decimals);
  } catch {
    return "";
  }
}

function calculateFixedPricePaymentDisplay(amountDisplay, asset, fixedPriceTon) {
  if (!asset || !fixedPriceTon) return "";
  try {
    const tdsdUnits = BigInt(displayAmountToUnits(amountDisplay || "0", asset.decimals));
    const priceNano = BigInt(displayAmountToUnits(fixedPriceTon, 9));
    const scale = 10n ** BigInt(asset.decimals);
    return unitsToDisplay((tdsdUnits * priceNano) / scale, 9);
  } catch {
    return "";
  }
}

function calculateFixedPriceTdsdDisplay(paymentTonDisplay, asset, fixedPriceTon) {
  if (!asset || !fixedPriceTon) return "";
  try {
    const paymentNano = BigInt(displayAmountToUnits(paymentTonDisplay || "0", 9));
    const priceNano = BigInt(displayAmountToUnits(fixedPriceTon, 9));
    if (priceNano <= 0n) return "";
    const scale = 10n ** BigInt(asset.decimals);
    return unitsToDisplay((paymentNano * scale) / priceNano, asset.decimals);
  } catch {
    return "";
  }
}

function readTonBalanceNano(payload) {
  if (payload?.ton_balance_nano !== undefined && payload?.ton_balance_nano !== null) {
    return String(payload.ton_balance_nano);
  }
  const legacyBalance = String(payload?.ton_balance || "0");
  if (legacyBalance.includes("e")) {
    return String(Math.round(Number(legacyBalance) * 1_000_000_000));
  }
  return tonToNanoString(legacyBalance);
}

function statusLabel(status) {
  const labels = {
    pending: "Ожидаем оплату",
    confirmed: "Оплата найдена",
    failed: "Ошибка отправки, обратитесь в поддержку",
  };
  return labels[status] || status;
}

function purchaseStatusLabel(deposit) {
  if (!deposit) return "";
  if (deposit.status === "pending") return "Ожидаем оплату";
  if (deposit.status === "failed") return "Ошибка отправки, обратитесь в поддержку";
  if (deposit.status === "confirmed") {
    if (deposit.payout_status === "sent" || deposit.payout_status === "confirmed") {
      return "TDSD отправлены";
    }
    if (deposit.payout_status === "failed") {
      return "Ошибка отправки, обратитесь в поддержку";
    }
    return "Отправляем TDSD";
  }
  return statusLabel(deposit.status);
}

function depositSymbol(deposit) {
  return deposit?.symbol || deposit?.asset_symbol || USER_ASSET_SYMBOL;
}

function depositAmountLabel(deposit) {
  const symbol = depositSymbol(deposit);
  if (deposit?.amount_display) {
    return `${deposit.amount_display} ${symbol}`;
  }
  if (deposit?.amount_ton !== undefined && deposit?.amount_ton !== null) {
    return `${deposit.amount_ton} ${symbol}`;
  }
  return `${formatTonFromNano(deposit?.amount_units || deposit?.amount_nano || "0")} ${symbol}`;
}

function depositPaymentAmountUnits(deposit) {
  if (deposit?.payment_amount_nano !== undefined && deposit?.payment_amount_nano !== null) {
    return String(deposit.payment_amount_nano);
  }
  if (deposit?.amount_units !== undefined && deposit?.amount_units !== null) {
    return String(deposit.amount_units);
  }
  if (deposit?.amount_nano !== undefined && deposit?.amount_nano !== null) {
    return String(deposit.amount_nano);
  }
  return tonToNanoString(deposit?.amount_ton || "0");
}

function ledgerTypeLabel(type) {
  const labels = {
    deposit: "Пополнение",
    gift_sent: "Подарок отправлен",
    gift_received: "Подарок получен",
    adjustment: "Корректировка",
    fee: "Комиссия",
    fee_purchase: "Комиссия покупки",
    fee_transfer: "Комиссия перевода",
    treasury_income: "Treasury",
    referral_reward: "Реферальная награда",
    referral_reward_pending: "Реферальная награда",
    referral_reward_credit: "Реферальная награда",
  };
  return labels[type] || type;
}

function directionLabel(direction) {
  return direction === "credit" ? "Зачисление" : "Списание";
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function balanceBySymbol(balances, symbol) {
  return balances.find((asset) => asset.symbol === symbol);
}

function primaryBalance(balances) {
  return (
    balanceBySymbol(balances, USER_ASSET_SYMBOL) ||
    balances[0]
  );
}

function transactionTitle(transaction) {
  return transaction.type === "sent" ? "Подарок отправлен" : "Подарок получен";
}

function transactionOperation(transaction) {
  return {
    key: `virtual-${transaction.id}`,
    date: transaction.created_at,
    title: transactionTitle(transaction),
    type: "Виртуальный дар",
    user: "Случайный пользователь",
    token: "TDSD",
    amount: String(transaction.amount),
    direction: transaction.type === "sent" ? "Списание" : "Зачисление",
    directionRaw: transaction.type === "sent" ? "debit" : "credit",
    comment: transaction.message,
  };
}

function publicTransactionOperation(transaction) {
  const isFee = transaction.source_type === "fee";
  const isReferralReward = transaction.source_type === "referral_reward";
  const revealTargets = [
    transaction.sender_reveal,
    transaction.receiver_reveal,
  ].filter(Boolean);
  return {
    key: transaction.id,
    date: transaction.created_at,
    title:
      isReferralReward
        ? "Реферальная награда"
        : isFee
        ? "Комиссия сервиса"
        : transaction.source_type === "asset_gift"
        ? "Дар токена"
        : "Дар TDSD",
    type: isFee
      ? "Системная операция"
      : isReferralReward
        ? "Рефералы"
        : transaction.source_type === "asset_gift"
        ? "TDSD"
        : "Виртуальный дар",
    user: transaction.sender,
    sender: transaction.sender,
    receiver: transaction.receiver,
    token: transaction.token,
    amount: transaction.amount,
    direction: transaction.direction,
    directionRaw: "transfer",
    comment: transaction.comment,
    revealTargets,
  };
}

function assetGiftOperation(gift) {
  const revealTargets = gift.reveal_target ? [gift.reveal_target] : [];
  return {
    key: `asset-gift-${gift.id}`,
    date: gift.created_at,
    title: gift.type === "sent" ? "Дар отправлен" : "Дар получен",
    type: "TDSD",
    user: gift.counterparty_display_name || "Случайный пользователь",
    token: gift.symbol,
    amount: gift.amount_display,
    direction: gift.type === "sent" ? "Списание" : "Зачисление",
    directionRaw: gift.type === "sent" ? "debit" : "credit",
    comment: gift.message,
    revealTargets,
  };
}

function assetGiftFeedOperation(gift) {
  return {
    key: `asset-feed-${gift.id}`,
    date: gift.created_at,
    title: "Публичный дар",
    type: "Общая лента",
    user: "Сообщество",
    token: gift.symbol,
    amount: gift.amount_display,
    direction: "Событие",
    directionRaw: "credit",
    comment: gift.text,
  };
}

function ledgerOperation(entry) {
  return {
    key: `ledger-${entry.id}`,
    date: entry.created_at,
    title: ledgerTypeLabel(entry.entry_type),
    type: ledgerTypeLabel(entry.entry_type),
    user: "Вы",
    token: entry.symbol,
    amount: entry.amount_display,
    direction: directionLabel(entry.direction),
    directionRaw: entry.direction,
    comment: entry.comment,
  };
}

function isFeeLedgerEntry(entry) {
  return ["fee", "fee_purchase", "fee_transfer", "treasury_income"].includes(
    entry?.entry_type,
  );
}

function newestFirst(items) {
  return [...items].sort((a, b) => new Date(b.date) - new Date(a.date));
}

function Stat({ label, value, onClick }) {
  const content = (
    <>
      <span>{label}</span>
      <strong>{value}</strong>
    </>
  );
  if (onClick) {
    return (
      <button className="stat stat-button" onClick={onClick} type="button">
        {content}
      </button>
    );
  }
  return (
    <div className="stat">
      {content}
    </div>
  );
}

function ProfileInfoSheet({ type, user, onClose }) {
  if (!type) return null;

  const modal = {
    karma: {
      title: "Карма",
      body: [
        "Карма отражает активность пользователя в проекте.",
        "Она начисляется за активность, переводы TDSD, участие в проекте и приглашение пользователей.",
      ],
    },
    rank: {
      title: "Ранг",
      body: [
        "Ранг показывает текущий уровень активности профиля.",
        `Ваш текущий ранг: ${user.rank || "Новичок"}.`,
      ],
    },
  }[type];

  if (!modal) return null;

  return (
    <div className="info-sheet-backdrop" onClick={onClose} role="presentation">
      <section
        aria-modal="true"
        className="info-sheet"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="info-sheet-title">
          <h2>{modal.title}</h2>
          <button className="sheet-close" onClick={onClose} type="button">
            Закрыть
          </button>
        </div>
        <div className="info-sheet-body">
          {modal.body.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
          {type === "rank" ? (
            <div className="rank-list">
              {RANKS.map((rank) => (
                <article
                  className={rank.name === user.rank ? "rank-item current" : "rank-item"}
                  key={rank.name}
                >
                  <div>
                    <strong>{rank.name}</strong>
                    <span>{rank.condition}</span>
                  </div>
                  <p>{rank.description}</p>
                </article>
              ))}
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}

function Notice({ type, children, onClose }) {
  if (!children) return null;
  return (
    <button className={`notice ${type}`} onClick={onClose} type="button">
      {children}
    </button>
  );
}

function TransactionList({ transactions, emptyText }) {
  if (!transactions.length) {
    return <p className="empty">{emptyText}</p>;
  }
  return (
    <div className="list">
      {transactions.map((item) => (
        <article className="row" key={item.id}>
          <div>
            <strong>{transactionTitle(item)}</strong>
            <span>{formatDate(item.created_at)}</span>
            {item.message ? <p>{item.message}</p> : null}
          </div>
          <b className={item.type === "sent" ? "negative" : "positive"}>
            {item.type === "sent" ? "-" : "+"}
            {item.amount}
          </b>
        </article>
      ))}
    </div>
  );
}

function OperationList({
  operations,
  emptyText,
  compact = false,
  onRevealUser,
  revealingKey = "",
}) {
  if (!operations.length) {
    return <p className="empty">{emptyText}</p>;
  }
  return (
    <div className={compact ? "list compact-list" : "list"}>
      {operations.map((item) => (
        <article className="operation-row" key={item.key}>
          <div>
            <strong>{item.title}</strong>
            <span>
              {formatDate(item.date)} · {item.user}
            </span>
            {item.sender && item.receiver ? (
              <p>
                {item.sender} → {item.receiver}
              </p>
            ) : null}
            <p>
              {item.type} · {item.token} · {item.direction}
            </p>
            {item.comment ? <p className="operation-comment">{item.comment}</p> : null}
            {Boolean(item.revealTargets?.length) && onRevealUser ? (
              <div className="reveal-actions">
                {item.revealTargets.map((target) => {
                  const key = revealTargetKey(target);
                  return (
                    <button
                      className="reveal-button"
                      disabled={revealingKey === key}
                      key={key}
                      onClick={() => onRevealUser(target)}
                      type="button"
                    >
                      {revealingKey === key ? "Раскрываем..." : target.label}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
          <b
            className={
              item.directionRaw === "credit"
                ? "positive"
                : item.directionRaw === "debit"
                  ? "negative"
                  : "neutral"
            }
          >
            {item.directionRaw === "credit" ? "+" : item.directionRaw === "debit" ? "-" : ""}
            {item.amount} {item.token}
          </b>
        </article>
      ))}
    </div>
  );
}

function AssetBalanceList({ balances, emptyText = "Балансы пока не созданы." }) {
  if (!balances.length) {
    return <p className="empty">{emptyText}</p>;
  }
  return (
    <div className="asset-grid">
      {balances.map((asset) => (
        <article className="asset-card" key={asset.symbol}>
          <div>
            <strong>{asset.symbol}</strong>
            <span>{asset.name}</span>
          </div>
          <b>{asset.balance_display}</b>
        </article>
      ))}
    </div>
  );
}

function HomeScreen({
  dashboard,
  tonAddress,
  assetBalances,
  recentOperations,
  sendProps,
  onRevealUser,
  revealingKey,
}) {
  const [giftOpen, setGiftOpen] = useState(false);
  const user = dashboard.user;
  const visibleAssetBalances = userAssets(assetBalances);
  return (
    <main className="screen">
      <section className="hero">
        <div>
          <span className="eyebrow">Туда-Сюда</span>
          <h1>Привет, {displayName(user)}</h1>
          <p>Делай переводы случайным людям</p>
          <span className={tonAddress ? "ton-status connected" : "ton-status"}>
            {tonAddress
              ? `Кошелек: ${shortenAddress(tonAddress)}`
              : "Кошелек не подключен"}
          </span>
        </div>
      </section>

      <section className="stats-grid">
        <Stat label="Карма" value={user.karma} />
        <Stat label="Ранг" value={user.rank} />
        <Stat label="Отправил" value={user.total_sent} />
        <Stat label="Получил" value={user.total_received} />
      </section>

      <section className="section cta-section">
        <div>
          <span className="eyebrow">Дар случайному человеку</span>
          <h2>{giftOpen ? "Выберите сумму TDSD" : "Сделать доброе движение"}</h2>
          <p>Отправляйте TDSD внутри приложения. Получатель выбирается случайно.</p>
        </div>
        <button
          className="primary"
          onClick={() => setGiftOpen((value) => !value)}
          type="button"
        >
          {giftOpen ? "Свернуть" : "Отправить дар"}
        </button>
      </section>

      {giftOpen ? <SendScreen {...sendProps} /> : null}

      <section className="section">
        <div className="section-title">
          <h2>TDSD</h2>
        </div>
        <AssetBalanceList
          balances={visibleAssetBalances}
          emptyText="TDSD появится после синхронизации."
        />
      </section>

      <section className="section">
        <div className="section-title">
          <h2>Последние операции</h2>
          <span>5 последних</span>
        </div>
        <OperationList
          compact
          operations={recentOperations}
          emptyText="Пока тихо. Первый подарок задаст тон."
          onRevealUser={onRevealUser}
          revealingKey={revealingKey}
        />
      </section>
    </main>
  );
}

function SendScreen({
  assetBalances,
  onSendAssetGift,
  assetGiftSending,
}) {
  const [message, setMessage] = useState("");
  const [assetSymbol, setAssetSymbol] = useState(USER_ASSET_SYMBOL);
  const [assetAmount, setAssetAmount] = useState("1");
  const visibleAssetBalances = userAssets(assetBalances);
  const selectedAsset =
    visibleAssetBalances.find((asset) => asset.symbol === assetSymbol) ||
    visibleAssetBalances[0];

  async function handleAssetSubmit(event) {
    event.preventDefault();
    if (!selectedAsset) return;
    const amountUnits = displayAmountToUnits(assetAmount, selectedAsset.decimals);
    await onSendAssetGift({
      asset_symbol: selectedAsset.symbol,
      amount_units: amountUnits,
      message: message.trim() || null,
    });
    setMessage("");
  }

  return (
      <section className="section gift-panel">
        <div className="section-title">
          <h2>Отправить подарок</h2>
          <span>
            {selectedAsset
              ? `${selectedAsset.balance_display} ${selectedAsset.symbol}`
              : "TDSD недоступен"}
          </span>
        </div>

          <form className="send-form" onSubmit={handleAssetSubmit}>
            {selectedAsset ? (
              <div className="wallet-address">
                <span>Доступно</span>
                <b>
                  {selectedAsset.balance_display} {selectedAsset.symbol}
                </b>
              </div>
            ) : (
              <p className="empty">TDSD пока недоступен.</p>
            )}
            <label className="field">
              <span>Сумма TDSD</span>
              <input
                inputMode="decimal"
                min="0"
                onChange={(event) => setAssetAmount(event.target.value)}
                placeholder="Например 1"
                type="text"
                value={assetAmount}
              />
            </label>
            <label className="field">
              <span>Анонимное сообщение</span>
              <textarea
                maxLength={500}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Напишите пару теплых слов"
                rows={5}
                value={message}
              />
            </label>
            <button
              className="primary"
              disabled={assetGiftSending || !selectedAsset}
              type="submit"
            >
              {assetGiftSending ? "Отправляем..." : "Отправить TDSD"}
            </button>
          </form>
      </section>
  );
}

function AssetGiftHistoryList({ gifts }) {
  if (!gifts.length) {
    return <p className="empty">TDSD-подарки появятся после первой отправки.</p>;
  }
  return (
    <div className="list">
      {gifts.map((gift) => (
        <article className="ledger-row" key={gift.id}>
          <div>
            <strong>
              {gift.type === "sent" ? "TDSD-подарок отправлен" : "TDSD-подарок получен"}
            </strong>
            <span>
              {gift.symbol} · {formatDate(gift.created_at)}
            </span>
            {gift.message ? <p>{gift.message}</p> : null}
            <p>{gift.counterparty_display_name}</p>
          </div>
          <b className={gift.type === "sent" ? "negative" : "positive"}>
            {gift.type === "sent" ? "-" : "+"}
            {gift.amount_display} {gift.symbol}
          </b>
        </article>
      ))}
    </div>
  );
}

function HistoryScreen({ transactions, assetGifts }) {
  return (
    <main className="screen">
      <section className="section">
        <div className="section-title">
          <h2>Виртуальные подарки</h2>
        </div>
        <TransactionList
          transactions={transactions}
          emptyText="История появится после первой отправки или получения."
        />
      </section>

      <section className="section">
        <div className="section-title">
          <h2>TDSD-подарки</h2>
        </div>
        <AssetGiftHistoryList gifts={assetGifts} />
      </section>
    </main>
  );
}

function LeaderboardScreen({ leaderboard, onRevealUser, revealingKey = "" }) {
  const [activeTab, setActiveTab] = useState("karma");
  const currentTab = LEADERBOARD_TABS.find((tab) => tab.id === activeTab);
  const rows = leaderboard?.[activeTab] || [];

  return (
    <main className="screen">
      <section className="section">
        <div className="section-title">
          <h2>Лидерборд</h2>
        </div>
        <div className="segments">
          {LEADERBOARD_TABS.map((tab) => (
            <button
              className={activeTab === tab.id ? "active" : ""}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
        {!rows.length ? (
          <p className="empty">Список лидеров пока пуст.</p>
        ) : (
          <div className="list">
            {rows.map((user, index) => (
              <article className="leader-row" key={user.id}>
                <span>{index + 1}</span>
                <div>
                  <strong>{displayName(user)}</strong>
                  <small>{user.rank}</small>
                  {user.reveal_target && onRevealUser ? (
                    <button
                      className="reveal-button inline"
                      disabled={revealingKey === revealTargetKey(user.reveal_target)}
                      onClick={() => onRevealUser(user.reveal_target)}
                      type="button"
                    >
                      {revealingKey === revealTargetKey(user.reveal_target)
                        ? "Раскрываем..."
                        : user.reveal_target.label}
                    </button>
                  ) : null}
                </div>
                <b>{user[currentTab.value]}</b>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function TonTopUpScreen({
  assets,
  assetBalances,
  feeConfig,
  connectedAddress,
  savedWallet,
  tonBalanceNano,
  deposits,
  currentDeposit,
  depositLoading,
  paying,
  verifying,
  onCreateDeposit,
  onPayDeposit,
  onCopyPaymentAddress,
  onVerifyDeposit,
}) {
  const [purchaseMode, setPurchaseMode] = useState("tdsd");
  const [customAmount, setCustomAmount] = useState("10");
  const [selectedAssetSymbol, setSelectedAssetSymbol] = useState(USER_ASSET_SYMBOL);
  const depositAssets = userAssets(assets);
  const selectedAsset =
    depositAssets.find((asset) => asset.symbol === selectedAssetSymbol) ||
    depositAssets[0] ||
    null;
  const selectedBalance = assetBalances.find(
    (balance) => balance.symbol === selectedAsset?.symbol,
  );
  const savedAddress = savedWallet?.wallet_address || "";
  const hasConnectedWallet = Boolean(connectedAddress);
  const hasSavedWallet = Boolean(savedAddress);
  const isDifferentWallet =
    hasConnectedWallet && hasSavedWallet && connectedAddress !== savedAddress;
  const needsWalletAutoSave =
    hasConnectedWallet && (!hasSavedWallet || isDifferentWallet);
  const amount = customAmount.trim();
  const buyCommissionPercent =
    feeConfig?.buy_commission_percent || feeConfig?.purchase_fee_percent || "1";
  const fixedPriceTon = feeConfig?.tdsd_fixed_price_ton || "0.1";
  const buyCommissionApplies = selectedAsset?.symbol === USER_ASSET_SYMBOL;
  const tdsdAmountDisplay = buyCommissionApplies && purchaseMode === "ton"
    ? calculateFixedPriceTdsdDisplay(amount, selectedAsset, fixedPriceTon)
    : amount;
  const buyCreditedDisplay = buyCommissionApplies
    ? calculateRecipientDisplay(tdsdAmountDisplay, selectedAsset, buyCommissionPercent)
    : "";
  const paymentDisplay = buyCommissionApplies
    ? purchaseMode === "ton"
      ? amount
      : calculateFixedPricePaymentDisplay(tdsdAmountDisplay, selectedAsset, fixedPriceTon)
    : "";
  const paymentAddress =
    currentDeposit?.payment_address || currentDeposit?.target_wallet_address || "";
  const balanceText = selectedBalance
    ? `${selectedBalance.balance_display} ${selectedBalance.symbol}`
    : selectedAsset?.symbol || USER_ASSET_SYMBOL;

  async function handleCreate(event) {
    event.preventDefault();
    if (!selectedAsset) return;
    await onCreateDeposit(selectedAsset, tdsdAmountDisplay);
  }

  return (
    <>
      <section className="section ton-section">
        <div className="section-title">
          <h2>Купить TDSD</h2>
          <span>{balanceText}</span>
        </div>

        <div className="wallet-state">
          <span
            className={hasConnectedWallet ? "wallet-dot connected" : "wallet-dot"}
          />
          <strong>
            {!hasConnectedWallet
              ? "Кошелек не подключен"
              : !hasSavedWallet
                ? "Кошелек подключен, но не сохранен"
                : isDifferentWallet
                  ? "Подключенный кошелек отличается от сохраненного"
                  : "Кошелек подключен"}
          </strong>
        </div>

        {savedAddress ? (
          <div className="wallet-address">
            <span>Сохраненный адрес</span>
            <b>{shortenAddress(savedAddress)}</b>
          </div>
        ) : null}

        {isDifferentWallet ? (
          <p className="wallet-warning">
            Подключенный адрес будет сохранен автоматически перед покупкой.
          </p>
        ) : null}

        {needsWalletAutoSave && !isDifferentWallet ? (
          <p className="wallet-note">
            Подключенный адрес будет сохранен автоматически перед покупкой.
          </p>
        ) : null}

        <form className="send-form" onSubmit={handleCreate}>
          <div className="amount-grid asset-picker">
            {depositAssets.map((asset) => (
              <button
                className={selectedAsset?.symbol === asset.symbol ? "amount active" : "amount"}
                key={asset.symbol}
                onClick={() => {
                  setSelectedAssetSymbol(asset.symbol);
                }}
                type="button"
              >
                {asset.symbol}
              </button>
            ))}
          </div>
          {!selectedAsset ? (
            <p className="empty">Пополнение TDSD временно недоступно</p>
          ) : null}
          <div className="segments purchase-mode">
            <button
              className={purchaseMode === "tdsd" ? "active" : ""}
              onClick={() => setPurchaseMode("tdsd")}
              type="button"
            >
              В TDSD
            </button>
            <button
              className={purchaseMode === "ton" ? "active" : ""}
              onClick={() => setPurchaseMode("ton")}
              type="button"
            >
              В TON
            </button>
          </div>
          <label className="field">
            <span>Сумма {purchaseMode === "tdsd" ? "TDSD" : "TON"}</span>
            <input
              inputMode="decimal"
              min="0"
              onChange={(event) => setCustomAmount(event.target.value)}
              placeholder={purchaseMode === "tdsd" ? "Например 100" : "Например 10"}
              type="text"
              value={customAmount}
            />
          </label>
          {buyCommissionApplies ? (
            <div className="fee-note">
              <p>Курс: 1 TDSD = {fixedPriceTon} TON</p>
              <p>
                Покупка: {tdsdAmountDisplay || "0"} {selectedAsset.symbol}
              </p>
              <p>К оплате: {paymentDisplay || "0"} TON</p>
              <p>
                На баланс будет зачислено: {buyCreditedDisplay || "0"} {selectedAsset.symbol}
              </p>
            </div>
          ) : null}
          <button
            className="primary"
            disabled={
              depositLoading ||
              !hasConnectedWallet ||
              !selectedAsset
            }
            type="submit"
          >
            {depositLoading ? "Создаем..." : "Купить TDSD"}
          </button>
        </form>

        {currentDeposit ? (
          <div className="deposit-box">
            <div className="wallet-address">
              <span>Статус</span>
              <b>{purchaseStatusLabel(currentDeposit)}</b>
            </div>
            <div className="wallet-address">
              <span>К покупке</span>
              <b>{depositAmountLabel(currentDeposit)}</b>
            </div>
            {currentDeposit.payment_amount_ton ? (
              <div className="wallet-address">
                <span>К оплате</span>
                <b>{currentDeposit.payment_amount_ton} TON</b>
              </div>
            ) : null}
            {paymentAddress ? (
              <>
                <div className="wallet-address">
                  <span>Адрес для оплаты</span>
                  <b>{paymentAddress}</b>
                </div>
                <button
                  className="secondary"
                  onClick={() => onCopyPaymentAddress(paymentAddress)}
                  type="button"
                >
                  Скопировать адрес
                </button>
              </>
            ) : null}
            <div className="wallet-address">
              <span>Комментарий</span>
              <b>{currentDeposit.comment}</b>
            </div>
            {currentDeposit.payout_tx_hash ? (
              <div className="wallet-address">
                <span>Выплата</span>
                <b>{shortenAddress(currentDeposit.payout_tx_hash)}</b>
              </div>
            ) : null}
            {currentDeposit.payout_status === "failed" && currentDeposit.payout_failed_reason ? (
              <p className="failed-reason">
                {userDepositMessage(currentDeposit.payout_failed_reason)}
              </p>
            ) : null}
            <p className="wallet-note">
              Оплатите указанную сумму TON и дождитесь подтверждения. Комментарий нужен
              для автоматического зачисления TDSD.
            </p>
            {["ton_native", "tdsd_fixed_price"].includes(currentDeposit.provider) ? (
              <button
                className="primary"
                disabled={paying || currentDeposit.status !== "pending"}
                onClick={() => onPayDeposit(currentDeposit)}
                type="button"
              >
                {paying ? "Открываем кошелек..." : "Оплатить через кошелёк"}
              </button>
            ) : (
              <p className="wallet-note">
                Для покупки отправьте {depositAmountLabel(currentDeposit)} на
                указанный адрес из подключенного кошелька и обязательно укажите комментарий.
              </p>
            )}
            <button
              className="secondary"
              disabled={verifying}
              onClick={() => onVerifyDeposit(currentDeposit.deposit_id || currentDeposit.id)}
              type="button"
            >
              {verifying ? "Проверяем..." : "Проверить статус"}
            </button>
          </div>
        ) : null}
      </section>

      <section className="section">
        <div className="section-title">
          <h2>Пополнения</h2>
        </div>
        {!deposits.length ? (
          <p className="empty">Пополнений пока нет.</p>
        ) : (
          <div className="list">
            {deposits.map((deposit) => (
              <article className="deposit-row" key={deposit.id}>
                <div>
                  <strong>{depositAmountLabel(deposit)}</strong>
                  <span>{purchaseStatusLabel(deposit)} · {formatDate(deposit.created_at)}</span>
                  {deposit.confirmed_at ? (
                    <p>Оплата найдена: {formatDate(deposit.confirmed_at)}</p>
                  ) : null}
                  {deposit.tx_hash ? <p>Оплата tx: {shortenAddress(deposit.tx_hash)}</p> : null}
                  {deposit.payout_tx_hash ? (
                    <p>Выплата tx: {shortenAddress(deposit.payout_tx_hash)}</p>
                  ) : null}
                  {deposit.comment ? <p>memo: {deposit.comment}</p> : null}
                  {deposit.status === "failed" && deposit.failed_reason ? (
                    <p className="failed-reason">{userDepositMessage(deposit.failed_reason)}</p>
                  ) : null}
                  {deposit.payout_status === "failed" && deposit.payout_failed_reason ? (
                    <p className="failed-reason">
                      {userDepositMessage(deposit.payout_failed_reason)}
                    </p>
                  ) : null}
                </div>
                <b>{depositSymbol(deposit)}</b>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function AssetsScreen({
  assets,
  balances,
  ledger,
  giftLeaderboard,
  onRevealUser,
  revealingKey = "",
}) {
  const visibleAssets = userAssets(assets);
  const visibleBalances = userAssets(balances);
  const senders = giftLeaderboard?.senders || [];
  const receivers = giftLeaderboard?.receivers || [];
  const balanceByAsset = new Map(
    visibleBalances.map((balance) => [balance.symbol, balance]),
  );
  return (
    <main className="screen">
      <section className="section">
        <div className="section-title">
          <h2>TDSD</h2>
        </div>
        {!visibleAssets.length ? (
          <p className="empty">TDSD пока не настроен.</p>
        ) : (
          <div className="list">
            {visibleAssets.map((asset) => (
              <article className="asset-row" key={asset.symbol}>
                <div>
                  <strong>{asset.symbol}</strong>
                  <span>{asset.name}</span>
                  <p>Внутренний баланс для подарков и покупок.</p>
                </div>
                <b>
                  {balanceByAsset.get(asset.symbol)?.balance_display || "0"} {asset.symbol}
                </b>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-title">
          <h2>Балансы</h2>
        </div>
        <AssetBalanceList balances={visibleBalances} />
      </section>

      <section className="section">
        <div className="section-title">
          <h2>История TDSD</h2>
        </div>
        {!ledger.length ? (
          <p className="empty">История появится после первой операции с TDSD.</p>
        ) : (
          <div className="list">
            {ledger.map((entry) => (
              <article className="ledger-row" key={entry.id}>
                <div>
                  <strong>{ledgerTypeLabel(entry.entry_type)}</strong>
                  <span>
                    {entry.symbol} · {formatDate(entry.created_at)}
                  </span>
                  {entry.comment ? <p>{entry.comment}</p> : null}
                </div>
                <b className={entry.direction === "credit" ? "positive" : "negative"}>
                  {entry.direction === "credit" ? "+" : "-"}
                  {entry.amount_display}
                </b>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-title">
          <h2>TDSD лидерборд</h2>
          <span>{giftLeaderboard?.symbol || USER_ASSET_SYMBOL}</span>
        </div>
        <div className="leaderboard-split">
          <div>
            <h3>Отправили</h3>
            {!senders.length ? (
              <p className="empty">Пока пусто.</p>
            ) : (
              <div className="list">
                {senders.slice(0, 5).map((user, index) => (
                  <article className="leader-row" key={user.id}>
                    <span>{index + 1}</span>
                    <div>
                      <strong>{displayName(user)}</strong>
                      <small>{user.amount_display} {giftLeaderboard.symbol}</small>
                      {user.reveal_target && onRevealUser ? (
                        <button
                          className="reveal-button inline"
                          disabled={revealingKey === revealTargetKey(user.reveal_target)}
                          onClick={() => onRevealUser(user.reveal_target)}
                          type="button"
                        >
                          {revealingKey === revealTargetKey(user.reveal_target)
                            ? "Раскрываем..."
                            : user.reveal_target.label}
                        </button>
                      ) : null}
                    </div>
                    <b>{user.amount_display}</b>
                  </article>
                ))}
              </div>
            )}
          </div>
          <div>
            <h3>Получили</h3>
            {!receivers.length ? (
              <p className="empty">Пока пусто.</p>
            ) : (
              <div className="list">
                {receivers.slice(0, 5).map((user, index) => (
                  <article className="leader-row" key={user.id}>
                    <span>{index + 1}</span>
                    <div>
                      <strong>{displayName(user)}</strong>
                      <small>{user.amount_display} {giftLeaderboard.symbol}</small>
                      {user.reveal_target && onRevealUser ? (
                        <button
                          className="reveal-button inline"
                          disabled={revealingKey === revealTargetKey(user.reveal_target)}
                          onClick={() => onRevealUser(user.reveal_target)}
                          type="button"
                        >
                          {revealingKey === revealTargetKey(user.reveal_target)
                            ? "Раскрываем..."
                            : user.reveal_target.label}
                        </button>
                      ) : null}
                    </div>
                    <b>{user.amount_display}</b>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

function AllTransactionsScreen({
  publicTransactions,
  loading,
  onRevealUser,
  revealingKey,
}) {
  const operations = newestFirst(
    publicTransactions.map(publicTransactionOperation),
  ).slice(0, 100);
  return (
    <main className="screen">
      <section className="section all-intro">
        <div className="section-title">
          <h2>Все транзакции</h2>
          <span>{loading ? "Загрузка" : `${operations.length} записей`}</span>
        </div>
        <p className="screen-note">
          Следите за щедростью всего сообщества.
        </p>
      </section>

      <section className="section">
        <OperationList
          operations={operations}
          emptyText="Пока нет операций для отображения."
          onRevealUser={onRevealUser}
          revealingKey={revealingKey}
        />
      </section>
    </main>
  );
}

function ReferralsScreen({
  referrals,
  loading,
  onCopyLink,
  onShareLink,
}) {
  const invitedUsers = referrals?.invited_users || [];
  const rewards = referrals?.rewards || [];
  const rewardSymbol = referrals?.reward_asset_symbol || "TDSD";

  return (
    <main className="screen">
      <section className="section referral-hero">
        <span className="eyebrow">Рефералы</span>
        <h2>Приглашайте друзей</h2>
        <p>
          Приглашайте друзей и получайте {referrals?.reward_percent || "10"}% от их покупок {rewardSymbol}.
        </p>
      </section>

      <section className="stats-grid">
        <Stat
          label="Приглашено"
          value={loading ? "..." : referrals?.invited_count ?? 0}
        />
        <Stat
          label="Получено"
          value={`${referrals?.total_reward_display || "0"} ${rewardSymbol}`}
        />
      </section>

      <section className="section">
        <div className="section-title">
          <h2>Ваша ссылка</h2>
          <span>{referrals?.referral_code || "..."}</span>
        </div>
        <div className="referral-link-box">
          <span>{referrals?.referral_link || "Ссылка загружается..."}</span>
        </div>
        <div className="referral-actions">
          <button
            className="secondary"
            disabled={!referrals?.referral_link}
            onClick={onCopyLink}
            type="button"
          >
            Скопировать
          </button>
          <button
            className="primary"
            disabled={!referrals?.referral_link}
            onClick={onShareLink}
            type="button"
          >
            Поделиться
          </button>
        </div>
      </section>

      <section className="section">
        <div className="section-title">
          <h2>Приглашенные</h2>
          <span>{invitedUsers.length}</span>
        </div>
        {invitedUsers.length ? (
          <div className="list">
            {invitedUsers.map((invited) => (
              <article className="operation-row" key={invited.user_id}>
                <div>
                  <strong>{invited.display_name}</strong>
                  <span>
                    {invited.invited_at
                      ? `С ${formatDate(invited.invited_at)}`
                      : "Приглашен"}
                  </span>
                  <p>
                    Покупки: {invited.total_purchases_display} {rewardSymbol}
                  </p>
                </div>
                <b className={invited.total_reward_tdsd > 0 ? "positive" : ""}>
                  {invited.total_reward_display} {rewardSymbol}
                </b>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty">
            Пока вы никого не пригласили. Поделитесь ссылкой и получите 10% от покупки друга.
          </p>
        )}
      </section>

      <section className="section">
        <div className="section-title">
          <h2>История наград</h2>
          <span>{rewards.length}</span>
        </div>
        {rewards.length ? (
          <div className="list">
            {rewards.map((reward) => (
              <article className="ledger-row" key={reward.id}>
                <div>
                  <strong>{reward.referred_user_display_name}</strong>
                  <span>{formatDate(reward.created_at)} · {reward.status}</span>
                  <p>
                    Покупка: {reward.purchase_amount_display} {rewardSymbol}
                  </p>
                </div>
                <b className={reward.status === "credited" ? "positive" : ""}>
                  +{reward.reward_amount_display} {rewardSymbol}
                </b>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty">История наград появится после покупок приглашенных пользователей.</p>
        )}
      </section>

      <section className="section">
        <div className="section-title">
          <h2>Правила</h2>
        </div>
        <div className="rules-list">
          <p>Вознаграждение начисляется после успешной покупки TDSD приглашенным пользователем.</p>
          <p>Система одноуровневая.</p>
          <p>Пригласивший фиксируется один раз.</p>
        </div>
      </section>
    </main>
  );
}

function ProfileScreen({
  user,
  telegramMode,
  telegramPhotoUrl,
  onSwitchMockUser,
  authLoading,
  connectedAddress,
  savedWallet,
  walletLoading,
  walletSaving,
  onOpenTonConnect,
  onSaveWallet,
  onDisconnectWallet,
  mockAllowed,
  assetBalances,
  depositProps,
}) {
  const [profileInfo, setProfileInfo] = useState(null);
  const avatarPhotoUrl = user.photo_url || telegramPhotoUrl;
  const savedAddress = savedWallet?.wallet_address || user.ton_wallet_address || "";
  const savedAt = savedWallet?.connected_at || user.ton_wallet_connected_at;
  const hasConnectedWallet = Boolean(connectedAddress);
  const hasSavedWallet = Boolean(savedAddress);
  const visibleAddress = connectedAddress || savedAddress;
  const isCurrentAddressSaved =
    Boolean(connectedAddress) && connectedAddress === savedAddress;
  const isDifferentWallet =
    Boolean(connectedAddress) &&
    Boolean(savedAddress) &&
    connectedAddress !== savedAddress;

  let walletStateText = "Кошелек не подключен";
  if (walletLoading) {
    walletStateText = "Проверяем кошелек...";
  } else if (isDifferentWallet) {
    walletStateText = "Подключенный кошелек отличается от сохраненного";
  } else if (hasConnectedWallet && isCurrentAddressSaved) {
    walletStateText = "Кошелек сохранен в профиле";
  } else if (hasConnectedWallet) {
    walletStateText = "Кошелек подключен, но еще не сохранен";
  } else if (hasSavedWallet) {
    walletStateText = "Адрес сохранен, кошелек сейчас отключен";
  }

  return (
    <>
    <main className="screen">
      <section className="profile">
        <span className="avatar">
          {avatarPhotoUrl ? (
            <img alt={displayName(user)} src={avatarPhotoUrl} />
          ) : (
            (user.first_name || user.username || "T").slice(0, 1)
          )}
        </span>
        <h2>{displayName(user)}</h2>
        <p>ID: {user.telegram_id}</p>
      </section>

      <section className="stats-grid">
        <Stat label="Ранг" onClick={() => setProfileInfo("rank")} value={user.rank} />
        <Stat label="Карма" onClick={() => setProfileInfo("karma")} value={user.karma} />
        <Stat label="TDSD" value={primaryBalance(userAssets(assetBalances))?.balance_display || "0"} />
      </section>

      <section className="section">
        <div className="section-title">
          <h2>Балансы</h2>
          <span>TDSD</span>
        </div>
        <AssetBalanceList
          balances={userAssets(assetBalances)}
          emptyText="Балансы появятся после первого депозита или синхронизации."
        />
      </section>

      <section className="section wallet-section">
        <div className="section-title">
          <h2>Кошелек</h2>
        </div>
        <div className="wallet-state">
          <span
            className={
              hasConnectedWallet || hasSavedWallet
                ? "wallet-dot connected"
                : "wallet-dot"
            }
          />
          <strong>{walletStateText}</strong>
        </div>
        {visibleAddress ? (
          <div className="wallet-address">
            <span>{hasConnectedWallet ? "Подключенный" : "Сохраненный"}</span>
            <b>{shortenAddress(visibleAddress)}</b>
          </div>
        ) : null}
        {isDifferentWallet ? (
          <p className="wallet-warning">
            Подключенный кошелек отличается от сохраненного. Сохраните новый
            адрес или отключите кошелек.
          </p>
        ) : null}
        {isDifferentWallet ? (
          <div className="wallet-address muted">
            <span>Сохраненный</span>
            <b>{shortenAddress(savedAddress)}</b>
          </div>
        ) : null}
        {savedAt ? (
          <p className="wallet-note">Сохранен: {formatDate(savedAt)}</p>
        ) : null}
        <div className="wallet-actions">
          {!hasConnectedWallet ? (
            <button
              className="primary"
              disabled={walletLoading || walletSaving}
              onClick={onOpenTonConnect}
              type="button"
            >
              Подключить кошелек
            </button>
          ) : (
            <>
              <button
                className="primary"
                disabled={walletLoading || walletSaving || isCurrentAddressSaved}
                onClick={onSaveWallet}
                type="button"
              >
                {walletSaving ? "Сохраняем..." : "Сохранить кошелек"}
              </button>
              <button
                className="secondary"
                disabled={walletLoading || walletSaving}
                onClick={onDisconnectWallet}
                type="button"
              >
                Отключить кошелек
              </button>
            </>
          )}
          {!hasConnectedWallet && hasSavedWallet ? (
            <button
              className="secondary"
              disabled={walletLoading || walletSaving}
              onClick={onDisconnectWallet}
              type="button"
            >
              Отключить кошелек
            </button>
          ) : null}
        </div>
      </section>

      <TonTopUpScreen {...depositProps} />

      {!telegramMode && mockAllowed ? (
        <section className="section">
          <div className="section-title">
            <h2>Тестовый пользователь</h2>
          </div>
          <div className="mock-users">
            {TEST_USERS.map((mockUser) => (
              <button
                className={mockUser.telegram_id === user.telegram_id ? "active" : ""}
                disabled={authLoading}
                key={mockUser.telegram_id}
                onClick={() => onSwitchMockUser(mockUser)}
                type="button"
              >
                {displayName(mockUser)}
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </main>
    <ProfileInfoSheet
      onClose={() => setProfileInfo(null)}
      type={profileInfo}
      user={user}
    />
    </>
  );
}

function BottomNav({ activeTab, onChange }) {
  return (
    <nav
      className="bottom-nav"
      style={{ gridTemplateColumns: `repeat(${MENU.length}, minmax(0, 1fr))` }}
    >
      {MENU.map((item) => (
        <button
          className={activeTab === item.id ? "active" : ""}
          key={item.id}
          onClick={() => onChange(item.id)}
          type="button"
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}

export default function App() {
  const [tonConnectUI] = useTonConnectUI();
  const tonWallet = useTonWallet();
  const [activeTab, setActiveTab] = useState("home");
  const [dashboard, setDashboard] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [leaderboard, setLeaderboard] = useState(null);
  const [savedWallet, setSavedWallet] = useState(null);
  const [tonDeposits, setTonDeposits] = useState([]);
  const [tonBalanceNano, setTonBalanceNano] = useState("0");
  const [assets, setAssets] = useState([]);
  const [assetBalances, setAssetBalances] = useState([]);
  const [assetLedger, setAssetLedger] = useState([]);
  const [assetGifts, setAssetGifts] = useState([]);
  const [assetGiftFeed, setAssetGiftFeed] = useState([]);
  const [publicTransactions, setPublicTransactions] = useState([]);
  const [assetGiftLeaderboard, setAssetGiftLeaderboard] = useState(null);
  const [feeConfig, setFeeConfig] = useState(DEFAULT_FEE_CONFIG);
  const [referrals, setReferrals] = useState(null);
  const [currentDeposit, setCurrentDeposit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [assetGiftSending, setAssetGiftSending] = useState(false);
  const [walletLoading, setWalletLoading] = useState(false);
  const [walletSaving, setWalletSaving] = useState(false);
  const [depositLoading, setDepositLoading] = useState(false);
  const [paying, setPaying] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [publicTransactionsLoading, setPublicTransactionsLoading] = useState(false);
  const [referralsLoading, setReferralsLoading] = useState(false);
  const [revealingKey, setRevealingKey] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const telegramMode = useMemo(() => isTelegramMode(), [dashboard]);
  const telegramPhotoUrl = useMemo(() => getTelegramUserPhotoUrl(), [dashboard]);
  const connectedTonAddress = tonWallet?.account?.address || "";
  const homeTonAddress =
    dashboard?.user.ton_wallet_address ||
    savedWallet?.wallet_address ||
    connectedTonAddress;
  const recentOperations = newestFirst([
    ...assetGifts.map(assetGiftOperation),
  ]).slice(0, 5);
  const sendProps = {
    assetBalances,
    assetGiftSending,
    balance: dashboard?.user.balance || 0,
    feeConfig,
    onSend: handleSendGift,
    onSendAssetGift: handleSendAssetGift,
    sending,
  };
  const depositProps = {
    assetBalances,
    assets,
    connectedAddress: connectedTonAddress,
    currentDeposit,
    depositLoading,
    deposits: tonDeposits,
    feeConfig,
    onCreateDeposit: handleCreateTonDeposit,
    onCopyPaymentAddress: handleCopyPaymentAddress,
    onPayDeposit: handlePayTonDeposit,
    onVerifyDeposit: handleVerifyTonDeposit,
    paying,
    savedWallet,
    tonBalanceNano,
    verifying,
  };

  async function loadDashboard() {
    const data = await api.getMe();
    setDashboard(data);
  }

  async function loadTransactions() {
    const data = await api.getTransactions();
    setTransactions(data);
  }

  async function loadPublicTransactions() {
    setPublicTransactionsLoading(true);
    try {
      const data = await api.getPublicTransactions();
      setPublicTransactions(
        data.filter(
          (item) =>
            item.token !== "TON" &&
            item.source_type !== "fee" &&
            item.source_type !== "virtual_gift",
        ),
      );
    } finally {
      setPublicTransactionsLoading(false);
    }
  }

  async function loadLeaderboard() {
    const data = await api.getLeaderboard();
    setLeaderboard(data);
  }

  async function loadWallet() {
    setWalletLoading(true);
    try {
      const data = await api.getWallet();
      setSavedWallet(data);
    } finally {
      setWalletLoading(false);
    }
  }

  async function loadFeeConfig() {
    const data = await api.getFeeConfig();
    setFeeConfig({ ...DEFAULT_FEE_CONFIG, ...data });
  }

  async function loadReferrals() {
    setReferralsLoading(true);
    try {
      const data = await api.getReferrals();
      setReferrals(data);
    } finally {
      setReferralsLoading(false);
    }
  }

  async function loadTonData() {
    const [balance, deposits] = await Promise.all([
      api.getTonBalance(),
      api.getAssetDeposits(),
    ]);
    setTonBalanceNano(readTonBalanceNano(balance));
    setTonDeposits(deposits.filter((deposit) => depositSymbol(deposit) === USER_ASSET_SYMBOL));
  }

  async function loadAssetData() {
    const commonRequests = [
      api.getAssets(),
      api.getAssetBalances(),
      api.getAssetLedger(),
      api.getAssetGifts(),
      api.getAssetGiftFeed(),
      api.getAssetGiftLeaderboard(USER_ASSET_SYMBOL),
    ];
    const [
      assetRows,
      balanceRows,
      ledgerRows,
      giftRows,
      giftFeedRows,
      giftLeaderboardRows,
    ] =
      await Promise.all(commonRequests);
    setAssets(assetRows);
    setAssetBalances(balanceRows);
    setAssetLedger(
      ledgerRows.filter(
        (entry) => entry.symbol === USER_ASSET_SYMBOL && !isFeeLedgerEntry(entry),
      ),
    );
    setAssetGifts(giftRows.filter((gift) => gift.symbol === USER_ASSET_SYMBOL));
    setAssetGiftFeed(giftFeedRows.filter((gift) => gift.symbol === USER_ASSET_SYMBOL));
    setAssetGiftLeaderboard(giftLeaderboardRows);
  }

  async function authenticate(mockUser = null) {
    setAuthLoading(true);
    setError("");
    try {
      initTelegramWebApp();
      const initData = getTelegramInitData();
      const referralParam = getTelegramStartParam();
      let payload;
      if (initData) {
        payload = { initData, referralParam };
      } else if (ENABLE_MOCK_AUTH) {
        payload = {
          mock: true,
          mock_user: mockUser || getMockUser(),
          referralParam,
        };
      } else {
        throw new Error("Откройте приложение внутри Telegram");
      }
      const auth = await api.authTelegram(payload);
      setAccessToken(auth.access_token);
      await Promise.all([
        loadDashboard(),
        loadTransactions(),
        loadLeaderboard(),
        loadWallet(),
        loadFeeConfig(),
        loadTonData(),
        loadAssetData(),
        loadReferrals(),
      ]);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setLoading(false);
      setAuthLoading(false);
    }
  }

  async function handleSendGift(payload) {
    setSending(true);
    setError("");
    setSuccess("");
    try {
      const result = await api.sendGift(payload);
      setSuccess(result.message);
      await Promise.all([loadDashboard(), loadTransactions(), loadLeaderboard()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  async function handleSendAssetGift(payload) {
    setAssetGiftSending(true);
    setError("");
    setSuccess("");
    try {
      const result = await api.sendAssetGift(payload);
      setSuccess(result.message);
      await Promise.all([loadDashboard(), loadAssetData(), loadReferrals()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setAssetGiftSending(false);
    }
  }

  async function handleOpenTonConnect() {
    setError("");
    try {
      await tonConnectUI.openModal();
    } catch (err) {
      setError(userDepositMessage(err.message || "Не удалось открыть кошелек"));
    }
  }

  async function ensurePurchaseWalletSaved() {
    if (!connectedTonAddress) {
      throw new Error("Сначала подключите кошелек");
    }
    const savedAddress = savedWallet?.wallet_address || dashboard?.user.ton_wallet_address || "";
    if (savedAddress === connectedTonAddress) {
      return;
    }

    setWalletSaving(true);
    try {
      const updatedUser = await api.connectWallet(connectedTonAddress);
      setDashboard((current) =>
        current ? { ...current, user: updatedUser } : current,
      );
      setSavedWallet({
        wallet_address: updatedUser.ton_wallet_address,
        connected_at: updatedUser.ton_wallet_connected_at,
      });
    } catch {
      throw new Error("Не удалось сохранить подключенный кошелек");
    } finally {
      setWalletSaving(false);
    }
  }

  async function handleSaveWallet() {
    if (!connectedTonAddress) {
      setError("Сначала подключите кошелек");
      return;
    }
    setWalletSaving(true);
    setError("");
    setSuccess("");
    try {
      const updatedUser = await api.connectWallet(connectedTonAddress);
      setDashboard((current) =>
        current ? { ...current, user: updatedUser } : current,
      );
      setSavedWallet({
        wallet_address: updatedUser.ton_wallet_address,
        connected_at: updatedUser.ton_wallet_connected_at,
      });
      setSuccess("Кошелек сохранен");
    } catch (err) {
      setError(userDepositMessage(err.message));
    } finally {
      setWalletSaving(false);
    }
  }

  async function handleDisconnectWallet() {
    setWalletSaving(true);
    setError("");
    setSuccess("");
    try {
      const updatedUser = await api.disconnectWallet();
      if (connectedTonAddress) {
        await tonConnectUI.disconnect();
      }
      setDashboard((current) =>
        current ? { ...current, user: updatedUser } : current,
      );
      setSavedWallet({
        wallet_address: updatedUser.ton_wallet_address,
        connected_at: updatedUser.ton_wallet_connected_at,
      });
      setSuccess("Кошелек отключен");
    } catch (err) {
      setError(userDepositMessage(err.message));
    } finally {
      setWalletSaving(false);
    }
  }

  async function handleCreateTonDeposit(asset, amountDisplay) {
    const normalizedAmount = String(amountDisplay).replace(",", ".").trim();
    let amountUnits = 0n;
    try {
      amountUnits = BigInt(displayAmountToUnits(normalizedAmount, asset.decimals));
    } catch {
      amountUnits = 0n;
    }
    if (amountUnits <= 0n) {
      setError(`Введите корректную сумму ${asset.symbol}`);
      return;
    }
    setDepositLoading(true);
    setError("");
    setSuccess("");
    try {
      await ensurePurchaseWalletSaved();
      const deposit = await api.createAssetDeposit({
        asset_symbol: asset.symbol,
        amount_units: amountUnits.toString(),
      });
      setCurrentDeposit(deposit);
      await Promise.all([loadTonData(), loadAssetData()]);
      setSuccess(
        deposit.provider === "tdsd_fixed_price"
          ? `Покупка TDSD создана. Оплатите ${deposit.payment_amount_ton} TON через кошелек или по адресу ниже.`
          : "Пополнение создано. Завершите перевод в кошельке.",
      );
    } catch (err) {
      setError(userDepositMessage(err.message));
    } finally {
      setDepositLoading(false);
    }
  }

  async function handlePayTonDeposit(deposit) {
    if (
      deposit.provider &&
      !["ton_native", "tdsd_fixed_price"].includes(deposit.provider)
    ) {
      setError("Автоматическая оплата временно недоступна для TDSD");
      return;
    }
    if (!connectedTonAddress) {
      setError("Сначала подключите кошелек");
      return;
    }
    setPaying(true);
    setError("");
    setSuccess("");
    try {
      await tonConnectUI.sendTransaction({
        validUntil: Math.floor(Date.now() / 1000) + 600,
        messages: [
          {
            address: deposit.payment_address || deposit.target_wallet_address,
            amount: depositPaymentAmountUnits(deposit),
            payload: encodeTonTextCommentPayload(deposit.comment),
          },
        ],
      });
      setSuccess("Транзакция отправлена. Проверьте статус через 5-20 секунд.");
    } catch (err) {
      setError(userDepositMessage(err.message || "Транзакция не выполнена"));
    } finally {
      setPaying(false);
    }
  }

  async function handleCopyPaymentAddress(address) {
    if (!address) return;
    await copyTextToClipboard(address);
    setSuccess("Адрес для оплаты скопирован");
  }

  async function handleVerifyTonDeposit(depositId) {
    if (!depositId) {
      setError("Сначала создайте пополнение");
      return;
    }
    setVerifying(true);
    setError("");
    setSuccess("");
    try {
      const result = await api.verifyAssetDeposit(depositId);
      setCurrentDeposit(result.deposit);
      if (result.asset_balance?.symbol === "TON") {
        setTonBalanceNano(String(result.asset_balance.balance_units || "0"));
      }
      await Promise.all([loadTonData(), loadAssetData(), loadReferrals()]);
      if (result.deposit.status === "confirmed") {
        if (result.deposit.payout_status === "failed") {
          setError(
            userDepositMessage(
              result.deposit.payout_failed_reason || result.message || "Ошибка отправки, обратитесь в поддержку",
            ),
          );
        } else {
          setSuccess(userDepositMessage(result.message || purchaseStatusLabel(result.deposit)));
        }
      } else if (result.deposit.status === "failed") {
        setError(userDepositMessage(result.deposit.failed_reason || result.message));
      } else {
        setSuccess(userDepositMessage(result.message));
      }
    } catch (err) {
      setError(userDepositMessage(err.message));
    } finally {
      setVerifying(false);
    }
  }

  async function handleSwitchMockUser(user) {
    if (!ENABLE_MOCK_AUTH) {
      setError("Mock mode отключен");
      return;
    }
    setMockUser(user);
    setAccessToken("");
    const ok = await authenticate(user);
    if (ok) {
      setSuccess(`Вы вошли как ${displayName(user)}`);
    }
  }

  async function handleCopyReferralLink() {
    if (!referrals?.referral_link) return;
    setError("");
    try {
      await copyTextToClipboard(referrals.referral_link);
      setSuccess("Ссылка скопирована");
    } catch {
      setError("Не удалось скопировать ссылку");
    }
  }

  async function handleShareReferralLink() {
    if (!referrals?.referral_link) return;
    setError("");
    const webApp = getTelegramWebApp();
    try {
      const shareUrl = buildTelegramShareUrl(referrals.referral_link);
      if (webApp?.openTelegramLink) {
        webApp.openTelegramLink(shareUrl);
        return;
      }
      if (navigator.share) {
        await navigator.share({
          title: "Tuda Suda",
          text: "Присоединяйтесь к Tuda Suda",
          url: referrals.referral_link,
        });
        return;
      }
      await handleCopyReferralLink();
    } catch (err) {
      try {
        await copyTextToClipboard(referrals.referral_link);
        setSuccess("Ссылка скопирована");
      } catch {
        setError(err.message || "Не удалось поделиться ссылкой");
      }
    }
  }

  async function handleRevealUser(target) {
    if (!target) return;
    const key = revealTargetKey(target);
    setRevealingKey(key);
    setError("");
    setSuccess("");
    try {
      const result = await api.revealUser(target);
      setSuccess(
        result.charged
          ? `Пользователь раскрыт за ${result.price_display} TDSD`
          : "Пользователь уже раскрыт",
      );
      await Promise.all([
        loadDashboard(),
        loadPublicTransactions(),
        loadAssetData(),
        loadLeaderboard(),
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setRevealingKey("");
    }
  }

  useEffect(() => {
    authenticate();
  }, []);

  useEffect(() => {
    if (!dashboard) return;
    if (activeTab === "home") {
      Promise.all([loadTransactions(), loadAssetData()]).catch((err) =>
        setError(err.message),
      );
    }
    if (activeTab === "all") {
      Promise.all([
        loadPublicTransactions(),
      ]).catch((err) => setError(err.message));
    }
    if (activeTab === "referrals") {
      loadReferrals().catch((err) => setError(err.message));
    }
    if (activeTab === "profile") {
      Promise.all([loadWallet(), loadTonData(), loadAssetData()]).catch((err) =>
        setError(err.message),
      );
    }
  }, [activeTab, dashboard]);

  if (loading) {
    return (
      <div className="app-shell center">
        <div className="loader" />
        <p>Открываем Туда-Сюда...</p>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Notice type="error" onClose={() => setError("")}>
        {error}
      </Notice>
      <Notice type="success" onClose={() => setSuccess("")}>
        {success}
      </Notice>

      {!dashboard ? (
        <main className="screen center">
          <h1>Не удалось войти</h1>
          <button className="primary" onClick={() => authenticate()} type="button">
            Повторить
          </button>
        </main>
      ) : null}

      {dashboard && activeTab === "home" ? (
        <HomeScreen
          assetBalances={assetBalances}
          dashboard={dashboard}
          onRevealUser={handleRevealUser}
          recentOperations={recentOperations}
          revealingKey={revealingKey}
          sendProps={sendProps}
          tonAddress={homeTonAddress}
        />
      ) : null}
      {dashboard && activeTab === "all" ? (
        <AllTransactionsScreen
          loading={publicTransactionsLoading}
          onRevealUser={handleRevealUser}
          publicTransactions={publicTransactions}
          revealingKey={revealingKey}
        />
      ) : null}
      {dashboard && activeTab === "referrals" ? (
        <ReferralsScreen
          loading={referralsLoading}
          onCopyLink={handleCopyReferralLink}
          onShareLink={handleShareReferralLink}
          referrals={referrals}
        />
      ) : null}
      {dashboard && activeTab === "profile" ? (
        <ProfileScreen
          assetBalances={assetBalances}
          authLoading={authLoading}
          connectedAddress={connectedTonAddress}
          depositProps={depositProps}
          onSwitchMockUser={handleSwitchMockUser}
          onDisconnectWallet={handleDisconnectWallet}
          onOpenTonConnect={handleOpenTonConnect}
          onSaveWallet={handleSaveWallet}
          savedWallet={savedWallet}
          mockAllowed={ENABLE_MOCK_AUTH}
          telegramPhotoUrl={telegramPhotoUrl}
          telegramMode={telegramMode}
          user={dashboard.user}
          walletLoading={walletLoading}
          walletSaving={walletSaving}
        />
      ) : null}

      <BottomNav activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}
