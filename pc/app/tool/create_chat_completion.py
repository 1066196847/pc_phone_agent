from typing import Any, List, Optional, Type, Union, get_args, get_origin

from pydantic import BaseModel, Field

from app.tool import BaseTool


class CreateChatCompletion(BaseTool):
    name: str = "create_chat_completion"
    # 使用指定的输出格式
    description: str = (
        "Creates a structured completion with specified output formatting."
    )

    # Type mapping for JSON schema
    type_mapping: dict = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array",
    }
    response_type: Optional[Type] = None
    # 实例化后，required的取值是['response']
    required: List[str] = Field(default_factory=lambda: ["response"])

    def __init__(self, response_type: Optional[Type] = str):
        """Initialize with a specific response type."""
        super().__init__()
        self.response_type = response_type
        self.parameters = self._build_parameters()

    # 函数功能：根据不同的response_type，设置不同的输出格式
    # 在_build_parameters+_create_type_schema中专门定义了下面几种response_type
    # 1、str
    # 2、BaseModel的子类
    # 3、get_origin(self.response_type) = None
    # 4、get_origin(self.response_type) = list
    # 5、get_origin(self.response_type) = dict
    # 6、get_origin(self.response_type) = Union
    def _build_parameters(self) -> dict:
        """Build parameters schema based on response type."""
        if self.response_type == str:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        # 应发送给用户的响应文本
                        "description": "The response text that should be delivered to the user.",
                    },
                },
                "required": self.required,
            }

        # isinstance(self.response_type, type) 这个基本上都会满足，但是是否是BaseModel的子类就不一定了
        # 如果是BaseModel的子类的话，就看这个子类定义了哪些字段，openai模型返回值就必须包含这些字段
        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            # 如果一个BaseModel的子类如下
            # class User(BaseModel):
            #     name: str
            #     age: int
            # 那么schema的取值如下
            # {
            # 	'properties': {
            # 		'name': {
            # 			'title': 'Name',
            # 			'type': 'string'
            # 		},
            # 		'age': {
            # 			'title': 'Age',
            # 			'type': 'integer'
            # 		}
            # 	},
            # 	'required': ['name', 'age'],
            # 	'title': 'User',
            # 	'type': 'object'
            # }
            schema = self.response_type.model_json_schema()
            return {
                "type": "object",
                "properties": schema["properties"],
                "required": schema.get("required", self.required), #['response']
            }

        return self._create_type_schema(self.response_type)

    def _create_type_schema(self, type_hint: Type) -> dict:
        """Create a JSON schema for the given type."""
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        # Handle primitive types
        if origin is None:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": self.type_mapping.get(type_hint, "string"),
                        "description": f"Response of type {type_hint.__name__}",
                    }
                },
                "required": self.required,
            }

        # Handle List type
        if origin is list:
            item_type = args[0] if args else Any
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "array",
                        "items": self._get_type_info(item_type),
                    }
                },
                "required": self.required,
            }

        # Handle Dict type
        if origin is dict:
            value_type = args[1] if len(args) > 1 else Any
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "object",
                        "additionalProperties": self._get_type_info(value_type),
                    }
                },
                "required": self.required,
            }

        # Handle Union type
        if origin is Union:
            return self._create_union_schema(args)

        return self._build_parameters()

    def _get_type_info(self, type_hint: Type) -> dict:
        """Get type information for a single type."""
        if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
            return type_hint.model_json_schema()

        return {
            "type": self.type_mapping.get(type_hint, "string"),
            "description": f"Value of type {getattr(type_hint, '__name__', 'any')}",
        }

    def _create_union_schema(self, types: tuple) -> dict:
        """Create schema for Union types."""
        return {
            "type": "object",
            "properties": {
                "response": {"anyOf": [self._get_type_info(t) for t in types]}
            },
            "required": self.required,
        }

    async def execute(self, required: list | None = None, **kwargs) -> Any:
        """Execute the chat completion with type conversion. 通过类型转换执行聊天对话。

        Args:
            required: List of required field names or None   必填字段名列表或无
            **kwargs: Response data

        Returns:
            Converted response based on response_type        基于response_type的转换响应
        """
        required = required or self.required

        # Handle case when required is a list
        if isinstance(required, list) and len(required) > 0:
            if len(required) == 1:
                required_field = required[0]
                result = kwargs.get(required_field, "")
            else:
                # Return multiple fields as a dictionary
                return {field: kwargs.get(field, "") for field in required}
        else:
            required_field = "response"
            result = kwargs.get(required_field, "")

        # Type conversion logic
        if self.response_type == str:
            return result

        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            return self.response_type(**kwargs)

        if get_origin(self.response_type) in (list, dict):
            return result  # Assuming result is already in correct format

        try:
            return self.response_type(result)
        except (ValueError, TypeError):
            return result
