import azure.functions as func
import json

def get_root(req: func.HttpRequest) -> func.HttpResponse:
    """Root endpoint"""
    return func.HttpResponse(
        json.dumps({
            "message": "AI Datawrapper Agent API - Running on Azure Functions",
            "version": "1.0.0"
        }),
        status_code=200,
        mimetype="application/json"
    ) 