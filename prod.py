import argparse
import ast
import logging
import re

import utils

# Get all available log levels
LOGLEVELS = {**logging._nameToLevel}

for k, v in logging._nameToLevel.items():
    if any(_k.startswith(k) and v==_v for _k, _v in logging._nameToLevel.items() if k != _k):  # noqa E225
        LOGLEVELS.pop(k)

LOGLEVELS = sorted(LOGLEVELS.keys())


def getArgs():
    """
    Get the command line arguments
    :return: parsed Namespace
    """
    args = argparse.ArgumentParser()
    args.add_argument('-i', dest='infilepath', type=str, required=True, help='input filepath')
    args.add_argument('-o', dest='outfilepath', type=str, required=True, help='output filepath')
    args.add_argument('-s', dest='stopwords', type=str, nargs="+", required=False, help='stopwords')

    return args.parse_args()


def parseComment(comment, stopwords=None):
    """
    Parse a comment to extract log level and message.

    :param comment: The comment text to parse
    :param stopwords: A list of stopwords to ignore if the comment starts with any of the stopwords
    :returns: A tuple of (logLevel, logMessage)
    """
    if not stopwords:
        stopwords = []

    level, _, logline = comment.partition(":")
    level = level.strip()
    logline = logline.strip()

    if not level:
        level = "INFO"
        logline = comment
    else:
        try:
            level = next(L for L in LOGLEVELS if L.startswith(level.upper()))
        except StopIteration:
            level = "INFO"
            logline = comment

    if any(logline.startswith(stopword) for stopword in stopwords):
        logline = ''

    return level, logline


def shouldSkipDecoratorLine(line, sourceCode):
    """
    Determine if a decorator line should be skipped based on whether it's
    a commentlogger import (name-agnostic).

    :param line: The line of code to check
    :param sourceCode: The full source code (needed to parse imports)
    :return: True if this decorator should be skipped, False otherwise
    """

    stripped = line.strip()
    if not stripped.startswith('@'):
        return False

    # Extract the decorator name
    decoratorMatch = re.match(r'@([\w.]+)\s*\(', stripped)
    if not decoratorMatch:
        return False

    decoratorName = decoratorMatch.group(1)
    baseName = decoratorName.split('.')[0]

    # Parse imports to check if this name comes from commentlogger
    try:
        tree = ast.parse(sourceCode)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == 'commentlogger':
                    for alias in node.names:
                        importedName = alias.asname if alias.asname else alias.name
                        if baseName == importedName or decoratorName == importedName:
                            return True
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'commentlogger':
                        importedName = alias.asname if alias.asname else 'commentlogger'
                        if baseName == importedName:
                            return True
    except Exception:
        pass

    return False


def extractLoggerInfo(sourceCode):
    """
    Extract logger name and decorated functions using AST (name-agnostic).

    :param sourceCode: str. The Python source code to analyze
    :return: A tuple of (loggerName, decoratedFunctions)
    """

    try:
        tree = ast.parse(sourceCode)

        # Track imports from commentlogger
        clNames = set()

        # Find all names imported from commentlogger
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == 'commentlogger':
                    for alias in node.names:
                        importedName = alias.asname if alias.asname else alias.name
                        clNames.add(importedName)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'commentlogger':
                        importedName = alias.asname if alias.asname else alias.name
                        clNames.add(importedName)

        loggerName = None
        decoratedFunctions = set()

        # Find decorated functions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        decoratorName = None

                        if isinstance(decorator.func, ast.Name):
                            decoratorName = decorator.func.id
                        elif isinstance(decorator.func, ast.Attribute):
                            if isinstance(decorator.func.value, ast.Name):
                                moduleName = decorator.func.value.id
                                if moduleName in clNames:
                                    decoratorName = f"{moduleName}.{decorator.func.attr}"

                        if not decoratorName:
                            continue
                        if decoratorName not in clNames and decoratorName.split('.')[0] not in clNames:
                            continue

                        if decorator.args and len(decorator.args) > 0:
                            arg = decorator.args[0]
                            if isinstance(arg, ast.Name):
                                loggerName = arg.id
                                decoratedFunctions.add(node.name)

        return loggerName, decoratedFunctions
    except Exception:
        return None, set()


def injectLogging(infilepath, outfilepath, stopwords):
    """
    Inject logging statements before lines with comments in a Python file.

    :param infilepath: str. Path to the input Python file
    :param outfilepath: str. Path to the output file
    :param stopwords: list of str. List of stopwords to ignore

    :returns: None
    """

    with open(infilepath) as infile:
        sourceCode = infile.read()

    loggerName, decoratedFunctions = extractLoggerInfo(sourceCode)

    if not loggerName:
        loggerName = "logger"

    lines = sourceCode.splitlines()
    newLines = []

    importsLogging = 'import logging' in sourceCode
    addedImports = False

    # map line numbers to function names and statement boundaries
    try:
        tree = ast.parse(sourceCode)
        lineToFunction = {}
        statementLines = set()  # Lines that start a new statement

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for i in range(node.lineno, node.end_lineno + 1 if node.end_lineno else node.lineno + 1):
                    lineToFunction[i] = node.name

        # Mark all lines that are the start of a statement
        for node in ast.walk(tree):
            if isinstance(node, ast.stmt):
                statementLines.add(node.lineno)
            # Also check for standalone expressions that are statements
            elif isinstance(node, ast.Expr) and hasattr(node, 'lineno'):
                statementLines.add(node.lineno)

    except Exception:
        lineToFunction = {}
        statementLines = set()

    # Build map of which lines have comments and should have logging injected
    linesToInject = {}  # {line_number : (indent, log_level, log_message)}

    for i, line in enumerate(lines, start=1):
        commentText = utils.extractComment(line)
        if not commentText:
            continue

        codeBeforeComment = line.split('#')[0].strip()  # check if there's actual code before the comment

        currFunc = lineToFunction.get(i)
        if currFunc not in decoratedFunctions:
            continue

        # for lines with code, check if it's a statement start (not continuation). Always allow comment-only lines
        if codeBeforeComment:
            if '@' in codeBeforeComment:  # it's a decorator line
                continue

            if i not in statementLines:  # does this line start a statement?
                continue

        logLevel, logMessage = parseComment(commentText, stopwords)
        if not logMessage:
            continue

        indentMatch = re.match(r'^(\s*)', line)
        indent = indentMatch.group(1) if indentMatch else ''

        linesToInject[i] = (indent, logLevel, logMessage)

    # Now build the output, injecting logging statements
    for i, line in enumerate(lines, start=1):

        # Add import if needed
        if not addedImports and not importsLogging:
            stripped = line.strip()
            starts = ("#", "'''", '"""')
            if i > 1 and stripped and not any(stripped.startswith(s) for s in starts):
                newLines.append('import logging')
                newLines.append('')
                addedImports = True

        if shouldSkipDecoratorLine(line, sourceCode):
            continue

        # Inject logging as needed
        if i in linesToInject:
            indent, logLevel, logMessage = linesToInject[i]
            logStatement = f'{indent}{loggerName}.{logLevel.lower()}("{logMessage}")'
            newLines.append(logStatement)

        newLines.append(line)

    with open(outfilepath, 'w') as outfile:
        outfile.write('\n'.join(newLines))


if __name__ == "__main__":
    print('starting')  # noqa T201

    args = getArgs()
    injectLogging(args.infilepath, args.outfilepath, args.stopwords)

    print('done')  # noqa T201
