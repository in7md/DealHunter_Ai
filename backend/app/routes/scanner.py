from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse
from app.services.scanner import ScannerService

scanner_service = ScannerService()

async def stream_deals(request):
    sources = request.query_params.get("sources", "opensooq,instagram")
    return EventSourceResponse(
        scanner_service.run_scan(sources_param=sources),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        },
        ping=15
    )

routes = [
    Route("/stream", stream_deals)
]
