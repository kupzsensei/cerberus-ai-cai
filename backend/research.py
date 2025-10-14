import os
import logging
import httpx
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
import json
import re
import time
from datetime import datetime
import database
import utils


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Validate environment variables
tavily_api_key = os.environ.get("TAVILY_API_KEY")
openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY is not set in the .env file")
if not openrouter_api_key:
    raise ValueError("OPENROUTER_API_KEY is not set in the .env file")

# Corrected domain list
include_domains = [
    "cyberdaily.au",
    "sbs.com.au",
    "infosecurity-magazine.com",
    "crowdstrike.com",
    "blackpointcyber.com",
    "thehackernews.com",
    "darkreading.com"
]

# Create search tool
tavily_tool = TavilySearch(
    max_results=15,
    topic="general",
    search_depth="advanced",
    include_domains=include_domains
)

# Function to perform a search
async def perform_search(query, server_name: str = None, model_name: str = "granite3.3", server_type: str = "ollama"):
    """
    Performs a research search using the specified AI server and model.
    
    Args:
        query: The search query
        server_name: Name of the AI server to use
        model_name: Name of the model to use
        server_type: Type of server (ollama or gemini)
        
    Returns:
        tuple: (result, generation_time) or (error_message, None)
    """
    try:
        # Start timer for the entire research process
        overall_start_time = time.time()

        # Determine which AI server to use
        selected_server = None
        server_url_or_key = None

        if server_type == "ollama":
            if server_name:
                selected_server = await database.get_ollama_server_by_name(server_name)
            if not selected_server:
                all_servers = await database.get_ollama_servers()
                if all_servers:
                    selected_server = all_servers[0]
                else:
                    raise ValueError("No Ollama servers configured.")
            server_url_or_key = selected_server['url']
            llm = ChatOllama(
                model=model_name,
                temperature=0,
                api_key=os.environ.get("OPENROUTER_API_KEY"),
                base_url=server_url_or_key.replace("/api/generate", "/")
            )
            # Test connection to the selected Ollama server using async HTTP client
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{server_url_or_key.replace('/api/generate', '')}/api/tags")
                if response.status_code != 200:
                    raise ConnectionError(f"Failed to connect to Ollama server at {server_url_or_key}")
        elif server_type == "gemini":
            if server_name:
                selected_server = await database.get_external_ai_server_by_name(server_name)
            if not selected_server:
                all_servers = await database.get_external_ai_servers()
                if all_servers:
                    selected_server = all_servers[0]
                else:
                    raise ValueError("No Gemini servers configured.")
            server_url_or_key = selected_server['api_key']
            llm = ChatGoogleGenerativeAI(
                model=f"models/gemini-2.5-flash",
                temperature=0,
                google_api_key=server_url_or_key
            )
        else:
            raise ValueError(f"Unsupported server type: {server_type}")

        # Preprocess query with unique timestamp to avoid caching
        if "Australia" not in query:
            query = f"{query} Australia cybersecurity incidents timestamp:{int(time.time())}"
        query = query.replace(" to ", ", 2025 to ")  # Ensure year is explicit
        logger.info(f"Processing query: {query}")
        
        # Get raw Tavily results
        # Since TavilySearch doesn't have an async version, we'll run it in a thread pool
        import asyncio
        raw_results = await asyncio.get_event_loop().run_in_executor(None, tavily_tool.invoke, query)
        logger.info(f"Raw Tavily results retrieved")
        
        # Filter results to ensure domain compliance and relevance
        filtered_results = [
            r for r in raw_results.get("results", [])
            if any(domain in r["url"] for domain in include_domains)
            and any(term in r["content"].lower() for term in [
                "australia", "australian", "qantas", "government", "superannuation",
                "business", "sector", "ransomware", "phishing", "ddos", "keylogger",
                "exploit", "vulnerability", "data breach", "cyberattack"
            ])
        ]
        for r in raw_results.get("results", []):
            if any(domain in r["url"] for domain in include_domains) and not any(term in r["content"].lower() for term in [
                "australia", "australian", "qantas", "government", "superannuation",
                "business", "sector", "ransomware", "phishing", "ddos", "keylogger",
                "exploit", "vulnerability", "data breach", "cyberattack"
            ]):
                logger.info(f"Excluded result: {r['url']} - No relevant keywords found")
        logger.info(f"Filtered results count: {len(filtered_results)}")
        
        # Generate output from raw results
        # Run the formatting in a thread pool to avoid blocking
        output = await asyncio.get_event_loop().run_in_executor(None, format_raw_results, filtered_results, 0, llm)
        
        if not output.strip():
            logger.warning("No relevant results found")
            return "No cybersecurity incidents relevant to Australian businesses found for the requested timeframe.", None
        
        overall_end_time = time.time()
        generation_time = overall_end_time - overall_start_time

        await database.add_research(query, output, generation_time, selected_server['name'], model_name)
        return output, generation_time
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        # Check for model-specific errors
        if "is not supported" in str(e) or "Invalid model" in str(e):
            error_message = f"The selected model '{model_name}' is not suitable for this research task. Please try a different model, such as 'granite3.3'."
            return error_message, None
        return f"Error processing query: {str(e)}", None

