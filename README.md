# HopShot

HopShot is a Python UDP tunneling prototype with adaptive port hopping, FEC, packet jitter, optional HTTP/3 masquerading, Brutal CC pacing, and a release-style client/server CLI.

Version: `1.0.0`

## English

### What it does

HopShot runs a client and a server that exchange UDP traffic through a configurable port range. The client can probe loss, choose a profile, hop ports deterministically, and optionally use QUIC/TLS or HTTP/3 masquerading. The server receives traffic, reconstructs FEC shards, and returns feedback.

### Main features

- Adaptive port hopping
- FEC recovery for burst loss
- Packet jitter to vary packet sizes
- Optional HTTP/3 masquerading
- Optional random source ports
- Brutal CC pacing with declared bandwidth hints
- Diagnostic CLI output
- JSON log file support
- Release version flag on both client and server

### Requirements

- Python 3.14 or newer
- Windows, Linux, or macOS
- A local or remote UDP-capable server
- Optional admin/root privileges for firewall or port redirection setup

### Quick start

#### 1. Server

Run the server first:

```bash
python server.py --port 10000 --seed "my-secret"
```

For a more complete deployment:

```bash
python server.py --port 10000 --quic-port 10001 --seed "my-secret" \
  --port-min 10000 --port-max 65000 --json-logs --log-file server.log
```

#### 2. Client

Run the client against the server:

```bash
python client.py --server 1.2.3.4 --port 10000 --seed "my-secret"
```

For an operator-style setup:

```bash
python client.py --server 1.2.3.4 --port 10000 --seed "my-secret" \
  --profile balanced --json-logs --log-file client.log
```

### Client profiles

- `balanced`: general-purpose default
- `reliable`: disables hopping for simpler connectivity
- `stealth`: enables stronger camouflage options
- `throughput`: keeps the path simpler for maximum delivery

### Release CLI

Use these commands to inspect the release build:

```bash
python client.py --version
python server.py --version
python client.py --diagnose --server 127.0.0.1 --dest 127.0.0.1
python server.py --diagnose
```

### Deployment on server

1. Copy the repository to the server host.
2. Create and activate a Python virtual environment.
3. Install any dependencies if your environment requires them.
4. Open the UDP ports you plan to use, including the QUIC/TLS port if enabled.
5. Start the server with the same shared seed the client will use.

Example:

```bash
python server.py --port 10000 --quic-port 10001 --seed "my-secret" \
  --port-min 10000 --port-max 65000 --iptables --masquerade
```

If you are running behind a firewall or NAT, make sure the listener ports are forwarded to the machine running `server.py`.

### Deployment on client

1. Copy the repository to the client machine.
2. Create and activate a Python virtual environment.
3. Configure the server IP or hostname.
4. Match the shared seed and port range.
5. Start with `--diagnose` first if you want to verify the resolved configuration.

Example:

```bash
python client.py --server 1.2.3.4 --port 10000 --seed "my-secret" \
  --port-min 10000 --port-max 65000 --profile balanced
```

### Logging and diagnostics

- `--log-file` writes logs to a file.
- `--json-logs` writes file logs as JSON lines.
- `--diagnose` prints the resolved configuration and exits.
- `--msg` sends one message and exits.

### Project layout

- `client.py` - client CLI and transport pipeline
- `server.py` - server CLI and receive pipeline
- `common.py` - packet headers, hopping, and shared helpers
- `fec.py` - FEC and recovery logic
- `brutal.py` - Brutal CC pacing and feedback
- `http3_masq.py` - HTTP/3 camouflage helpers
- `mtu_probe.py` - MTU discovery
- `resolver.py` - DNS and destination probing
- `session_resume.py` - probe token cache
- `terminal_ui.py` - colored logging and terminal formatting
- `test_hopshot.py` - integration test suite

### Notes

- The transport is designed for experimentation and controlled deployments.
- The client and server should use the same shared seed.
- If you enable masquerading or iptables redirect, make sure the server side is configured for it.

## فارسی

### این پروژه چه کاری انجام می‌دهد

HopShot یک نمونهٔ پایتونی برای تونل UDP با پرش تطبیقی پورت، FEC، نویز دادن به اندازهٔ بسته‌ها، ماسک‌کردن اختیاری HTTP/3، و CLI آمادهٔ استفاده برای کلاینت و سرور است.

### ویژگی‌ها

