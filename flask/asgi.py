import asyncio

from .ctx import RequestContext
from .signals import request_started

class ASGIMixin:
    def asgi_app(self, scope):
        type_ = scope['type']
        handler = self.asgi_map[type_]
        return handler(scope)

    def dispatch_asgi_request(self):
        self.try_trigger_before_first_request_functions()
        try:
            request_started.send(self)
            rv = self.preprocess_request()
            if rv is None:
                rv = self.dispatch_request()
        except Exception as e:
            rv = self.handle_user_exception(e)
        return rv

    def asgi_request_context(self, scope, receiver, sender):
        return RequestContext(self, scope, self.asgi_request_class(scope, receiver, sender))

    async def asgi_finalize_response(self, response, scope, receive, send):
        if asyncio.iscoroutine(response):
            response = await response
        response = self.finalize_request(response)
        await response(scope)(receive, send)

    def asgi_handler(self, scope):
        async def app(receive, send):
            ctx = self.asgi_request_context(scope, receive, send)
            error = None
            try:
                try:
                    ctx.push()
                    response = self.dispatch_asgi_request()
                except Exception as e:
                    error = e
                    response = self.handle_exception(e)
                except:
                    error = sys.exc_info()[1]
                    ctx.auto_pop(error)
                    raise
                await self.asgi_finalize_response(response, scope, receive, send)
            finally:
                if self.should_ignore_error(error):
                    error = None
                ctx.auto_pop(error)
        return app
