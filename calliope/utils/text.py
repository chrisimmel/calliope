import json
import re
from typing import Any, cast, Dict, List, Optional, Sequence, Union
import unicodedata


from google.cloud import translate_v2 as translate


def slugify(value: Any, allow_unicode: bool = False) -> str:
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


alphabets = "([A-Za-z])"
prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = "(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"  # noqa: E501
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov|edu|me)"
digits = "([0-9])"
multiple_dots = r"\.{2,}"
abbreviations = [
    "etc.", "i.e.", "e.g.", "vs.", "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.",
    "Inc.", "Ltd.", "Co.", "Jr.", "Sr.", "St.", "Ave.", "Blvd.", "Rd.",
    "Ph.D.", "M.D.", "B.A.", "M.A.", "U.S.", "U.K.", "U.N."
]


def split_into_sentences(text: str) -> List[str]:
    """
    Splits text into a list of sentences.
    Improved from: https://stackoverflow.com/questions/4576077/how-can-i-split-a-text-into-sentences
    """  # noqa: E501

    text = " " + text + "  "
    text = text.replace("\n", " ")

    # Handle all abbreviations
    for abbr in abbreviations:
        if abbr in text:
            # Replace period in abbreviation with placeholder
            abbr_no_period = abbr.replace(".", "<prd>")
            text = text.replace(abbr, abbr_no_period)

    text = re.sub(prefixes, "\\1<prd>", text)
    text = re.sub(websites, "<prd>\\1", text)
    text = re.sub(digits + "[.]" + digits, "\\1<prd>\\2", text)
    text = re.sub(
        multiple_dots, lambda match: "<prd>" * len(match.group(0)) + "<stop>", text
    )

    text = re.sub("\s" + alphabets + "[.] ", " \\1<prd> ", text)
    text = re.sub(acronyms + " " + starters, "\\1<stop> \\2", text)
    text = re.sub(
        alphabets + "[.]" + alphabets + "[.]" + alphabets + "[.]",
        "\\1<prd>\\2<prd>\\3<prd>",
        text,
    )
    text = re.sub(alphabets + "[.]" + alphabets + "[.]", "\\1<prd>\\2<prd>", text)
    text = re.sub(" " + suffixes + "[.] " + starters, " \\1<stop> \\2", text)
    text = re.sub(" " + suffixes + "[.]", " \\1<prd>", text)
    text = re.sub(" " + alphabets + "[.]", " \\1<prd>", text)

    text = text.replace(""", '"')
    text = text.replace(""", '"')
    text = text.replace("'", "'")
    text = text.replace("'", "'")

    text = text.replace('."', '".')
    text = text.replace('!"', '"!')
    text = text.replace('?"', '"?')

    text = text.replace(".'", "'.")
    text = text.replace("!'", "'!")
    text = text.replace("?'", "'?")

    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")

    text = text.replace('".', '."')
    text = text.replace('"!', '!"')
    text = text.replace('"?', '?"')

    text = text.replace("'.", ".'")
    text = text.replace("'!", "!'")
    text = text.replace("'?", "?'")

    text = text.replace("<prd>", ".")
    sentences = text.split("<stop>")
    sentences = sentences[:-1]
    sentences = [s.strip() for s in sentences]
    return sentences


def ends_with_punctuation(string: str) -> bool:
    """
    Determines whether the string ends with a simple set of recognized
    punctuation marks. Is simplistic and English/Latin-centric.
    """
    return len(string) > 0 and string[-1] in (
        ".",
        "!",
        "?",
        ":",
        ",",
        ";",
        "-",
        '"',
        "'",
    )


def balance_quotes(string: str) -> str:
    """
    Counts the quotes (") in string. If there are an odd number,
    appends an additional quote in returned string. Otherwise
    returns the unmodified original string.
    """
    num_quotes_mod_2 = string.count('"') % 2
    return (string + '"') if num_quotes_mod_2 else string


def translate_text(target: str, text: Union[str, bytes]) -> str:
    """Translates text into the target language.

    Target must be an ISO 639-1 language code.
    See https://g.co/cloud/translate/v2/translate-reference#supported_languages
    """
    translate_client = translate.Client()

    if isinstance(text, bytes):
        text = text.decode("utf-8")

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.translate(text, target_language=target)

    translation = cast(str, result.get("translatedText", text)) if result else text

    print(f"Translation: {translation}")
    print(f"Detected source language: {result['detectedSourceLanguage']}")

    return translation


def load_llm_output_as_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to interpret a piece of text presumably coming from an LLM as JSON,
    with tolerance for some of the oddities we sometimes see in LLM-generated
    JSON.

    Returns None if the input text doesn't contain valid JSON.
    """
    # TODO: Look at using a LangChain PydanticOutputParser instead.
    if not text:
        return None

    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3]
        print(f"JSON output detected. Stripped to: {text}")

    text = text.replace("\n", " ")

    lbrace_index = text.find("{")
    rbrace_index = text.rfind("}")
    if lbrace_index < 0 or rbrace_index < lbrace_index:
        return None

    text = text[lbrace_index : rbrace_index + 1]
    try:
        # Use json.loads() to parse the text as JSON.
        data = json.loads(text)

        # If the result is a dictionary, return it.
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    return None


def format_sequence(items: Sequence[Any]) -> str:
    """
    Formats a sequence of zero or more values, using normal English punctuation
    and an Oxford comma when appropriate.
    """
    count = len(items)
    if count == 0:
        return ""
    elif count == 1:
        return f"{items[0]}"
    elif count == 2:
        return f"{items[0]} and {items[1]}"
    else:
        return f"{', '.join(items[:-1])}, and {items[-1]}"
