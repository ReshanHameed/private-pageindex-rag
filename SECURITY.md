# Security Policy

## Supported Versions

We actively support and accept security reports for the following versions of **Private PageIndex RAG**:

| Version | Supported |
| ------- | --------- |
| < 0.1.x | ❌ No      |
| 0.1.x   | ✅ Yes     |

## Our Security & Privacy Guarantees

**Private PageIndex RAG** is designed with a strict offline-first privacy boundary:
1. **Local Execution**: All PDF ingestion, text parsing, database operations, and user chats happen entirely on your local machine.
2. **Local Inference**: All LLM queries are sent exclusively to your local Ollama instance (defaulting to `http://localhost:11434`).
3. **No Cloud Phoning**: The application is barred from sending telemetry, documents, or logs to external hosted APIs or cloud services.

## Reporting a Vulnerability

If you discover a security vulnerability (such as an accidental network leak, unauthorized local file access, or unsafe parsing behaviour), please report it to us as follows:

1. **Do Not Open a Public Issue**: To protect users running this system, do not disclose the vulnerability in public GitHub issues, discussions, or pull requests.
2. **Email the Maintainers**: Send a detailed description of the vulnerability, a proof of concept (PoC), and potential impacts to **maintainers@example.com**.
3. **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours and work with you to verify and resolve the issue.
4. **Coordinated Disclosure**: We aim to release a patch and disclose the vulnerability within 30 days of receipt. We ask that you do not publicly disclose the vulnerability until the patch has been released.