# Function to format raw results
def format_raw_results(results, start_count, llm):
    output = ""
    for i, result in enumerate(results[:15], start_count + 1):
        title = result.get("title", "Untitled Incident")
        content = result.get("content", "No description available")
        url = result.get("url", "Not specified")
        
        # Use LLM to extract structured data and summarize the article
        extraction_prompt = f'''Please provide a summary of the following article, ignoring any boilerplate text like navigation menus, headers, or footers. The summary should be on a single line, prefixed with "Summary: ". Then, extract the following information, each on a new line:
        - Date of Incident (if not present, say "Not specified")
        - Targets of the incident (e.g., Qantas customers, Australian government agencies, etc. If not present, say "Not specified")
        - Method of the attack (e.g., Ransomware, Phishing, Data breach, etc. If not present, say "Not specified")

        Article: {content}
        '''
        try:
            extracted_data = llm.invoke(extraction_prompt).content
            
            summary_match = re.search(r"Summary: (.*)", extracted_data, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else content[:600] + "..."

            date_match = re.search(r"Date of Incident: (.*)", extracted_data)
            date = date_match.group(1) if date_match else "Not specified"
            
            targets_match = re.search(r"Targets: (.*)", extracted_data)
            targets = targets_match.group(1) if targets_match else "Not specified"
            
            method_match = re.search(r"Method: (.*)", extracted_data)
            method = method_match.group(1) if method_match else "Not specified"
        except Exception as e:
            logger.error(f"Error extracting data from LLM: {e}")
            summary = content[:600] + "..."
            date = "Not specified"
            targets = "Not specified"
            method = "Not specified"

        # Improved relevance
        relevance = "Relevant to Australian businesses due to potential impact on similar industries or supply chains"
        if "Qantas" in content:
            relevance = "Directly impacts Qantas, a major Australian airline, affecting customer trust and compliance."
        elif "government" in content.lower():
            relevance = "Affects Australian government operations and public sector data security."
        elif "superannuation" in content.lower():
            relevance = "Impacts Australia’s superannuation industry, critical for financial security."
        elif "university" in content.lower():
            relevance = "Impacts Australian educational institutions, affecting data security and operations."
        elif "Australian sectors" in content or "Australia" in content:
            relevance = "Impacts Australian businesses across multiple sectors, increasing cybersecurity risks."
        
        # Note speculative data for 2025
        if "2025" in date:
            relevance += " Speculative based on current trends."
        
        output += f'''
# [{i}]. {title}

{summary}

- **Date of Incident**: {date}
- **Targets**: {targets}
- **Method**: {method}
- **Relevance to Australian Business**: {relevance}
- **Source**: {url}



---


'''
    if len(results) < 10:
        output += f"\nOnly [{len(results)}] relevant cybersecurity incidents found for the requested timeframe."
    return output

# Main function for testing
if __name__ == "__main__":
    import asyncio
    async def main():
        # Example query
        query = "Cybersecurity incidents in Australia from January 2025 to March 2025"
        output, generation_time = await perform_search(query)
        print(output)
        print(f"Generation time: {generation_time:.2f} seconds")
    asyncio.run(main())

def format_investigation_results(query, results, llm):
    # Extract content and URLs from results
    formatted_results = ""
    for result in results:
        formatted_results += f"URL: {result.get('url', 'N/A')}\nContent: {result.get('content', 'N/A')}\n\n"

    prompt = f"""
    As a senior cybersecurity analyst, your task is to produce a detailed and well-structured threat intelligence report based on the provided web search results. The report should be written in Markdown format and follow the structure below.

    **Objective:** Synthesize the provided data into a comprehensive report on the cybersecurity incident: "{query}".

    **Report Structure:**

    1.  **Heading:**
        - Create a clear, concise heading for the report (e.g., `# {query} Research`).

    2.  **Incident Overview:**
        - **Who & When:**
            - **Date of breach:** Specify the date the breach occurred.
            - **Discovery:** State when the breach was discovered.
            - **Notification:** Detail when the public or relevant authorities were notified.
            - **Customer notifications planned:** Mention any planned dates for notifying customers.
        - **Exposed Data & Scope:**
            - Describe the platform or system that was breached (e.g., third-party CRM, internal network).
            - Explain the method used by the threat actor (e.g., social engineering, malware).
            - List the types of data compromised (e.g., PII, financial credentials).
        - **Organisation Context:**
            - Provide background on the affected organization, including its size and industry.
            - Clarify the scope of the breach (e.g., U.S. operations only).
        - **Response & Remediation:**
            - Detail the immediate actions taken by the organization.
            - Describe the customer protection measures being offered.
            - Mention the ongoing status of the investigation and any attribution to threat groups.

    3.  **Timeline Summary:**
        - Create a Markdown table with two columns: "Date" and "Event".
        - Populate the table with key dates and corresponding events from the incident.

    4.  **MITRE ATT&CK Mapping:**
        - Identify relevant MITRE ATT&CK techniques based on the incident details.
        - **Attack Flow Summary:** Describe the likely attack sequence in a few steps.
        - **Detailed Table:** Create a Markdown table with columns: "MITRE Phase", "Technique/Sub-technique", and "Description & Relevance".
        - **Security Implications:** Analyze the security implications of the attack.
        - **Recommendations:** Provide a table with columns: "Control Area" and "Actions", suggesting measures to prevent similar incidents.

    5.  **References:**
        - List all the source URLs provided in the search results.

    **Input Data:**

    {formatted_results}

    ---
    **Instructions:**
    - Ensure all sections are completed thoroughly and accurately based on the provided data.
    - If specific information is not available in the results, state "Not specified" or "N/A".
    - Maintain a professional and analytical tone throughout the report.
    - The final output must be a single, well-formatted Markdown document.
    """

    # Invoke the LLM with the detailed prompt
    response = llm.invoke(prompt)
    return response.content

async def investigate(query: str, server_name: str = None, model_name: str = "granite3.3", server_type: str = "ollama"):
    try:
        # Start timer for the entire research process
        overall_start_time = time.time()

        selected_server = None
        server_url_or_key = None

        if server_type == "ollama":
            if server_name:
                selected_server = await database.get_ollama_server_by_name(server_name)
            if not selected_server:
                all_servers = await database.get_ollama_servers()
                if all_servers:
                    selected_server = all_servers[0]
                else:
                    raise ValueError("No Ollama servers configured.")
            server_url_or_key = selected_server['url']
            llm = ChatOllama(
                model=model_name,
                temperature=0,
                api_key=os.environ.get("OPENROUTER_API_KEY"),
                base_url=server_url_or_key.replace("/api/generate", "/")
            )
            # Test connection to the selected Ollama server using async HTTP client
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{server_url_or_key.replace('/api/generate', '')}/api/tags")
                if response.status_code != 200:
                    raise ConnectionError(f"Failed to connect to Ollama server at {server_url_or_key}")
        elif server_type == "gemini":
            if server_name:
                selected_server = await database.get_external_ai_server_by_name(server_name)
            if not selected_server:
                all_servers = await database.get_external_ai_servers()
                if all_servers:
                    selected_server = all_servers[0]
                else:
                    raise ValueError("No Gemini servers configured.")
            server_url_or_key = selected_server['api_key']
            llm = ChatGoogleGenerativeAI(
                model=f"models/gemini-2.5-flash",
                temperature=0,
                google_api_key=server_url_or_key
            )
        else:
            raise ValueError(f"Unsupported server type: {server_type}")

        # Get raw Tavily results
        # Since TavilySearch doesn't have an async version, we'll run it in a thread pool
        import asyncio
        tavily_tool_unrestricted = TavilySearch(
            max_results=15,
            topic="general",
            search_depth="advanced",
        )
        raw_results = await asyncio.get_event_loop().run_in_executor(None, tavily_tool_unrestricted.invoke, query)
        logger.info(f"Raw Tavily results retrieved")

        # Generate the detailed investigation report
        # Run the formatting in a thread pool to avoid blocking
        output = await asyncio.get_event_loop().run_in_executor(None, format_investigation_results, query, raw_results.get("results", []), llm)

        if not output.strip():
            logger.warning("No relevant results found")
            return "No information found for the requested query.", None

        overall_end_time = time.time()
        generation_time = overall_end_time - overall_start_time

        await database.add_research(query, output, generation_time, selected_server['name'], model_name)
        return output, generation_time
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        # Check for model-specific errors
        if "is not supported" in str(e) or "Invalid model" in str(e):
            error_message = f"The selected model '{model_name}' is not suitable for this research task. Please try a different model, such as 'granite3.3'."
            return error_message, None
        return f"Error processing query: {str(e)}", None
