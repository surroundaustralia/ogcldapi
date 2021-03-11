# from: https://gist.github.com/erny/2569d6555bd9349e2afc110a63ffca1a#file-renderers-py

"""Simple content negotiation

Usage:

    Example 1:

        from renderers import render

        @router.post("/myapp/items/")
        async def api_login(item: Item, accept: Optional[str] = Header(default='application/jwt')):
            ...
            stored_item = store.save(item)
            return render(stored_item, accept, status_code=201)

    Example 2:

        from renderers import JSONRenderer, XMLRenderer, PlainTextRenderer, render

        class MyItemRenderer(PlainTextRenderer):

            def render(
                self, value: Any, status_code: int = 200,
                headers: Optional[Dict[str, str]] = None, media_type: Optional[str] = None,
            ):
                try:
                    value = "\n".join([f"{fld}: {getattr(value, fld)}" for fld in value.__fields__])
                except AttributeError:
                    value = str(value)
                return super().render(value, status_code=status_code, headers=headers, media_type=media_type)

        @router.post("/myapp/items/")
        async def api_login(item: Item, accept: Optional[str] = Header(default='application/jwt')):
            ...
            stored_item = store.save(item)
            return render(
                stored_item, accept, status_code=201,
                renderers=[JSONRenderer, XMLRenderer, MyItemRenderer])
"""
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type

import json

from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse


class Renderer:
    media_types: ClassVar[Tuple[str, ...]] = ('application/jwt', 'text/plain')

    def render(
        self, value: Any, status_code: int = 200,
        headers: Optional[Dict[str, str]] = None, media_type: Optional[str] = None,
    ):
        if not isinstance(value, str):
            value = str(value)
        return PlainTextResponse(value, status_code=status_code, headers=headers, media_type=media_type)


PlainTextRenderer = Renderer


class JSONRenderer(Renderer):
    media_types = ('application/json', )

    def render(
        self, value: Any, status_code: int = 200,
        headers: Optional[Dict[str, str]] = None, media_type: Optional[str] = None,
    ):
        return JSONResponse(value, status_code=status_code, headers=headers, media_type=media_type)

class HTMLRenderer(Renderer):
    media_types = ('text/html', )

    def render(
        self, value: Any, status_code: int = 200,
        headers: Optional[Dict[str, str]] = None, media_type: Optional[str] = None,
    ):
        return HTMLResponse(value, status_code=status_code, headers=headers, media_type=media_type)


# class XMLRenderer(Renderer):
#     media_types = ('application/xml', 'text/xml')
#
#     def render(
#         self, value: Any, status_code: int = 200,
#         headers: Optional[Dict[str, str]] = None, media_type: Optional[str] = None,
#     ):
#         try:
#             value = value.json()
#         except AttributeError:
#             value = json.dumps(value)
#         from json2xml.json2xml import Json2xml
#         value = Json2xml(value).to_xml()
#         return PlainTextResponse(value, status_code=status_code, headers=headers, media_type=media_type)


def render(
    value: Any,
    accept: Optional[str],
    status_code: Optional[int],
    headers: Optional[Dict[str, str]] = None,
    renderers: Optional[List[Type]] = None,
):
    """Render response taking into accout the requested media type in 'accept'"""
    renderers = renderers or [JSONRenderer, PlainTextRenderer]
    if accept:
        for media_type in accept.split(','):
            media_type = media_type.split(';')[0].strip()
            for renderer in renderers:
                if media_type in renderer.media_types:
                    return renderer().render(value, status_code=status_code, headers=headers, media_type=media_type)
    renderer = renderers[0]
    media_type = renderer.media_types[0]
    return renderer().render(value, status_code=status_code, headers=headers, media_type=media_type)
