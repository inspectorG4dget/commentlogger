import io
import tokenize


def extractComment(line):
    """
    Extract comment from a line of sourcecode using Python's tokenizer.

    :param line: A line of Python code
    :returns: The comment text (without the # symbol) or None if no comment exists
    """
    try:
        tokens = tokenize.generate_tokens(io.StringIO(line).readline)  # tokenize expects bytes
        for token in tokens:
            if token.type == tokenize.COMMENT:
                return token.string[1:].strip()  # Remove the leading # and whitespace
    except tokenize.TokenError:  # Incomplete line (e.g., unclosed string) - no valid comment
        return None

    return None
