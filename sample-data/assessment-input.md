# Sample Assessment Input — Legacy On-Prem Web Application

Use the fields below when creating an assessment in the platform.

---

## Assessment Name
**Meridian HR Portal — Annual Threat Risk Assessment 2026**

---

## Description
Comprehensive threat risk assessment of the Meridian HR Portal, an internal-facing web application used by 1,200 employees across 3 regional offices for payroll processing, benefits enrollment, employee records management, and leave tracking. The application handles Protected Class B information including Social Insurance Numbers (SIN), banking details, salary records, and personal health information for benefits administration. This assessment covers the full technology stack from infrastructure through application layer, authentication, data handling, and network architecture. The last assessment was performed in Q1 2023; several identified risks remain unresolved.

---

## System Background
Comprehensive threat risk assessment of the Meridian HR Portal, an internal-facing web application used by 1,200 employees across 3 regional offices for payroll processing, benefits enrollment, employee records management, and leave tracking. The application handles Protected Class B information including Social Insurance Numbers (SIN), banking details, salary records, and personal health information for benefits administration. This assessment covers the full technology stack from infrastructure through application layer, authentication, data handling, and network architecture. The last assessment was performed in Q1 2023; several identified risks remain unresolved.

---

## Technology Stack

| Layer | Technology | Version | End-of-Life Status |
|---|---|---|---|
| **Operating System** | Microsoft Windows Server 2008 R2 SP1 | 6.1.7601 | EOL: January 14, 2020 |
| **Web Server** | Apache HTTP Server | 2.2.34 | EOL: December 2017 |
| **Runtime** | PHP | 5.6.40 | EOL: December 31, 2018 |
| **Database** | MySQL Community Server | 5.5.62 | EOL: December 2018 |
| **Application Framework** | Custom PHP (no framework) | N/A | Bespoke / unmaintained |
| **Authentication** | Application-specific (PHP sessions + MD5 password hashes) | N/A | No MFA, no lockout |
| **TLS** | OpenSSL 1.0.2u | 1.0.2u | EOL: December 2019 |
| **File Transfer** | FTP (vsftpd on a Linux relay) | 3.0.2 | Unencrypted |
| **Backup** | Windows Server Backup to Synology NAS (SMBv1) | N/A | SMBv1 deprecated |
| **Network** | Flat VLAN — no segmentation between servers and user workstations | N/A | No firewall between zones |
| **Antivirus** | Symantec Endpoint Protection | 14.0 (definitions 6+ months stale) | Agent not centrally managed |
| **Monitoring** | None (manual Windows Event Viewer checks) | N/A | No SIEM / no alerting |
| **Load Balancer / WAF** | None | N/A | Direct exposure to internal LAN |

### Additional Design Risks Noted
- **Hardcoded database credentials** in `config.php` (plaintext, world-readable)
- **No input validation** — raw SQL string concatenation throughout codebase (SQL injection likely)
- **Session tokens** stored in URL query strings (session hijacking risk)
- **Admin console** accessible at `/admin` with default credentials (`admin / admin123`)
- **No HTTPS enforcement** — application responds on both HTTP (80) and HTTPS (443); no redirect
- **Self-signed TLS certificate** expired in November 2024
- **Shared service account** "svc_meridian" used for database, file shares, and scheduled tasks with domain admin privileges
- **Direct database port exposure** — MySQL 3306 open to all internal IPs
- **No centralized logging** — application logs written to local `C:\logs\` folder, no rotation, no forwarding
- **USB autorun enabled** on the server
- **Remote Desktop (RDP)** enabled with NLA disabled, exposed to internal network
- **No change management** — patches applied ad-hoc during business hours

---

## Threats to Enter in Assessment

Use these when adding threats manually:

| # | Title | Catalogue Key | Description |
|---|---|---|---|
| 1 | SQL Injection via HR Search Module | `web_app_attacks` | The employee search and reporting modules use unsanitized string concatenation to build SQL queries. An authenticated user can inject arbitrary SQL to extract or modify any database record including payroll and SIN data. |
| 2 | Credential Theft via MD5 Hash Cracking | `password_cracking` | User passwords are stored as unsalted MD5 hashes. The full user table (1,200 records) can be extracted and cracked in under 2 minutes with commodity hardware using rainbow tables. |
| 3 | Ransomware on End-of-Life Windows 2008 | `ransomware` | Windows Server 2008 R2 receives no security patches. Publicly available exploits (EternalBlue/MS17-010 and BlueKeep/CVE-2019-0708) allow unauthenticated remote code execution. Ransomware operators routinely target unpatched SMB and RDP services. |
| 4 | Data Exfiltration via Unencrypted FTP | `data_loss_leakage` | Nightly payroll extracts containing SIN and banking data are transferred via unencrypted FTP. Any user on the network can capture full file contents with a packet sniffer. |
| 5 | Privilege Escalation via Shared Service Account | `unauthorized_access` | The svc_meridian account has domain admin privileges and its credentials are stored in plaintext in config.php. Compromise of the web application grants full domain access. |
| 6 | Persistent Backdoor via Unpatched Apache | `apt` | Apache 2.2.34 has 47 known CVEs including remote code execution (CVE-2017-9798, CVE-2017-7679). An attacker exploiting these can plant a web shell for persistent access to the internal network. |
| 7 | Session Hijacking via URL Token Leakage | `mitm_eavesdropping` | Session IDs are passed as URL query parameters. They appear in browser history, proxy logs, and Referer headers when users click external links, enabling account takeover. |
| 8 | Malware Infection via Stale Antivirus | `malicious_code` | Symantec EP definitions are 6+ months out of date and the agent is not centrally managed. The server has no application whitelisting. Malware delivered via RDP or web shell would not be detected. |
| 9 | Admin Console Takeover via Default Credentials | `misconfiguration` | The /admin panel ships with default credentials (admin/admin123) which were never changed. It provides full database query access, user management, and file upload capability. |
| 10 | Insider Data Theft via Direct DB Access | `insider_threats` | MySQL port 3306 is open to all internal IPs. Any employee with basic SQL knowledge and a MySQL client can connect directly using the shared credentials from config.php and export the entire HR database. |
