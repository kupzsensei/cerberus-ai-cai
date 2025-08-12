# Report: Gemini API Security & Usage in Cerberus AI

**Date:** August 6, 2025
**Status:** For Internal Review

---

## 1. Executive Summary

This report details the security implications, usage limitations, and data exposure risks associated with the integration of the Google Gemini API within the Cerberus AI application.

The primary security risk identified is the **storage of the Gemini API key in plaintext** within the local database, which is not a secure practice for production environments. The most significant data privacy concern is that **all data sent to the Gemini API is processed on Google's servers**, and per their standard terms of service, may be used to improve their services. This means the data is not private in the same way data processed locally by the Ollama server is.

The chance of a direct, public data leak from Google's infrastructure is **very low**. However, the chance that your data will be seen and used by Google is **high**, as this is part of their standard operating procedure for public APIs.

Key limitations include API rate limits, potential for significant financial cost, and the inherent reliability risks of relying on a third-party service.

This report strongly recommends using the integrated Ollama server for any sensitive or confidential tasks and reserving the Gemini integration for research on public data.

---

## 2. Security Implications

### 2.1. API Key Security (High Risk)

*   **Vulnerability:** The Gemini API key is currently stored in plaintext in the `external_ai_servers` table of the `tasks.db` SQLite database file.
*   **Impact:** If this database file is ever exposed, an attacker will gain full access to your API key. This would allow them to make API calls at your expense, potentially leading to significant and unexpected charges on your Google Cloud billing account.
*   **Recommendation:** API keys and other secrets should **never** be stored in application code or a database. They should be managed through a secure secrets management tool (like HashiCorp Vault or AWS/Google Secret Manager) or, at a minimum, be loaded from secure environment variables on the backend server.

### 2.2. Data Privacy and Confidentiality (High Risk)

*   **Vulnerability:** Any query or data sent via the "Investigate" or "Chatbot" features when a Gemini model is selected is transmitted to and processed by Google's servers.
*   **Impact:** This data is subject to Google's data usage and privacy policies. For standard APIs, Google may use this data to train and improve their models. This means your data—including prompts and the content of any web pages analyzed—is not private.
*   **Recommendation:** **Do not send any sensitive, confidential, or proprietary information to the Gemini API.** This includes, but is not limited to:
    *   Personally Identifiable Information (PII)
    *   Financial or health records
    *   Proprietary source code or business plans
    *   Any information you are not comfortable sharing with Google.

---

## 3. Risk of Public Data Exposure

This section directly addresses the probability of your data being exposed to the general public.

*   **Risk of a Direct Public Leak (Very Low):** The probability of a malicious actor breaching Google's infrastructure and causing a direct, public leak of user API logs is extremely low. Google invests heavily in security, and such an event would be catastrophic for their business. While no system is infallible, this is not the primary concern for a typical user.

*   **Risk of Internal Exposure to Google (High / Certainty):** This is the most important risk to understand. When you use the service, you are intentionally sending your data to Google for processing. Their standard terms of service allow them to use this data for service improvement. Therefore, the "exposure" of your data to Google is not a risk; it is a **certainty** of how the service operates.

*   **Risk of Exposure via Legal Compliance (Low but Possible):** As a U.S. company, Google is subject to legal requests from government and law enforcement agencies. If presented with a valid warrant or subpoena, Google may be legally required to provide your data.

---

## 4. Usage Limitations

### 4.1. Cost Management

*   **Limitation:** The Gemini API is a metered, pay-as-you-go service. While a free tier exists, it is limited. Heavy or inefficient use can lead to high costs.
*   **Recommendation:** Set up **billing alerts** in your Google Cloud Console to be notified when your spending exceeds a certain threshold. Monitor your usage regularly.

### 4.2. API Rate Limits and Service Reliability

*   **Limitation:** The API enforces rate limits (e.g., a maximum number of requests per minute). Exceeding these limits will cause API calls to fail, temporarily disabling the feature. The application's functionality is also dependent on the uptime and availability of Google's public API.
*   **Recommendation:** For critical tasks, consider the reliability of a public API versus the self-hosted Ollama server, which is not subject to the same external dependencies.

### 4.3. Model Capabilities

*   **Knowledge Cutoff:** The model's knowledge is not real-time and is limited to the date of its last training run. It may not be aware of very recent events.
*   **Accuracy (Hallucinations):** The AI can generate plausible but incorrect or fabricated information. All outputs, especially from the "Investigate" feature, should be critically reviewed and fact-checked against the provided sources.

---

## 5. Conclusion & Final Recommendation

The Gemini integration in Cerberus AI is a powerful tool for public-facing research and general chatbot interaction. However, due to the inherent data privacy model of public APIs and the current insecure storage of the API key, it is **not suitable for any tasks involving sensitive or confidential information.**

**Primary Recommendation:** Use the self-hosted **Ollama server** for all private or sensitive analysis. Use the **Gemini server** only for research on public data where you are comfortable with the data being processed by Google.
