"""HTTP layer: FastAPI routers and request/response wiring.

Route handlers live here as endpoints are implemented. This layer should stay
thin — it validates input via schemas/, delegates to services/, and returns
the result. No business logic belongs here.
"""
