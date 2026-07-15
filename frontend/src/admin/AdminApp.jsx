import { Fragment, useCallback, useEffect, useMemo, useState } from "react";

import { adminApi } from "./api.js";


const PERIODS = [
  { id: "today", label: "Сегодня", chartDays: 7 },
  { id: "7d", label: "7 дней", chartDays: 7 },
  { id: "30d", label: "30 дней", chartDays: 30 },
  { id: "all", label: "Всё время", chartDays: 90 },
];
const USERS_PAGE_SIZE = 50;

const integerFormatter = new Intl.NumberFormat("ru-RU");
const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "2-digit",
  year: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});
const shortDateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "2-digit",
});

function formatInteger(value) {
  return integerFormatter.format(Number(value || 0));
}

function formatUsersCount(value) {
  const count = Number(value || 0);
  const mod100 = count % 100;
  const mod10 = count % 10;
  let noun = "пользователей";
  if (mod100 < 11 || mod100 > 14) {
    if (mod10 === 1) noun = "пользователь";
    else if (mod10 >= 2 && mod10 <= 4) noun = "пользователя";
  }
  return `${formatInteger(count)} ${noun}`;
}

function formatDate(value) {
  if (!value) return "—";
  return dateFormatter.format(new Date(value));
}

function compactWallet(value) {
  if (!value) return "Не подключён";
  if (value.length <= 18) return value;
  return `${value.slice(0, 8)}…${value.slice(-8)}`;
}

function userInitial(user) {
  const value = user.first_name || user.username || user.telegram_id || "U";
  return value.trim().slice(0, 1).toUpperCase();
}

function statusLabel(status) {
  const labels = {
    pending: "Ожидает",
    confirmed: "Подтверждена",
    sent: "Отправлено",
    failed: "Ошибка",
    completed: "Завершён",
    cancelled: "Отменён",
  };
  return labels[status] || status || "—";
}

function statusTone(status) {
  if (["sent", "confirmed", "completed"].includes(status)) return "success";
  if (["failed", "cancelled"].includes(status)) return "danger";
  return "warning";
}

function StatusBadge({ status }) {
  return (
    <span className={`status-badge ${statusTone(status)}`}>
      {statusLabel(status)}
    </span>
  );
}