- پرش تطبیقی پورت
- بازیابی خطا با FEC
- تغییر اندازهٔ بسته‌ها برای سخت‌تر شدن fingerprint
- ماسک‌کردن اختیاری HTTP/3
- تصادفی‌سازی اختیاری پورت مبدأ
- کنترل نرخ با Brutal CC
- خروجی تشخیصی برای CLI
- پشتیبانی از لاگ JSON
- نمایش نسخه در کلاینت و سرور

### پیش‌نیازها

- Python 3.14 یا جدیدتر
- ویندوز، لینوکس یا macOS
- یک سرور UDP در دسترس
- در صورت نیاز، دسترسی admin/root برای باز کردن یا redirect کردن پورت‌ها

### راه‌اندازی سریع

#### 1) سرور

اول سرور را اجرا کنید:

```bash
python server.py --port 10000 --seed "my-secret"
```

برای حالت کامل‌تر:

```bash
python server.py --port 10000 --quic-port 10001 --seed "my-secret" \
  --port-min 10000 --port-max 65000 --json-logs --log-file server.log
```

#### 2) کلاینت

سپس کلاینت را اجرا کنید:

```bash
python client.py --server 1.2.3.4 --port 10000 --seed "my-secret"
```

برای استفادهٔ عملیاتی‌تر:

```bash
python client.py --server 1.2.3.4 --port 10000 --seed "my-secret" \
  --profile balanced --json-logs --log-file client.log
```

### پروفایل‌های کلاینت

- `balanced`: حالت پیش‌فرض عمومی
- `reliable`: ساده‌تر و پایدارتر، بدون hopping
- `stealth`: با تنظیمات مخفی‌سازی قوی‌تر
- `throughput`: مسیر ساده‌تر برای تحویل بهتر

### دستورهای نسخه و تشخیص

```bash
python client.py --version
python server.py --version
python client.py --diagnose --server 127.0.0.1 --dest 127.0.0.1
python server.py --diagnose
```

### استقرار روی سرور

1. مخزن را روی ماشین سرور کپی کنید.
2. یک virtual environment بسازید و فعال کنید.
3. اگر لازم است dependencyها را نصب کنید.
4. پورت‌های UDP و در صورت نیاز QUIC/TLS را باز کنید.
5. سرور را با همان seed کلاینت اجرا کنید.

نمونه:

```bash
python server.py --port 10000 --quic-port 10001 --seed "my-secret" \
  --port-min 10000 --port-max 65000 --iptables --masquerade
```

اگر سرور پشت firewall یا NAT است، باید پورت‌ها به همان ماشین forward شوند.

### استقرار روی کلاینت

1. مخزن را روی ماشین کلاینت کپی کنید.
2. virtual environment بسازید و فعال کنید.
3. IP یا hostname سرور را مشخص کنید.
4. seed و بازهٔ پورت را با سرور هماهنگ کنید.
5. اگر خواستید اول `--diagnose` بگیرید تا config نهایی را ببینید.

نمونه:

```bash
python client.py --server 1.2.3.4 --port 10000 --seed "my-secret" \
  --port-min 10000 --port-max 65000 --profile balanced
```

### لاگ و عیب‌یابی

- `--log-file` لاگ را در فایل ذخیره می‌کند.
- `--json-logs` لاگ فایل را به صورت JSON line می‌نویسد.
- `--diagnose` تنظیمات نهایی را چاپ می‌کند و خارج می‌شود.
- `--msg` یک پیام می‌فرستد و تمام می‌شود.

### ساختار پروژه

- `client.py` - CLI و مسیر ارسال کلاینت
- `server.py` - CLI و مسیر دریافت سرور
- `common.py` - هدر بسته‌ها و helperهای مشترک
- `fec.py` - منطق FEC و بازیابی
- `brutal.py` - pacing و feedback
- `http3_masq.py` - ماسک‌کردن HTTP/3
- `mtu_probe.py` - تشخیص MTU
- `resolver.py` - DNS و probing مقصد
- `session_resume.py` - کش tokenهای probe
- `terminal_ui.py` - لاگ رنگی و formatting ترمینال
- `test_hopshot.py` - تست‌های یکپارچه

### نکته

- این پروژه برای آزمایش و استقرار کنترل‌شده طراحی شده است.
- کلاینت و سرور باید یک seed مشترک داشته باشند.
- اگر masquerade یا iptables redirect را فعال می‌کنید، تنظیمات سمت سرور را هم انجام دهید.
