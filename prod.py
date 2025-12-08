import argparse
import ast
import logging
import re

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

    with open(infilepath, 'r') as f:
        sourceCode = f.read()

    detectedLogger, decoratedFunctions = extractLoggerInfo(sourceCode)

    if detectedLogger:
        loggerName = detectedLogger
    else:
        loggerName = "logger"

    lines = sourceCode.splitlines()
    newLines = []

    importsLogging = 'import logging' in sourceCode
    addedImports = False

    try:
        tree = ast.parse(sourceCode)
        lineToFunction = {}

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for i in range(node.lineno, node.end_lineno + 1 if node.end_lineno else node.lineno + 1):
                    lineToFunction[i] = node.name
    except Exception:
        lineToFunction = {}

    for i, line in enumerate(lines):

        if not addedImports and not importsLogging:
            stripped = line.strip()
            starts = ("#", "'''", '"""')
            if i and stripped and not any(stripped.startswith(s) for s in starts):
                newLines.append('import logging')
                newLines.append('')
                addedImports = True

        if shouldSkipDecoratorLine(line, sourceCode):
            continue

        commentMatch = re.search(r'#\s*(.*)', line)

        if commentMatch:
            commentText = commentMatch.group(1).strip()
            indentTatch = re.match(r'^(\s*)', line)
            indent = indentTatch.group(1) if indentTatch else ''

            preCommentCode = line.split('#')[0].strip()
            currFunc = lineToFunction.get(i + 1)

            if (preCommentCode and currFunc in decoratedFunctions and '@' not in preCommentCode):
                logLevel, logMessage = parseComment(commentText, stopwords)  # Parse comment to extract log level and message
                if not logMessage:
                    continue

                logStatement = f'{indent}{loggerName}.{logLevel.lower()}("{logMessage}")'
                newLines.append(logStatement)

        newLines.append(line)

    with open(outfilepath, 'w') as f:
        f.write('\n'.join(newLines))


if __name__ == "__main__":
    print('starting')  # noqa T201

    args = getArgs()
    injectLogging(args.infilepath, args.outfilepath, args.stopwords)

    print('done')  # noqa T201
