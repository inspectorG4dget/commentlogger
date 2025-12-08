import inspect
import logging
import re
import sys
from functools import wraps


LOGLEVELS = {**logging._nameToLevel}

for k, v in logging._nameToLevel.items():
    if any(_k.startswith(k) and v==_v for _k, _v in logging._nameToLevel.items() if k != _k):  # noqa E225
        LOGLEVELS.pop(k)

LOGLEVELS = sorted(LOGLEVELS.keys())


def logcomments(myLogger, stopwords=None):
    if stopwords is None:
        stopwords = []

    def decoDebug(func):
        """Development decorator that traces comment execution."""
        source = inspect.getsource(func)
        sourceLines = source.split('\n')
        startLine = inspect.getsourcelines(func)[1]

        commentLines = {}
        for i, line in enumerate(sourceLines):
            match = re.search(r'#\s*(.*)', line)
            if match:
                commentLines[startLine + i] = match.group(1).strip()

        funcCode = func.__code__
        funcFilename = funcCode.co_filename

        @wraps(func)
        def wrapper(*args, **kwargs):
            loggedLines = set()

            def traceLines(frame, event, _arg):
                if frame.f_code is not funcCode:
                    return None

                if event == 'call':
                    return traceLines

                if event != 'line':
                    return traceLines

                lineNum = frame.f_lineno

                if lineNum in commentLines and lineNum not in loggedLines:
                    comment = commentLines[lineNum]
                    level, _, logline = comment.partition(":")
                    level = level.strip()
                    logline = logline.strip()

                    if not level:
                        level = "info"
                        logline = comment

                    else:
                        try:
                            level = next(L for L in LOGLEVELS if L.startswith(level.upper()))
                        except StopIteration:
                            level = "INFO"
                            logline = comment

                    if not any(logline.startswith(stopword) for stopword in stopwords):
                        commentLines[lineNum] = logline

                        if myLogger.isEnabledFor(getattr(logging, level.upper())):
                            record = myLogger.makeRecord(myLogger.name,
                                                         getattr(logging, level),
                                                         funcFilename,  # filename of the logging function
                                                         lineNum,
                                                         commentLines[lineNum],
                                                         args = (),
                                                         exc_info = None,
                                                         func = func.__name__,  # name of the logging function
                                                         extra = None,
                                                         sinfo = None,
                                                         )
                            myLogger.handle(record)
                            loggedLines.add(lineNum)

                return traceLines

            oldTrace = sys.gettrace()
            sys.settrace(traceLines)

            try:
                result = func(*args, **kwargs)
            finally:
                sys.settrace(oldTrace)

            return result

        return wrapper
    return decoDebug


logComments = log_comments = logcomments  # supporting whatever code style a dev might want  # noqa N816
