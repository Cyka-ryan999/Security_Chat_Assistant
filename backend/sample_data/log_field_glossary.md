# Log Field & Terminology Glossary

**Event ID 4625** (Windows Security log): An account failed to log on.
Key fields: `TargetUserName` (account attempted), `IpAddress` (source of
attempt), `LogonType` (3 = network, 10 = RDP), `FailureReason`.

**Event ID 4624**: An account successfully logged on. Compare `LogonType`
and `IpAddress` against the account's normal baseline to spot anomalies.

**Event ID 4688**: A new process has been created. Useful for tracing
process lineage (parent-child relationships) during an incident.

**Sysmon Event ID 1**: Process creation, includes command line, hashes,
and parent process — richer than native Event ID 4688.

**Sysmon Event ID 3**: Network connection initiated by a monitored
process — useful for spotting C2 beaconing or unexpected outbound
connections.

**Sysmon Event ID 11**: File created — useful for spotting ransomware
(mass file writes) or dropped payloads.

**Firewall "DENY" log entries**: A connection attempt was blocked by
policy. A high rate of DENY entries from one source is often a scan;
a single DENY on a sensitive port from an external IP may indicate
reconnaissance.

**Severity vs. Confidence**: Severity describes how bad it would be if the
activity is malicious. Confidence describes how sure we are that it is
malicious. An alert can be high severity but low confidence (e.g., a
single unconfirmed sign of ransomware) — both should be communicated
together, not collapsed into one number.

**IOC (Indicator of Compromise)**: A forensic artifact (IP, domain,
file hash, registry key) associated with malicious activity.

**False positive**: An alert that fired on benign activity. Analysts
should always consider whether context (e.g., a scheduled vulnerability
scan, an admin's known remote-access habits) explains the alert before
escalating.
