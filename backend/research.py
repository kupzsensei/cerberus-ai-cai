import os
import logging
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_tavily import TavilySearch
import requests
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
async def perform_search(query, ollama_server_name: str = None, ollama_model: str = "granite3.3"):
    try:
        # Start timer for the entire research process
        overall_start_time = time.time()

        # Determine which Ollama server to use
        selected_server = None
        if ollama_server_name:
            selected_server = await database.get_ollama_server_by_name(ollama_server_name)
        
        if not selected_server:
            # Fallback to default if not found or not provided
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
        output = format_raw_results(filtered_results, 0, llm)
        
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