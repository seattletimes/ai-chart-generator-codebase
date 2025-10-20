import azure.functions as func
from endpoints.datawrapper import create_chart_id, update_chart
from endpoints.root import get_root

# Create the Azure Function app
app = func.FunctionApp()

@app.route(route="create_chart_id", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def create_chart_id_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Create Datawrapper chart ID and upload data - Step 1"""
    return create_chart_id(req)

@app.route(route="update_chart", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def update_chart_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Update chart metadata and publish - Step 2"""
    return update_chart(req)

@app.route(route="", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def root(req: func.HttpRequest) -> func.HttpResponse:
    """Root endpoint"""
    return get_root(req) 