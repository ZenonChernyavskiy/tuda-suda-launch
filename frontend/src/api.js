const API_URL = import.meta.env.VITE_API_URL || "";
const ADMIN_API_KEY = import.meta.env.VITE_ADMIN_API_KEY || "";

if (!API_URL && import.meta.env.PROD) {
  throw new Error("VITE_API_URL is required for production build");
}

let accessToken = localStorage.getItem("tuda_suda_token") || "";

export function setAccessToken(token) {
  accessToken = token;
  if (token) {
    localStorage.setItem("tuda_suda_token", token);
  } else {
    localStorage.removeItem("tuda_suda_token");
  }
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  if (ADMIN_API_KEY && path.startsWith("/admin")) {
    headers["X-Admin-Token"] = ADMIN_API_KEY;
  }

  const response = await fetch(`${API_URL || "http://localhost:8000"}${path}`, {
    ...options,
    headers,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((item) => item.msg).join(", ")
      : data?.detail;
    throw new Error(detail || "Запрос не выполнен");
  }

  return data;
}

export const api = {
  authTelegram(payload) {
    return request("/auth/telegram", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getMe() {
    return request("/me");
  },
  sendGift(payload) {
    return request("/gift/send", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getTransactions() {
    return request("/transactions");
  },
  getPublicTransactions() {
    return request("/transactions/public");
  },
  getReferrals() {
    return request("/referrals/me");
  },
  getLeaderboard() {
    return request("/leaderboard");
  },
  connectWallet(address) {
    return request("/wallet/connect", {
      method: "POST",
      body: JSON.stringify({ wallet_address: address }),
    });
  },
  getWallet() {
    return request("/wallet/me");
  },
  disconnectWallet() {
    return request("/wallet/disconnect", {
      method: "DELETE",
    });
  },
  getFeeConfig() {
    return request("/fees/config");
  },
  getTransferFeeQuote(payload) {
    return request("/fees/transfer/quote", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getPurchaseFeeQuote(payload) {
    return request("/fees/purchase/quote", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  createTonDeposit(payload) {
    return request("/ton/deposits/create", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  verifyTonDeposit(depositId) {
    return request(`/ton/deposits/${depositId}/verify`, {
      method: "POST",
    });
  },
  getTonDeposits() {
    return request("/ton/deposits");
  },
  getTonBalance() {
    return request("/ton/balance");
  },
  createAssetDeposit(payload) {
    return request("/asset-deposits/create", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  verifyAssetDeposit(depositId) {
    return request(`/asset-deposits/${depositId}/verify`, {
      method: "POST",
    });
  },
  getAssetDeposits() {
    return request("/asset-deposits");
  },
  getAssets() {
    return request("/assets");
  },
  getAdminAssets() {
    return request("/admin/assets");
  },
  createAdminAsset(payload) {
    return request("/admin/assets/create", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getAssetBalances() {
    return request("/assets/balances");
  },
  getAssetLedger() {
    return request("/assets/ledger");
  },
  getAssetBalance(symbol) {
    return request(`/assets/${encodeURIComponent(symbol)}/balance`);
  },
  sendAssetGift(payload) {
    return request("/asset-gifts/send-random", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getAssetGifts() {
    return request("/asset-gifts");
  },
  getAssetGiftFeed() {
    return request("/asset-gifts/feed");
  },
  getAssetGiftLeaderboard(symbol = "TDSD") {
    return request(`/asset-gifts/leaderboard?symbol=${encodeURIComponent(symbol)}`);
  },
  getGlobalLedger(filters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        params.set(key, String(value).trim());
      }
    });
    const query = params.toString();
    return request(`/admin/ledger/all${query ? `?${query}` : ""}`);
  },
};
