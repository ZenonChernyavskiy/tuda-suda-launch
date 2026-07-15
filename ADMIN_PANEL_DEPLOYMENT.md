# Tuda Suda Admin Panel

The admin panel is a separate Vite entry served at:

```text
https://app.tudasuda.tech/admin/
```

The browser calls only the same-origin `/admin-api/` gateway. The production
`ADMIN_API_KEY` is injected by host Nginx and is never compiled into frontend
assets or stored in browser storage.

## Routes

Backend routes remain protected by `X-Admin-Token`:

- `GET /admin/dashboard/overview?period=today|7d|30d|all`
- `GET /admin/dashboard/timeseries?days=1..180`
- `GET /admin/dashboard/activity?limit=1..50`

Host Nginx protects both `/admin/` and `/admin-api/` with HTTP Basic Auth.

## First Server Setup

Run these steps only after the updated backend and frontend containers are
healthy.

Install the password-file utility and create a password interactively. Do not
put the password in shell history or project env files.

```bash
sudo apt-get update
sudo apt-get install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd-tuda-suda-admin zenon
sudo chmod 640 /etc/nginx/.htpasswd-tuda-suda-admin
sudo chown root:www-data /etc/nginx/.htpasswd-tuda-suda-admin
```

Create the root-only Nginx include from the token already loaded into the
backend container. The token is not printed by these commands.

```bash
cd /opt/tuda-suda

ADMIN_API_KEY="$(docker compose exec -T backend printenv ADMIN_API_KEY)"

case "$ADMIN_API_KEY" in
  ""|*[!A-Za-z0-9_-]*)
    echo "ADMIN_API_KEY is missing or contains unsupported characters"
    unset ADMIN_API_KEY
    return 1 2>/dev/null || exit 1
    ;;
esac

sudo install -m 600 /dev/null /etc/nginx/snippets/tuda-suda-admin-token.conf
printf 'proxy_set_header X-Admin-Token "%s";\n' "$ADMIN_API_KEY" \
  | sudo tee /etc/nginx/snippets/tuda-suda-admin-token.conf >/dev/null
unset ADMIN_API_KEY
```

Add the locations from
`ops/nginx/admin-panel.locations.conf.example` to the existing
`server_name app.tudasuda.tech` server block. Do not replace the rest of the
production Nginx configuration.

Validate and reload without printing the full configuration, because the
included admin token is secret:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Do not share output from `sudo nginx -T`; it expands the root-only include and
can print the admin API token.

## Verification

An unauthenticated request must return `401`:

```bash
curl -I https://app.tudasuda.tech/admin/
curl -I https://app.tudasuda.tech/admin-api/dashboard/overview?period=30d
```

Open `https://app.tudasuda.tech/admin/` in a browser and enter the Basic Auth
credentials. The page should load overview cards, three charts and the recent
purchase and gift tables.

The Mini App URL remains unchanged:

```text
https://app.tudasuda.tech/
```

## Token Rotation

After changing `ADMIN_API_KEY` in `.env.production` and rebuilding/restarting
the backend, recreate `/etc/nginx/snippets/tuda-suda-admin-token.conf` with the
same safe command block and reload Nginx.
