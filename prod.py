import ast
import logging
import re

# Get all available log levels
LOGLEVELS = {**logging._nameToLevel}

for k,v in logging._nameToLevel.items():
    if any(_k.startswith(k) and v==_v for _k,_v in logging._nameToLevel.items() if k != _k):
        LOGLEVELS.pop(k)

LOGLEVELS = sorted(LOGLEVELS.keys())


def parseComment(comment):
    """
    Parse a comment to extract log level and message.

    Args:
        comment: The comment text to parse

    Returns:
        A tuple of (logLevel, logMessage)
    """
    level, _, logline = comment.partition(":")
    level = level.strip()
    logline = logline.strip()

    if not level:
        level = "INFO"
        logline = comment
    else:
        try:
            level = next(L for L in LOGLEVELS if L.startswith(level.upper()))
            print(f"Discovered {level = }")  ##
        except StopIteration:
            level = "INFO"
            logline = comment

    return level, logline


def shouldSkipDecoratorLine(line, sourceCode):
    """
    Determine if a decorator line should be skipped based on whether it's
    a commentlogger import (name-agnostic).

    Args:
        line: The line of code to check
        sourceCode: The full source code (needed to parse imports)

    Returns:
        True if this decorator should be skipped, False otherwise
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
    except:
        pass

    return False


def extractLoggerInfo(sourceCode):
    """
    Extract logger name and decorated functions using AST (name-agnostic).

    Args:
        sourceCode: The Python source code to analyze

    Returns:
        A tuple of (loggerName, decoratedFunctions)
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

                        if decoratorName and (
                                decoratorName in clNames or
                                decoratorName.split('.')[0] in clNames
                        ):
                            if decorator.args and len(decorator.args) > 0:
                                arg = decorator.args[0]
                                if isinstance(arg, ast.Name):
                                    loggerName = arg.id
                                    decoratedFunctions.add(node.name)

        return loggerName, decoratedFunctions
    except Exception as e:
        print(f"⚠ Warning: Could not parse AST: {e}")
        return None, set()


def injectLogging(infilepath, outfilepath):
    """
    Inject logging statements before lines with comments in a Python file.

    Args:
        infilepath: Path to the input Python file
        outfilepath: Path to the output file. If None, prints to stdout.

    Returns:
        The modified source code with logging injected
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
    except:
        lineToFunction = {}

    i = 0
    while i < len(lines):
        line = lines[i]

        if not addedImports and not importsLogging:
            stripped = line.strip()
            if (not stripped.startswith('#') and
                    not stripped.startswith('"""') and
                    not stripped.startswith("'''") and
                    stripped != '' and
                    i > 0):
                newLines.append('import logging')
                newLines.append('')
                addedImports = True

        if shouldSkipDecoratorLine(line, sourceCode):
            i += 1
            continue

        commentMatch = re.search(r'#\s*(.*)', line)

        if commentMatch:
            commentText = commentMatch.group(1).strip()
            indentTatch = re.match(r'^(\s*)', line)
            indent = indentTatch.group(1) if indentTatch else ''

            preCommentCode = line.split('#')[0].strip()
            currFunc = lineToFunction.get(i + 1)

            if (preCommentCode and currFunc in decoratedFunctions and '@' not in preCommentCode):
                logLevel, logMessage = parseComment(commentText)  # Parse comment to extract log level and message

                logStatement = f'{indent}{loggerName}.{logLevel.lower()}("{logMessage}")'
                newLines.append(logStatement)

        newLines.append(line)
        i += 1

    result = '\n'.join(newLines)

    if outfilepath:
        with open(outfilepath, 'w') as f:
            f.write(result)
        print(f"✓ Logging injected successfully!")
        print(f"  Input:  {infilepath}")
        print(f"  Output: {outfilepath}")
        if decoratedFunctions:
            print(f"  Processed functions: {', '.join(sorted(decoratedFunctions))}")
    else:
        print(result)

    return result


if __name__ == "__main__":
    injectLogging('test.py', 'test_output.py')
