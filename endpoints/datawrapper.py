import azure.functions as func
import logging
import requests
import json
import pandas as pd
import io
import os
import re
import urllib3
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

# Suppress SSL warnings for local development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def make_datawrapper_request(method: str, url: str, headers: Dict[str, str], **kwargs) -> requests.Response:
    """Make a request to Datawrapper API with robust SSL verification fallback for corporate environments"""
    
    # Strategy 1: Try with different SSL configurations
    ssl_strategies = [
        # Strategy 1a: Default SSL verification
        {"verify": True, "description": "Default SSL verification"},
        # Strategy 1b: No SSL verification (for Zscaler/proxy environments)
        {"verify": False, "description": "No SSL verification"},
        # Strategy 1c: Custom SSL context with relaxed verification
        {"verify": False, "description": "Custom SSL context", "ssl_context": True}
    ]
    
    # Strategy 2: Try with different session configurations
    session_strategies = [
        # Strategy 2a: Default requests
        {"use_session": False, "description": "Default requests"},
        # Strategy 2b: Custom session with retry logic
        {"use_session": True, "description": "Custom session with retries"}
    ]
    
    # Try all combinations of strategies
    for ssl_strategy in ssl_strategies:
        for session_strategy in session_strategies:
            try:
                logging.info(f"Trying Datawrapper API call with: {ssl_strategy['description']}, {session_strategy['description']}")
                
                if session_strategy["use_session"]:
                    # Use custom session with retry logic
                    session = requests.Session()
                    session.headers.update(headers)
                    
                    # Configure session for corporate environments
                    if ssl_strategy.get("ssl_context"):
                        import ssl
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        session.verify = False
                    else:
                        session.verify = ssl_strategy["verify"]
                    
                    # Add retry logic
                    from requests.adapters import HTTPAdapter
                    from urllib3.util.retry import Retry
                    
                    retry_strategy = Retry(
                        total=3,
                        backoff_factor=1,
                        status_forcelist=[429, 500, 502, 503, 504],
                    )
                    adapter = HTTPAdapter(max_retries=retry_strategy)
                    session.mount("http://", adapter)
                    session.mount("https://", adapter)
                    
                    response = session.request(method, url, **kwargs)
                else:
                    # Use direct requests
                    if ssl_strategy.get("ssl_context"):
                        import ssl
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        response = requests.request(method, url, headers=headers, verify=False, **kwargs)
                    else:
                        response = requests.request(method, url, headers=headers, verify=ssl_strategy["verify"], **kwargs)
                
                response.raise_for_status()
                logging.info(f"Successfully made Datawrapper API call using: {ssl_strategy['description']}, {session_strategy['description']}")
                return response
                
            except requests.exceptions.SSLError as ssl_error:
                logging.warning(f"SSL error with {ssl_strategy['description']}, {session_strategy['description']}: {str(ssl_error)}")
                continue
            except requests.exceptions.RequestException as req_error:
                logging.warning(f"Request error with {ssl_strategy['description']}, {session_strategy['description']}: {str(req_error)}")
                continue
            except Exception as e:
                logging.warning(f"Unexpected error with {ssl_strategy['description']}, {session_strategy['description']}: {str(e)}")
                continue
    
    # If all strategies failed, try one last approach with urllib3
    try:
        logging.info("Trying final fallback with urllib3 for Datawrapper API")
        import urllib3
        
        # Prepare request data
        data = kwargs.get('data')
        json_data = kwargs.get('json')
        
        if json_data:
            data = json.dumps(json_data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        
        http = urllib3.PoolManager(cert_reqs='CERT_NONE', assert_hostname=False)
        response = http.request(method, url, body=data, headers=headers, timeout=30.0)
        
        if response.status in [200, 201, 204]:  # Success status codes
            logging.info("Successfully made Datawrapper API call using urllib3 fallback")
            # Create a mock response object that mimics requests.Response
            mock_response = type('MockResponse', (), {
                'status_code': response.status,
                'json': lambda: json.loads(response.data.decode('utf-8')) if response.data else {},
                'raise_for_status': lambda: None if response.status < 400 else Exception(f"HTTP {response.status}")
            })()
            return mock_response
    except Exception as e:
        logging.warning(f"urllib3 fallback also failed: {str(e)}")
    
    # If we get here, all strategies failed
    raise Exception("All Datawrapper API call strategies failed. This might be due to corporate firewall/proxy restrictions.")


def create_chart_id(req: func.HttpRequest) -> func.HttpResponse:
    """Create a Datawrapper chart ID and upload data - Step 1 of chart creation"""
    logging.info('Python HTTP trigger function processed a request for Datawrapper chart ID creation.')
    
    try:
        # Get Datawrapper API token
        datawrapper_token = os.environ.get("DATAWRAPPER_TOKEN")
        if not datawrapper_token:
            return func.HttpResponse(
                json.dumps({"status": "error", "message": "Datawrapper API token not configured"}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Parse request body
        req_body = req.get_json()
        
        # Extract form fields
        file_url = req_body.get('file_url')
        chart_type = req_body.get('chart_type')
        title = req_body.get('title')
        
        # Validate required fields
        if not file_url or not chart_type or not title:
            return func.HttpResponse(
                json.dumps({"status": "error", "message": "Missing required fields: file_url, chart_type, title"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Validate file URL format
        if not is_valid_file_url(file_url):
            return func.HttpResponse(
                json.dumps({"status": "error", "message": "Invalid file URL. Must be a Google Sheets URL"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Download and parse file from URL
        try:
            df = download_and_parse_file(file_url)
        except Exception as e:
            logging.error(f"Error downloading/parsing file: {str(e)}")
            return func.HttpResponse(
                json.dumps({"status": "error", "message": f"Error processing file: {str(e)}"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Convert DataFrame to CSV string
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        # Datawrapper API headers
        headers = {
            "Authorization": f"Bearer {datawrapper_token}",
            "Content-Type": "application/json"
        }
        
        # Step 1: Create chart
        create_chart_url = "https://api.datawrapper.de/v3/charts"
        create_chart_data = {
            "type": chart_type,
            "title": title
        }
        
        create_response = make_datawrapper_request("POST", create_chart_url, headers, json=create_chart_data)
        chart_id = create_response.json()["id"]
        
        # Step 2: Upload data
        data_url = f"https://api.datawrapper.de/v3/charts/{chart_id}/data"
        data_headers = {
            "Authorization": f"Bearer {datawrapper_token}",
            "Content-Type": "text/csv"
        }
        
        data_response = make_datawrapper_request("PUT", data_url, data_headers, data=csv_data.encode('utf-8'))
        
        # Return success response with chart_id
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "chart_id": chart_id,
                "message": "Chart created and data uploaded successfully"
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling Datawrapper API: {str(e)}")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": f"Error calling Datawrapper API: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error in create_chart_id function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

def update_chart(req: func.HttpRequest) -> func.HttpResponse:
    """Update chart metadata and publish - Step 2 of chart creation"""
    logging.info('Python HTTP trigger function processed a request for Datawrapper chart update.')
    
    try:
        # Get Datawrapper API token
        datawrapper_token = os.environ.get("DATAWRAPPER_TOKEN")
        if not datawrapper_token:
            return func.HttpResponse(
                json.dumps({"status": "error", "message": "Datawrapper API token not configured"}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Parse request body
        req_body = req.get_json()
        
        # Extract form fields
        chart_id = req_body.get('chart_id')
        intro = req_body.get('intro', '')
        byline = req_body.get('byline', '')
        source_name = req_body.get('source_name')
        source_url = req_body.get('source_url', '')
        custom_colors = req_body.get('custom_colors', '')
        
        # Validate required fields
        if not chart_id or not source_name:
            return func.HttpResponse(
                json.dumps({"status": "error", "message": "Missing required fields: chart_id, source_name"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Parse custom colors if provided
        custom_colors_dict = {}
        if custom_colors:
            try:
                custom_colors_dict = json.loads(custom_colors) if isinstance(custom_colors, str) else custom_colors
            except json.JSONDecodeError:
                return func.HttpResponse(
                    json.dumps({"status": "error", "message": "Invalid custom_colors JSON format"}),
                    status_code=400,
                    mimetype="application/json"
                )
        
        # Datawrapper API headers
        headers = {
            "Authorization": f"Bearer {datawrapper_token}",
            "Content-Type": "application/json"
        }
        
        # Step 3: Update metadata
        metadata_url = f"https://api.datawrapper.de/v3/charts/{chart_id}"
        metadata_data = {
            "metadata": {
                "describe": {
                    "intro": intro,
                    "byline": byline,
                    "source-name": source_name,
                    "source-url": source_url
                }
            }
        }
        
        # Add custom colors if provided
        if custom_colors_dict:
            metadata_data["metadata"]["visualize"] = {
                "custom-colors": custom_colors_dict
            }
        
        metadata_response = make_datawrapper_request("PATCH", metadata_url, headers, json=metadata_data)
        
        # Step 4: Publish chart
        publish_url = f"https://api.datawrapper.de/v3/charts/{chart_id}/publish"
        publish_response = make_datawrapper_request("POST", publish_url, headers)
        
        # Return success response with chart_url
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "chart_id": chart_id,
                "chart_url": f"https://www.datawrapper.de/_/{chart_id}/",
                "message": "Chart metadata updated and published successfully"
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling Datawrapper API: {str(e)}")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": f"Error calling Datawrapper API: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error in update_chart function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )



def is_valid_file_url(url: str) -> bool:
    """Validate if the URL is a Google Sheets URL"""
    try:
        parsed_url = urlparse(url)
        
        # Check for Google Sheets
        if 'docs.google.com' in parsed_url.netloc and '/spreadsheets/' in parsed_url.path:
            return True
        
        return False
    except:
        return False

def download_and_parse_file(file_url: str) -> pd.DataFrame:
    """Download and parse file from Google Sheets URL"""
    
    if 'docs.google.com' in file_url:
        return download_google_sheet(file_url)
    else:
        raise ValueError("Unsupported file URL format. Only Google Sheets URLs are supported.")

def download_google_sheet(url: str) -> pd.DataFrame:
    """Download and parse Google Sheet with robust SSL handling for corporate environments"""
    try:
        # Convert Google Sheets URL to CSV export URL
        # Extract sheet ID from URL
        sheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not sheet_id_match:
            raise ValueError("Could not extract sheet ID from Google Sheets URL")
        
        sheet_id = sheet_id_match.group(1)
        csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
        
        # Strategy 1: Try with different SSL configurations
        ssl_strategies = [
            # Strategy 1a: Default SSL verification
            {"verify": True, "description": "Default SSL verification"},
            # Strategy 1b: No SSL verification (for Zscaler/proxy environments)
            {"verify": False, "description": "No SSL verification"},
            # Strategy 1c: Custom SSL context with relaxed verification
            {"verify": False, "description": "Custom SSL context", "ssl_context": True}
        ]
        
        # Strategy 2: Try with different session configurations
        session_strategies = [
            # Strategy 2a: Default requests session
            {"use_session": False, "description": "Default requests"},
            # Strategy 2b: Custom session with retry logic
            {"use_session": True, "description": "Custom session with retries"}
        ]
        
        # Strategy 3: Try with different headers (mimic browser)
        header_strategies = [
            # Strategy 3a: Minimal headers
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            # Strategy 3b: Full browser headers
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        ]
        
        # Try all combinations of strategies
        for ssl_strategy in ssl_strategies:
            for session_strategy in session_strategies:
                for headers in header_strategies:
                    try:
                        logging.info(f"Trying Google Sheets download with: {ssl_strategy['description']}, {session_strategy['description']}")
                        
                        if session_strategy["use_session"]:
                            # Use custom session with retry logic
                            session = requests.Session()
                            session.headers.update(headers)
                            
                            # Configure session for corporate environments
                            if ssl_strategy.get("ssl_context"):
                                import ssl
                                ssl_context = ssl.create_default_context()
                                ssl_context.check_hostname = False
                                ssl_context.verify_mode = ssl.CERT_NONE
                                session.verify = False
                            else:
                                session.verify = ssl_strategy["verify"]
                            
                            # Add retry logic
                            from requests.adapters import HTTPAdapter
                            from urllib3.util.retry import Retry
                            
                            retry_strategy = Retry(
                                total=3,
                                backoff_factor=1,
                                status_forcelist=[429, 500, 502, 503, 504],
                            )
                            adapter = HTTPAdapter(max_retries=retry_strategy)
                            session.mount("http://", adapter)
                            session.mount("https://", adapter)
                            
                            response = session.get(csv_export_url, timeout=30)
                        else:
                            # Use direct requests
                            if ssl_strategy.get("ssl_context"):
                                import ssl
                                ssl_context = ssl.create_default_context()
                                ssl_context.check_hostname = False
                                ssl_context.verify_mode = ssl.CERT_NONE
                                response = requests.get(csv_export_url, headers=headers, timeout=30, verify=False)
                            else:
                                response = requests.get(csv_export_url, headers=headers, timeout=30, verify=ssl_strategy["verify"])
                        
                        response.raise_for_status()
                        
                        # Check if we got valid CSV data
                        content = response.text.strip()
                        if content and not content.startswith('<html'):  # Not an HTML error page
                            # Parse CSV data
                            df = pd.read_csv(io.StringIO(content))
                            logging.info(f"Successfully downloaded Google Sheet using: {ssl_strategy['description']}, {session_strategy['description']}")
                            return df
                        else:
                            logging.warning(f"Received HTML response instead of CSV data")
                            continue
                            
                    except requests.exceptions.SSLError as ssl_error:
                        logging.warning(f"SSL error with {ssl_strategy['description']}, {session_strategy['description']}: {str(ssl_error)}")
                        continue
                    except requests.exceptions.RequestException as req_error:
                        logging.warning(f"Request error with {ssl_strategy['description']}, {session_strategy['description']}: {str(req_error)}")
                        continue
                    except Exception as e:
                        logging.warning(f"Unexpected error with {ssl_strategy['description']}, {session_strategy['description']}: {str(e)}")
                        continue
        
        # If all strategies failed, try one last approach with urllib3
        try:
            logging.info("Trying final fallback with urllib3")
            import urllib3
            http = urllib3.PoolManager(cert_reqs='CERT_NONE', assert_hostname=False)
            response = http.request('GET', csv_export_url, timeout=30.0)
            
            if response.status == 200:
                content = response.data.decode('utf-8')
                if content and not content.startswith('<html'):
                    df = pd.read_csv(io.StringIO(content))
                    logging.info("Successfully downloaded Google Sheet using urllib3 fallback")
                    return df
        except Exception as e:
            logging.warning(f"urllib3 fallback also failed: {str(e)}")
        
        # If we get here, all strategies failed
        raise Exception("All download strategies failed. This might be due to corporate firewall/proxy restrictions or the sheet requires authentication.")
        
    except Exception as e:
        logging.error(f"Error downloading Google Sheet: {str(e)}")
        raise Exception(f"Failed to download Google Sheet: {str(e)}")
