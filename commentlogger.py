import inspect
import logging
import re
import sys
from functools import wraps


# ============================================================================
# DEVELOPMENT: Decorator with sys.settrace for debugging
# ============================================================================

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
                actual_line_num = start_line + i
                comment_lines[actual_line_num] = match.group(1).strip()

        func_code = func.__code__

        @wraps(func)
        def wrapper(*args, **kwargs):
            logged_lines = set()

            def traceLines(frame, event, arg):
                if frame.f_code is not func_code:
                    return None

                if event == 'call':
                    return traceLines

                if event == 'line':
                    line_num = frame.f_lineno

                    if line_num in comment_lines and line_num not in logged_lines:
                        myLogger.info(f"[{func.__name__}:{line_num}] {comment_lines[line_num]}")
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


logComments = log_comments = logcomments  # supporting whatever code style a dev might want
