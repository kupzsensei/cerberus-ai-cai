import os
import logging
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_tavily import TavilySearch
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import requests
import json
import re
import time
from datetime import datetime
from langgraph.prebuilt import create_react_agent
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

# Initialize the LLM (optional, for fallback)
# Initialize the LLM (optional, for fallback)
# This is now initialized within perform_search based on selected server
# try:
#     ollama_api_url = utils.config.get("ollama_api_url").replace("localhost", "host.docker.internal")
#     ollama_model = utils.config.get("ollama_model")

#     llm = ChatOllama(
#         model=ollama_model,
#         temperature=0,
#         api_key=openrouter_api_key,
#         base_url=ollama_api_url.replace("/api/generate", "/") # Adjust base_url for ChatOllama
#     )
#     response = requests.get(f"{ollama_api_url.replace('/api/generate', '')}/api/tags")
#     if response.status_code != 200:
#         raise ConnectionError("Failed to connect to Ollama server")
# except Exception as e:
#     raise ConnectionError(f"Ollama server error: {str(e)}")

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

# Define the custom prompt template (optional, for fallback)
prompt = ChatPromptTemplate.from_messages([
    ("system", '''You are a research assistant tasked with generating a cybersecurity threat and risk report for incidents relevant to Australian businesses, based solely on Tavily search results from the following domains: {domains}. Include incidents such as exploits, data breaches, cyberattacks, and vulnerabilities, whether they occurred in Australia or globally, as long as they have clear relevance to Australian businesses (e.g., impacting Australian companies, supply chains, or industries). Do not invent, modify, or assume information not explicitly present in the search results. Provide 10–15 results if available, using all relevant raw results from Tavily. If fewer, state: "Only [X] relevant cybersecurity incidents found for the requested timeframe." Each item MUST follow this format:

## [Number]. [Headline]

[Description]

- **Date of Incident**: [Date or "Not specified" if unavailable]
- **Targets**: [Targets or "Not specified" if unavailable]
- **Method**: [Method, e.g., exploit, phishing, ransomware, etc.]
- **Relevance to Australian Business**: [Explain relevance, e.g., impact on Australian companies, customers, or industries]
- **Source**: [Exact URL from Tavily results, matching one of the specified domains]

Follow these steps:
1. Use the Tavily Search tool to retrieve results for cybersecurity incidents (exploits, data breaches, cyberattacks, vulnerabilities) relevant to Australian businesses, strictly within the requested timeframe (e.g., June 1, 2025 to July 1, 2025).
2. Only include results from the specified domains: {domains}. Discard any results from other domains.
3. Use the exact URLs and content from the raw Tavily results; do not modify or fabricate data.
4. Summarize all relevant results concisely and accurately in the specified format, prioritizing incidents within the query's timeframe.
5. If no relevant data is found, state: "No cybersecurity incidents relevant to Australian businesses found for the requested timeframe."
6. For future timeframes (e.g., 2025), include predictive trends or vulnerabilities from the raw results and note if data is speculative with: "Speculative based on current trends."
7. Ensure all relevant raw results (up to 15) are included unless they fail relevance or domain criteria.

Available tools:
- tavily_search_results_json: Returns up to 15 web search results as JSON from the specified domains.

User query is provided in the messages.'''.format(domains=", ".join(include_domains))),
    MessagesPlaceholder(variable_name="messages")
])

# Create the agent (optional, for fallback)
# Create the agent (optional, for fallback)
# agent = create_react_agent(llm, [tavily_tool])

# Function to perform a search
async def perform_search(query, ollama_server_name: str = None, ollama_model: str = None):
    try:
        # Start timer for the entire research process
        overall_start_time = time.time()

        # Determine which Ollama server to use
        selected_server = None
        if ollama_server_name:
            selected_server = await database.get_ollama_server_by_name(ollama_server_name)
        
        if not selected_server:
            # Fallback to default if not found or not provided
            # For now, we'll just use the first one in the config if none is selected or found
            # In a real app, you'd want a more robust default selection or error handling
            all_servers = await database.get_ollama_servers()
            if all_servers:
                selected_server = all_servers[0]
            else:
                raise ValueError("No Ollama servers configured.")
        
        ollama_api_url = selected_server['url']

        # Initialize the LLM with the selected server details
        llm = ChatOllama(
            model=ollama_model,
            temperature=0,
            api_key=openrouter_api_key,
            base_url=ollama_api_url.replace("/api/generate", "/")
        )
        # Create the agent
        agent = create_react_agent(llm, [tavily_tool])
        # Test connection to the selected Ollama server
        response = requests.get(f"{ollama_api_url.replace('/api/generate', '')}/api/tags")
        if response.status_code != 200:
            raise ConnectionError(f"Failed to connect to Ollama server at {ollama_api_url}")

        # Preprocess query with unique timestamp to avoid caching
        if "Australia" not in query:
            query = f"{query} Australia cybersecurity incidents timestamp:{int(time.time())}"
        query = query.replace(" to ", ", 2025 to ")  # Ensure year is explicit
        logger.info(f"Processing query: {query}")
        
        # Get raw Tavily results
        raw_results = tavily_tool.invoke(query)
        logger.info(f"Raw Tavily results: {json.dumps(raw_results, indent=2)}")
        
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
        output = format_raw_results(filtered_results, 0)
        
        if not output.strip():
            logger.warning("No relevant results found")
            return "No cybersecurity incidents relevant to Australian businesses found for the requested timeframe.", None
        
        overall_end_time = time.time()
        generation_time = overall_end_time - overall_start_time

        await database.add_research(query, output, generation_time, selected_server['name'])
        return output, generation_time
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return f"Error processing query: {str(e)}", None

# Function to format raw results
def format_raw_results(results, start_count):
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

# Example usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = "june 1 to july 1, 2025"
    result = perform_search(user_query)
    print("\nSearch Results:")
    print(result)
