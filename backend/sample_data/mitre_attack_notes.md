# Common Attack Techniques (Reference Notes for the Assistant)

## T1110 - Brute Force
Brute force involves an attacker systematically guessing credentials to gain
unauthorized access. In logs, this typically appears as a high volume of
failed authentication events (e.g., Windows Event ID 4625, SSH "Failed
password" entries) from a single source IP or user account in a short time
window. Detection: alert when failed-login count from one source exceeds a
threshold (e.g., 10 failures in 5 minutes). Response: lock the account,
block the source IP at the firewall, and review whether MFA is enabled.

## T1078 - Valid Accounts
Attackers who have already obtained valid credentials (via phishing, brute
force, or credential dumping) can log in without triggering malware alerts.
Indicators include logins at unusual hours, logins from unfamiliar
geographic locations, or a service account authenticating interactively.
Detection relies on behavioral baselining rather than signature matching.
Response: verify with the account owner, force a password reset, and check
for lateral movement from that session.

## T1046 - Network Service Discovery
After initial access, attackers often scan the internal network to find
additional hosts and services. This shows up as a single internal host
making connection attempts to many different ports/IPs in a short period
(port scan pattern). Detection: flag hosts with connection attempts to more
than N distinct destination IPs within a short window. Response: isolate the
scanning host and check its process list for scanning tools.

## T1486 - Data Encrypted for Impact (Ransomware)
Ransomware encrypts files and typically renames them with a new extension.
Early indicators in logs include a spike in file-rename/file-write events
across many files in a short time, sudden shadow-copy deletion commands
(e.g., `vssadmin delete shadows`), and unusual process trees where an
Office document spawns a script interpreter, which spawns an encryption
binary. Response: isolate the host immediately, do not power it off,
preserve volatile memory if possible, and begin restoration from backups.

## T1071 - Application Layer Protocol (C2 over HTTP/HTTPS)
Malware often communicates with command-and-control servers over standard
web ports (80/443) to blend in with normal traffic. Indicators: periodic
"beaconing" traffic with regular intervals to a rare or newly-registered
domain, unusually small/consistent request sizes, or User-Agent strings
that don't match the installed browser. Detection: baseline outbound
traffic patterns and flag statistically regular beaconing intervals.

## T1059 - Command and Scripting Interpreter
Attackers frequently use PowerShell, cmd.exe, or bash to execute commands
post-compromise. Suspicious indicators include obfuscated/encoded
PowerShell commands (`-EncodedCommand`), scripts downloading further
payloads (`IEX (New-Object Net.WebClient).DownloadString(...)`), or a
non-administrative user account spawning a scripting interpreter at all.

## Severity Triage Guidance
When explaining an alert to an analyst, classify severity roughly as:
- **Critical**: confirmed data exfiltration, ransomware execution, or
  domain admin compromise.
- **High**: successful lateral movement, C2 beaconing confirmed, or
  privileged account misuse.
- **Medium**: suspicious but unconfirmed activity (e.g., a single failed
  brute-force attempt, one unusual login).
- **Low**: expected noise (e.g., a vulnerability scanner the org runs
  itself, a known benign service triggering a signature).
Always state your confidence level and what additional evidence would
increase or decrease it.