function MetricCard({ label, value, detail, tone = "blue" }) {
  return (
    <article className={`metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail || "\u00a0"}</small>
    </article>
  );
}

function BarChart({ title, points, valueKey, tooltipValue, tone }) {
  const values = points.map((point) => Number(point[valueKey] || 0));
  const maximum = Math.max(...values, 1);
  const middleIndex = Math.floor((points.length - 1) / 2);

  return (
    <section className="chart-panel">
      <div className="chart-heading">
        <h2>{title}</h2>
        <strong>{formatInteger(values.reduce((total, value) => total + value, 0))}</strong>
      </div>
      <div className="chart-scroll">
        <div
          className="chart-bars"
          style={{ "--chart-points": Math.max(points.length, 1) }}
        >
          {points.map((point, index) => {
            const value = Number(point[valueKey] || 0);
            const showLabel =
              index === 0 || index === middleIndex || index === points.length - 1;
            const titleText = `${shortDateFormatter.format(new Date(`${point.date}T00:00:00`))}: ${
              tooltipValue ? tooltipValue(point) : formatInteger(value)
            }`;
            return (
              <div className="chart-column" key={point.date} title={titleText}>
                <div className="chart-track">
                  <div
                    className={`chart-bar ${tone}`}
                    style={{
                      height: `${value > 0 ? Math.max(7, (value / maximum) * 100) : 2}%`,
                    }}
                  />
                </div>
                <span>{showLabel ? shortDateFormatter.format(new Date(`${point.date}T00:00:00`)) : ""}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function PurchasesTable({ rows }) {
  return (
    <div className="table-frame">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Пользователь</th>
            <th>TDSD</th>
            <th>Оплата TON</th>
            <th>Оплата</th>
            <th>Payout</th>
            <th>Создана</th>
            <th>Ошибка</th>
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row) => (
              <tr key={row.id}>
                <td>#{row.id}</td>
                <td>{row.user}</td>
                <td>{row.amount_display}</td>
                <td>{row.payment_amount_ton}</td>
                <td><StatusBadge status={row.status} /></td>
                <td><StatusBadge status={row.payout_status} /></td>
                <td>{formatDate(row.created_at)}</td>
                <td className={row.error ? "error-cell" : "muted-cell"}>
                  {row.error || "—"}
                </td>
              </tr>
            ))
          ) : (
            <tr><td className="empty-cell" colSpan="8">Покупок пока нет</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function GiftsTable({ rows }) {
  return (
    <div className="table-frame">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Отправитель</th>
            <th>Получатель</th>
            <th>Отправлено</th>
            <th>Получено</th>
            <th>Комиссия</th>
            <th>Статус</th>
            <th>Дата</th>
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row) => (
              <tr key={row.id}>
                <td>#{row.id}</td>
                <td>{row.sender}</td>
                <td>{row.receiver}</td>
                <td>{row.amount_display}</td>
                <td>{row.net_amount_display}</td>
                <td>{row.fee_display}</td>
                <td><StatusBadge status={row.status} /></td>
                <td>{formatDate(row.created_at)}</td>
              </tr>
            ))
          ) : (
            <tr><td className="empty-cell" colSpan="8">Подарков пока нет</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function UserDetail({ label, children, wide = false }) {
  return (
    <div className={wide ? "user-detail wide" : "user-detail"}>
      <span>{label}</span>
      <strong>{children || "—"}</strong>
    </div>
  );
}

function UsersTable({ rows }) {
  const [expandedUserId, setExpandedUserId] = useState(null);

  if (!rows.length) {
    return <div className="users-empty">Пользователи не найдены</div>;
  }

  return (
    <div className="table-frame users-table-frame">
      <table className="users-table">
        <thead>
          <tr>
            <th>Пользователь</th>
            <th>Telegram ID</th>
            <th>Баланс TDSD</th>
            <th>TON-кошелёк</th>
            <th>Подарки</th>
            <th>Последняя активность</th>
            <th aria-label="Действия" />
          </tr>
        </thead>
        <tbody>
          {rows.map((user) => {
            const isExpanded = expandedUserId === user.id;
            return (
              <Fragment key={user.id}>
                <tr>
                  <td>
                    <div className="user-identity">
                      <span className="user-initial">{userInitial(user)}</span>
                      <div>
                        <strong>{user.first_name || `User #${user.id}`}</strong>
                        <span>{user.username ? `@${user.username}` : "Без username"}</span>
                      </div>
                    </div>
                  </td>
                  <td><code>{user.telegram_id}</code></td>
                  <td><strong>{user.tdsd_balance_display}</strong></td>
                  <td>
                    <code className={user.ton_wallet_address ? "" : "muted-cell"}>
                      {compactWallet(user.ton_wallet_address)}
                    </code>
                  </td>
                  <td>
                    <span className="activity-pair">
                      <span>Отправлено {formatInteger(user.total_sent)}</span>
                      <span>Получено {formatInteger(user.total_received)}</span>
                    </span>
                  </td>
                  <td>{formatDate(user.last_active_at)}</td>
                  <td className="row-action-cell">
                    <button
                      aria-expanded={isExpanded}
                      className="details-button"
                      onClick={() => setExpandedUserId(isExpanded ? null : user.id)}
                      type="button"
                    >
                      {isExpanded ? "Скрыть" : "Подробнее"}
                    </button>
                  </td>
                </tr>
                {isExpanded ? (
                  <tr className="user-details-row">
                    <td colSpan="7">
                      <div className="user-details-grid">
                        <UserDetail label="Внутренний ID">{`#${user.id}`}</UserDetail>
                        <UserDetail label="Имя">{user.first_name}</UserDetail>
                        <UserDetail label="Username">
                          {user.username ? `@${user.username}` : null}
                        </UserDetail>
                        <UserDetail label="Фото профиля">
                          {user.photo_url ? (
                            <a href={user.photo_url} rel="noreferrer" target="_blank">Открыть</a>
                          ) : null}
                        </UserDetail>
                        <UserDetail label="TON-кошелёк" wide>
                          <code>{user.ton_wallet_address || "Не подключён"}</code>
                        </UserDetail>
                        <UserDetail label="Кошелёк сохранён">
                          {formatDate(user.ton_wallet_connected_at)}
                        </UserDetail>
                        <UserDetail label="Баланс TDSD">
                          {`${user.tdsd_balance_display} TDSD`}
                        </UserDetail>
                        <UserDetail label="Сохранённый TON-баланс">
                          {`${user.ton_balance_display} TON`}
                        </UserDetail>
                        <UserDetail label="Внутренний баланс">{formatInteger(user.balance)}</UserDetail>
                        <UserDetail label="Карма">{formatInteger(user.karma)}</UserDetail>
                        <UserDetail label="Репутация">{formatInteger(user.reputation)}</UserDetail>
                        <UserDetail label="Риск">{formatInteger(user.risk_score)}</UserDetail>
                        <UserDetail label="Вес сообщества">{formatInteger(user.community_weight)}</UserDetail>
                        <UserDetail label="Реферальный код">{user.referral_code}</UserDetail>
                        <UserDetail label="Пригласил">{user.referrer}</UserDetail>
                        <UserDetail label="Дата приглашения">{formatDate(user.referred_at)}</UserDetail>
                        <UserDetail label="Регистрация">{formatDate(user.created_at)}</UserDetail>
                        <UserDetail label="Последняя активность">{formatDate(user.last_active_at)}</UserDetail>
                      </div>
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function UsersView({ knownTotal }) {
  const [queryInput, setQueryInput] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [page, setPage] = useState(0);
  const [usersPage, setUsersPage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadUsers = useCallback(async (background = false) => {
    if (background) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const result = await adminApi.getUsers({
        query: submittedQuery,
        limit: USERS_PAGE_SIZE,
        offset: page * USERS_PAGE_SIZE,
      });
      setUsersPage(result);
    } catch (loadError) {
      setError(loadError.message || "Не удалось загрузить пользователей");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [page, submittedQuery]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const submitSearch = (event) => {
    event.preventDefault();
    const nextQuery = queryInput.trim();
    if (nextQuery === submittedQuery && page === 0) {
      loadUsers(true);
      return;
    }
    setPage(0);
    setSubmittedQuery(nextQuery);
  };

  const clearSearch = () => {
    setQueryInput("");
    setPage(0);
    if (submittedQuery) setSubmittedQuery("");
    else loadUsers(true);
  };

  const total = usersPage?.total ?? knownTotal ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / USERS_PAGE_SIZE));

  return (
    <main className="users-view">
      <section className="users-heading">
        <div>
          <h1>Пользователи</h1>
          <span>{formatUsersCount(total)}</span>
        </div>
        <button
          className="refresh-button"
          disabled={refreshing}
          onClick={() => loadUsers(true)}
          type="button"
        >
          {refreshing ? "Обновление" : "Обновить"}
        </button>
      </section>

      <form className="users-search" onSubmit={submitSearch}>
        <label htmlFor="admin-user-search">Поиск пользователей</label>
        <div>
          <input
            autoComplete="off"
            id="admin-user-search"
            maxLength="128"
            onChange={(event) => setQueryInput(event.target.value)}
            placeholder="Telegram ID, имя, username или TON-кошелёк"
            type="search"
            value={queryInput}
          />
          <button className="search-button" type="submit">Найти</button>
          {submittedQuery || queryInput ? (
            <button className="clear-button" onClick={clearSearch} type="button">Сбросить</button>
          ) : null}
        </div>
      </form>

      {error ? <div className="error-banner">{error}</div> : null}
      {loading && !usersPage ? (
        <div className="users-loading">Загрузка пользователей</div>
      ) : (
        <UsersTable rows={usersPage?.items || []} />
      )}

      <section className="pagination" aria-label="Навигация по страницам">
        <span>Страница {page + 1} из {pageCount}</span>
        <div>
          <button
            disabled={page === 0 || loading}
            onClick={() => setPage((value) => Math.max(0, value - 1))}
            type="button"
          >
            Назад
          </button>
          <button
            disabled={(page + 1) * USERS_PAGE_SIZE >= total || loading}
            onClick={() => setPage((value) => value + 1)}
            type="button"
          >
            Далее
          </button>
        </div>
      </section>
    </main>
  );
}

export default function AdminApp() {
  const [activeView, setActiveView] = useState("overview");
  const [period, setPeriod] = useState("30d");
  const [overview, setOverview] = useState(null);
  const [timeseries, setTimeseries] = useState(null);
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const chartDays = useMemo(
    () => PERIODS.find((item) => item.id === period)?.chartDays || 30,
    [period],
  );

  const loadDashboard = useCallback(async (background = false) => {
    if (background) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const [overviewData, timeseriesData, activityData] = await Promise.all([
        adminApi.getOverview(period),
        adminApi.getTimeseries(chartDays),
        adminApi.getActivity(12),
      ]);
      setOverview(overviewData);
      setTimeseries(timeseriesData);
      setActivity(activityData);
    } catch (loadError) {
      setError(loadError.message || "Не удалось загрузить статистику");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [chartDays, period]);

  useEffect(() => {
    if (activeView !== "overview") return undefined;
    loadDashboard();
    const intervalId = window.setInterval(() => loadDashboard(true), 60_000);
    return () => window.clearInterval(intervalId);
  }, [activeView, loadDashboard]);

  if (loading && !overview) {
    return (
      <main className="admin-state">
        <strong>Tuda Suda</strong>
        <span>Загрузка статистики</span>
      </main>
    );
  }

  if (!overview) {
    return (
      <main className="admin-state error-state">
        <strong>Данные недоступны</strong>
        <span>{error}</span>
        <button type="button" onClick={() => loadDashboard()}>
          Повторить
        </button>
      </main>
    );
  }

  const metrics = [
    {
      label: "Пользователи",
      value: formatInteger(overview.users.total),
      detail: `+${formatInteger(overview.users.new_in_period)} за период`,
      tone: "blue",
    },
    {
      label: "Активные",
      value: formatInteger(overview.users.active_in_period),
      detail: `DAU ${formatInteger(overview.users.active_1d)} · MAU ${formatInteger(overview.users.active_30d)}`,
      tone: "green",
    },
    {
      label: "TON-кошельки",
      value: formatInteger(overview.users.wallets_connected),
      detail: "Сохранённые подключения",
      tone: "cyan",
    },
    {
      label: "Подарки",
      value: formatInteger(overview.gifts.count),
      detail: `${overview.gifts.gross_display} TDSD отправлено`,
      tone: "orange",
    },
    {
      label: "Успешные покупки",
      value: formatInteger(overview.purchases.successful),
      detail: `${overview.purchases.purchased_display} TDSD`,
      tone: "green",
    },
    {
      label: "Расчётный объём TON",
      value: overview.purchases.payment_amount_ton,
      detail: `${formatInteger(overview.purchases.created)} заявок · текущая цена`,
      tone: "blue",
    },
    {
      label: "Доход проекта",
      value: `${overview.revenue.total_display} TDSD`,
      detail: `Переводы ${overview.revenue.transfer_fee_display} · Покупки ${overview.revenue.purchase_fee_display}`,
      tone: "orange",
    },
    {
      label: "Ошибки payout",
      value: formatInteger(overview.purchases.payout_failed),
      detail: `${formatInteger(overview.purchases.payout_pending)} ожидают`,
      tone: overview.purchases.payout_failed ? "red" : "green",
    },
  ];

  return (
    <div className="admin-shell">
      <header className="admin-header">
        <div className="admin-brand">
          <span className="brand-mark">TS</span>
          <div>
            <strong>Tuda Suda</strong>
            <span>Администрирование</span>
          </div>
        </div>
        <div className="admin-header-tools">
          <nav className="admin-tabs" aria-label="Разделы админ-панели">
            <button
              aria-current={activeView === "overview" ? "page" : undefined}
              className={activeView === "overview" ? "active" : ""}
              onClick={() => setActiveView("overview")}
              type="button"
            >
              Обзор
            </button>
            <button
              aria-current={activeView === "users" ? "page" : undefined}
              className={activeView === "users" ? "active" : ""}
              onClick={() => setActiveView("users")}
              type="button"
            >
              Пользователи
            </button>
          </nav>
          {activeView === "overview" ? (
            <div className="admin-actions">
              <div className="period-control" aria-label="Период статистики">
                {PERIODS.map((item) => (
                  <button
                    className={period === item.id ? "active" : ""}
                    key={item.id}
                    onClick={() => setPeriod(item.id)}
                    type="button"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <button
                className="refresh-button"
                disabled={refreshing}
                onClick={() => loadDashboard(true)}
                type="button"
              >
                {refreshing ? "Обновление" : "Обновить"}
              </button>
            </div>
          ) : null}
        </div>
      </header>

      {activeView === "overview" && error ? <div className="error-banner">{error}</div> : null}

      {activeView === "overview" ? (
      <main>
        <section className="metric-grid" aria-label="Основные показатели">
          {metrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}
        </section>

        <section className="section-band">
          <div className="section-heading">
            <div>
              <h1>Динамика</h1>
              <span>Последние {timeseries?.days || chartDays} дней</span>
            </div>
            <span>Обновлено {formatDate(overview.generated_at)}</span>
          </div>
          <div className="charts-grid">
            <BarChart
              points={timeseries?.points || []}
              title="Новые пользователи"
              tone="blue"
              valueKey="new_users"
            />
            <BarChart
              points={timeseries?.points || []}
              title="Подарки"
              tone="orange"
              valueKey="gifts_count"
            />
            <BarChart
              points={timeseries?.points || []}
              title="Покупки"
              tone="green"
              valueKey="purchases_count"
            />
          </div>
        </section>

        <section className="detail-strip">
          <div><span>Уникальные отправители</span><strong>{formatInteger(overview.gifts.unique_senders)}</strong></div>
          <div><span>Уникальные получатели</span><strong>{formatInteger(overview.gifts.unique_receivers)}</strong></div>
          <div><span>Получено после комиссий</span><strong>{overview.gifts.net_display} TDSD</strong></div>
          <div><span>Раскрытия</span><strong>{formatInteger(overview.reveals.count)}</strong></div>
          <div><span>Приглашённые</span><strong>{formatInteger(overview.referrals.invited_users)}</strong></div>
          <div><span>Реферальные выплаты</span><strong>{overview.referrals.credited_reward_display} TDSD</strong></div>
        </section>

        <section className="section-band">
          <div className="section-heading">
            <div><h2>Последние покупки</h2><span>TDSD за TON</span></div>
          </div>
          <PurchasesTable rows={activity?.recent_purchases || []} />
        </section>

        <section className="section-band">
          <div className="section-heading">
            <div><h2>Последние подарки</h2><span>Внутренние переводы TDSD</span></div>
          </div>
          <GiftsTable rows={activity?.recent_gifts || []} />
        </section>
      </main>
      ) : (
        <UsersView knownTotal={overview.users.total} />
      )}
    </div>
  );
}
