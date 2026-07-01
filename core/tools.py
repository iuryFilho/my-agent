import inspect
import json
from dataclasses import dataclass, field
from typing import Callable, Any, Annotated, Union, Final, get_origin, get_args


@dataclass
class Tools:
    TOOL_SCHEMA_ATTR: Final[str] = "__tool_schema__"
    tools: dict[str, Callable[..., Any]] = field(default_factory=dict)

    @staticmethod
    def _annotation_to_schema(annotation: Any) -> dict[str, Any]:
        schema: dict[str, Any] = {"type": "string"}
        description: str | None = None
        origin = get_origin(annotation)

        if origin is Annotated:
            base_type, *meta = get_args(annotation)
            schema = Tools._annotation_to_schema(base_type)
            if meta:
                description = str(meta[0])
        elif annotation in (int, float):
            schema = {"type": "number"}
        elif annotation is bool:
            schema = {"type": "boolean"}
        elif annotation is dict:
            schema = {"type": "object"}
        elif annotation is list:
            schema = {"type": "array"}
        elif origin is list:
            schema = {
                "type": "array",
                "items": Tools._annotation_to_schema(get_args(annotation)[0]),
            }
        elif origin is dict:
            schema = {"type": "object"}
        elif origin is Union:
            any_of = [
                Tools._annotation_to_schema(arg)
                for arg in get_args(annotation)
                if arg is not type(None)
            ]
            if any_of:
                schema = any_of[0]

        if description:
            schema["description"] = description

        return schema

    @staticmethod
    def _schema_to_callable(func: Callable[..., Any]) -> dict[str, Any]:
        sig = inspect.signature(func)
        annotations = inspect.get_annotations(func)

        parameters: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

        for name, param in sig.parameters.items():
            annotation = annotations.get(name, inspect.Parameter.empty)

            if annotation is inspect.Parameter.empty:
                continue

            parameters["properties"][name] = Tools._annotation_to_schema(annotation)

            if param.default is inspect.Parameter.empty:
                parameters["required"].append(name)

        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__.strip() or "No description provided.",
                "parameters": parameters,
                "strict": True,
            },
        }

    def get_schemas(self) -> dict[str, Any]:
        out: list[dict[str, Any]] = []
        for fn in self.tools.values():
            s = getattr(fn, self.TOOL_SCHEMA_ATTR, None)
            if s is not None:
                out.append(s)
        return out

    def register(self, func: Callable[..., Any]) -> Callable[..., Any]:
        if getattr(func, self.TOOL_SCHEMA_ATTR, None) is None:
            setattr(func, self.TOOL_SCHEMA_ATTR, self._schema_to_callable(func))
        self.tools[func.__name__] = func
        return func

    def execute(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        fn_payload: dict[str, Any] = tool_call.get("function", {})
        fn_name = fn_payload.get("name")
        fn = self.tools.get(fn_name) if fn_name else None

        if not fn:
            return {"error": f"Tool '{fn_name}' not found."}

        try:
            args = json.loads(fn_payload.get("arguments", "{}"))
            result = fn(**args)
            return result if isinstance(result, dict) else {"result": result}
        except KeyboardInterrupt:
            raise
        except Exception as e:
            return {"error": str(e)}
