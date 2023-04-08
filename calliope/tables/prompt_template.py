from datetime import datetime
from typing import Any, Dict

import jinja2

from piccolo.table import Table
from piccolo.columns import (
    Timestamptz,
    Varchar,
    Text,
)


class PromptTemplate(Table):
    """
    A template for a text prompt to be sent to an inference model, with support for template
    variables and control structures in Jinja2 format.
    """

    # A slug naming the prompt template. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # The name of the template.
    title = Varchar(length=80)

    # Description and commentary on the template. What is it for? Which model(s) does it target?
    description = Text()

    # The raw template text, in Jinja2 format.
    text = Text()

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    def render(self, context: Dict[str, Any]) -> str:
        """
        Renders the template, replacing variables and executing control structures.

        Args:
            context: a dictionary of context variables available in the template.

        Returns:
            the rendered template.
        """
        environment = jinja2.Environment()
        template = environment.from_string(self.text)
        return template.render(context)
