import inspect
import logging
import re
import sys
from functools import wraps


LOGLEVELS = sorted(logging._nameToLevel.keys())


def logcomments(myLogger):
    def decoDebug(func):
        """Development decorator that traces comment execution."""
        source = inspect.getsource(func)
        source_lines = source.split('\n')
        start_line = inspect.getsourcelines(func)[1]

        comment_lines = {}
        for i, line in enumerate(source_lines):
            match = re.search(r'#\s*(.*)', line)
            if match:
                comment_lines[start_line + i] = match.group(1).strip()

        func_code = func.__code__
        func_filename = func_code.co_filename

        @wraps(func)
        def wrapper(*args, **kwargs):
            logged_lines = set()

            def traceLines(frame, event, _arg):
                if frame.f_code is not func_code:
                    return None

                if event == 'call':
                    return traceLines

                if event == 'line':
                    line_num = frame.f_lineno

                    if line_num in comment_lines and line_num not in logged_lines:
                        comment = comment_lines[line_num]
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

                        comment_lines[line_num] = logline

                        if myLogger.isEnabledFor(getattr(logging, level.upper())):
                            record = myLogger.makeRecord(myLogger.name,
                                                         getattr(logging, level),
                                                         func_filename,  # filename of the logging function
                                                         line_num,
                                                         comment_lines[line_num],
                                                         args = (),
                                                         exc_info = None,
                                                         func = func.__name__,  # name of the logging function
                                                         extra = None,
                                                         sinfo = None,
                                                         )
                            myLogger.handle(record)
                            logged_lines.add(line_num)

                return traceLines

            old_trace = sys.gettrace()
            sys.settrace(traceLines)

            try:
                result = func(*args, **kwargs)
            finally:
                sys.settrace(old_trace)

            return result

        return wrapper
    return decoDebug


logComments = log_comments = logcomments  # supporting whatever code style a dev might want  # noqa N816
