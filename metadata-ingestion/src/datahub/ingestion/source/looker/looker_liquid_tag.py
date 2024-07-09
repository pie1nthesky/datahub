from functools import lru_cache
from typing import ClassVar, Optional, TextIO, cast

from liquid import Environment
from liquid.ast import Node
from liquid.context import Context
from liquid.parse import expect, get_parser
from liquid.stream import TokenStream
from liquid.tag import Tag
from liquid.template import BoundTemplate
from liquid.token import TOKEN_EXPRESSION, TOKEN_LITERAL, TOKEN_TAG, Token


class CustomTagException(Exception):
    def __init__(self, message):
        super().__init__(message)


class ConditionNode(Node):
    def __init__(self, tok: Token, sql_or_lookml_reference: str, filter_name: str):
        self.tok = tok

        self.sql_or_lookml_reference = sql_or_lookml_reference

        self.filter_name = filter_name

    def render_to_output(self, context: Context, buffer: TextIO) -> Optional[bool]:
        filter_value: Optional[str] = cast(
            str, context.globals.get(self.filter_name)
        )  # to silent lint

        if filter_value is None:
            raise CustomTagException(
                f'filter {self.filter_name} value is not provided for "condition" tag'
            )

        filter_value = filter_value.strip()

        buffer.write(f"{self.sql_or_lookml_reference}='{filter_value}'")

        return True


# Define the custom tag
class ConditionTag(Tag):
    """
    ConditionTag is the equivalent implementation of looker's custom liquid tag "condition".
    Refer doc: https://cloud.google.com/looker/docs/templated-filters#basic_usage

    Refer doc to see how to write liquid custom tag: https://jg-rp.github.io/liquid/guides/custom-tags

    This class render the below tag as order.region='ap-south-1' if order_region is provided in config.liquid_variables
    as order_region: 'ap-south-1'
        {% condition order_region %} order.region {% endcondition %}

    """

    TAG_START: ClassVar[str] = "condition"
    TAG_END: ClassVar[str] = "endcondition"
    name: str = "condition"

    def __init__(self, env: Environment):
        super().__init__(env)
        self.parser = get_parser(self.env)

    def parse(self, stream: TokenStream) -> Node:
        expect(stream, TOKEN_TAG, value=ConditionTag.TAG_START)

        start_token = stream.current

        stream.next_token()
        expect(stream, TOKEN_EXPRESSION)
        filter_name: str = stream.current.value.strip()

        stream.next_token()
        expect(stream, TOKEN_LITERAL)

        sql_or_lookml_reference: str = stream.current.value.strip()

        stream.next_token()
        expect(stream, TOKEN_TAG, value=ConditionTag.TAG_END)

        return ConditionNode(
            tok=start_token,
            sql_or_lookml_reference=sql_or_lookml_reference,
            filter_name=filter_name,
        )


custom_tags = [ConditionTag]


@lru_cache(maxsize=1)
def _create_env() -> Environment:
    env: Environment = Environment()
    # register tag. One time activity
    for custom_tag in custom_tags:
        env.add_tag(custom_tag)
    return env


def create_template(text: str) -> BoundTemplate:
    env: Environment = _create_env()
    return env.from_string(text)
