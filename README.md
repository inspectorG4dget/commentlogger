# commentlogger

**Convert your inline comments into log lines during development**

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
```bash
pip install commentlogger
```

## The Problem

> My motivation is highly opinionated. If you have similar pain points, this project may be for you :)

As developers, we face a dilemma:

- **During development**: We want clean, readable code without log statements cluttering our logic
- **In production**: We need comprehensive logging to debug issues

Writing logging statements while developing can make code harder to read and understand. But we still want to trace execution flow during debugging.

**commentlogger** solves this by letting you write natural inline comments during development, then automatically logging them as your code executes.

## Features

- 🎯 **Zero code clutter** - Your comments become your logs
- 🔍 **Line-by-line execution tracing** - See exactly what's running and when
- 🎨 **Flexible logger support** - Use your own logger or the default
- 📊 **Log level support** - Specify log levels directly in comments (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- 🚫 Stopword filtering - Comments starting with certain user-specified keywords (like TODO, FIXME, NOTE, HACK, XXX, BUG) are automatically skipped and won't be logged
- 🚀 **Development-focused** - Designed for debugging, not production (see Performance note)
- 📝 **Clean syntax** - Simple decorator, nothing more
- 🔄 **Production converter** - Tool to convert development code to production-ready logging

## Quick Start

```python
import logging
from commentlogger import logcomments

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

@logcomments(logger)
def foo(a, b):
    a += 1  # increment for stability
    b *= 2  # multiply for legal compliance
    
    # compute sum
    answer = a + b
    return answer

def bar(a, b):
    a += 1  # increment for stability
    b *= 2  # multiply for legal compliance
    
    # compute sum
    answer = a + b
    return answer

if __name__ == "__main__":
    print('starting')
    
    foo(2, 3)  # Comments are logged
    bar(1, 2)  # No decorator, no logging
    
    print('done')
```

**Output:**
```
starting
[foo:12] increment for stability
[foo:13] multiply for legal compliance
[foo:16] compute sum
done
```

Notice that `bar()` doesn't produce any log output because it's not decorated.

## Usage

### Basic Usage
```python
from commentlogger import logcomments

@logcomments()  # Uses default logger
def my_function():
    # This comment will be logged
    x = 1
    return x
```

### Custom Logger
```python
import logging
from commentlogger import logcomments

# Create your custom logger
logger = logging.getLogger('myapp')
logger.setLevel(logging.DEBUG)

@logcomments(logger)
def my_function():
    # This uses your custom logger
    x = 1
    return x
```

### Log Levels in Comments

You can specify log levels directly in your comments using the format `# LEVEL: message`:

```python
import logging
from commentlogger import logcomments

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@logcomments(logger)
def process_transaction(amount):
    # DEBUG: Starting transaction processing
    validated = validate_amount(amount)
    
    # INFO: Transaction validated successfully
    result = apply_transaction(validated)
    
    # WARNING: High value transaction detected
    if result > 10000:
        alert_compliance()
    
    # ERROR: Transaction amount is negative
    if result < 0:
        rollback()
        
    # This is a regular info message (no level specified)
    return result
```

**Output:**
```
DEBUG: Starting transaction processing
INFO: Transaction validated successfully
WARNING: High value transaction detected
INFO: This is a regular info message
```

### Stopword Filtering
You can specify stopwords to prevent certain comments from being logged:
```python
import logging
from commentlogger import logcomments

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

@logcomments(logger, stopwords=['TODO', 'FIXME', 'NOTE'])
def process_data(data):
    # TODO: optimize this algorithm later
    validated = validate(data)
    
    # Processing data now
    result = transform(validated)
    
    # FIXME: handle edge case for empty lists
    if result:
        return result[0]
    
    # NOTE: this is a temporary workaround
    return None
```

Only comments that don't start with a stopword prefix is logged. Comments starting with TODO, FIXME, or NOTE are silently skipped.

**Supported log levels:**  
These are the default log levels in python's logging module.
If you'd like additional/custom log levels, ensure you add them before you pass the logger to the `logcomments` decorator
- `DEBUG` (or `D`, `DEB`, `DEBU`, `debu`)
- `INFO` (or `I`, `INF`, `inf`)
- `WARNING` (or `W`, `WARN`, `WA`, `wa`)
- `ERROR` (or `E`, `ERR`, `ER`, `er`)
- `CRITICAL` (or `C`, `CRIT`, `CRI`, `cri`)

**Shorthand matching:**
- Comments are case-insensitive for level matching
- Prefix matches work: `# warn: message` → `WARNING` level
- If multiple levels share a prefix, the lexicographically first is used
- If no level is specified or recognized, defaults to `INFO`

### Multiple Naming Styles

The package supports different naming conventions:
```python
from commentlogger import logcomments
from commentlogger import logComments  # camelCase
from commentlogger import log_comments # snake_case alternative

# All three work identically
@logcomments(logger)
@logComments(logger)
@log_comments(logger)
```

## How It Works

commentlogger uses Python's `sys.settrace()` mechanism to intercept line-by-line execution. When a decorated function runs:

1. The decorator extracts all comments from the function's source code
2. As each line executes, it checks if that line has a comment
3. If a comment exists, it parses the log level (if specified) and message
4. It logs the message at the appropriate level before executing the line
5. Execution continues normally

**Log level parsing:**
- Format: `# LEVEL: message` (e.g., `# DEBUG: Entering function`)
- If no level is specified (e.g., `# message`), defaults to `INFO`
- Supports shorthand: `# W: message` matches `WARNING`
- Case-insensitive matching

## Performance Considerations

⚠️ **Important**: commentlogger uses `sys.settrace()` which has **significant performance overhead** (10-30x slower).

**Recommended usage:**
- ✅ Development and debugging
- ✅ Local testing
- ✅ Understanding complex logic flow
- ❌ Production environments
- ❌ Performance-critical code
- ❌ Automated test suites

## Transition to Production

When you're ready to move to production, you have several options:

### 1. Remove the decorator (simplest)
Just remove `@logcomments(logger)` from your functions.

### 2. Convert to explicit logging (recommended)

Use the included `inject_logging.py` tool to automatically convert your commented code to production-ready logging:

```bash
python -m commentlogger.prod -i mycode.py -o mycode_production.py -s FIXME DEBUG
```

**Input code:**
```python
import logging

from commentlogger import logcomments

logger = logging.getLogger(__name__)

@logcomments(logger)
def process_data(x):
    x = validate(x)  # DEBUG: Starting data processing
    result = transform(x)  # INFO: Data validated
    
    if len(result) > 1000:  # WARNING: Large dataset detected
        optimize()
    
    return result
```

**Output code:**
```python
import logging

logger = logging.getLogger(__name__)

def process_data(x):
    logger.debug("Starting data processing")
    x = validate(x)  # DEBUG: Starting data processing
    
    logger.info("Data validated")
    result = transform(x)  # INFO: Data validated
    
    logger.warning("Large dataset detected")
    if len(result) > 1000:  # WARNING: Large dataset detected
        optimize()
    
    return result
```

The tool:
- Automatically detects your logger variable name from the decorator
- Preserves log levels from comments
- Removes the `@logcomments` decorator
- Only processes decorated functions
- Works with any import alias (e.g., `from commentlogger import logcomments as trace`)

## Philosophy

This tool embodies a simple idea: **during development, your comments already describe what your code does**. Why write them twice - once as comments and again as log statements?

commentlogger lets you:
- Write cleaner development code
- Maintain readability
- Debug with detailed execution traces
- Specify appropriate log levels inline
- Transition to production logging when ready

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Author

Created with ❤️ for developers who value clean, readable code.

## See Also

- [Python logging documentation](https://docs.python.org/3/library/logging.html)
- [sys.settrace() documentation](https://docs.python.org/3/library/sys.html#sys.settrace)

---

**Note**: Remember that commentlogger is a development tool. For production logging, use explicit `logger` calls or generate them programmatically from your development code using the included conversion tool.
