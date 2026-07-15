const ADMIN_API_URL = (import.meta.env.VITE_ADMIN_API_URL || "/admin-api").replace(
  /\/$/,
  "",
);

async function adminRequest(path) {
  const response = await fetch(`${ADMIN_API_URL}${path}`, {
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
    },
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error("Доступ к admin-панели не разрешён");
    }
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((item) => item.msg).join(", ")
      : data?.detail;
    throw new Error(detail || `Ошибка загрузки (${response.status})`);
  }
  return data;
}

export const adminApi = {
  getOverview(period) {
    return adminRequest(
      `/dashboard/overview?period=${encodeURIComponent(period)}`,
    );
  },
  getTimeseries(days) {
    return adminRequest(`/dashboard/timeseries?days=${days}`);
  },
  getActivity(limit = 12) {
    return adminRequest(`/dashboard/activity?limit=${limit}`);
  },
  getUsers({ query = "", limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (query) params.set("query", query);
    return adminRequest(`/dashboard/users?${params.toString()}`);
  },
};
