export const TEST_USERS = [
  { telegram_id: "1001", username: "demo_user", first_name: "Demo" },
  { telegram_id: "1002", username: "alina", first_name: "Алина" },
  { telegram_id: "1003", username: "maxim", first_name: "Максим" },
  { telegram_id: "1004", username: "vera", first_name: "Вера" },
  { telegram_id: "1005", username: "timur", first_name: "Тимур" },
  { telegram_id: "1006", username: "sofia", first_name: "София" },
];

const MOCK_USER_KEY = "tuda_suda_mock_user";

export function getTelegramWebApp() {
  return window.Telegram?.WebApp || null;
}

export function initTelegramWebApp() {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    return null;
  }
  webApp.ready();
  webApp.expand();
  return webApp;
}

export function getTelegramInitData() {
  const webApp = getTelegramWebApp();
  return webApp?.initData || "";
}

export function getTelegramStartParam() {
  const webApp = getTelegramWebApp();
  const telegramParam =
    webApp?.initDataUnsafe?.start_param ||
    webApp?.initDataUnsafe?.startapp ||
    "";
  if (telegramParam) {
    return telegramParam;
  }
  const params = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const webAppData = hashParams.get("tgWebAppData");
  const webAppDataParams = webAppData ? new URLSearchParams(webAppData) : null;
  return (
    params.get("startapp") ||
    params.get("start") ||
    params.get("ref") ||
    hashParams.get("tgWebAppStartParam") ||
    webAppDataParams?.get("start_param") ||
    hashParams.get("startapp") ||
    hashParams.get("start") ||
    hashParams.get("ref") ||
    ""
  );
}

export function getTelegramUserPhotoUrl() {
  const webApp = getTelegramWebApp();
  return webApp?.initDataUnsafe?.user?.photo_url || "";
}

export function isTelegramMode() {
  return Boolean(getTelegramInitData());
}

export function getMockUser() {
  const stored = localStorage.getItem(MOCK_USER_KEY);
  if (stored) {
    return JSON.parse(stored);
  }
  localStorage.setItem(MOCK_USER_KEY, JSON.stringify(TEST_USERS[0]));
  return TEST_USERS[0];
}

export function setMockUser(user) {
  localStorage.setItem(MOCK_USER_KEY, JSON.stringify(user));
}
