from contextvars import ContextVar

request_id_var: ContextVar = ContextVar("request_id")
