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
- 🚀 **Development-focused** - Designed for debugging, not production (see Performance note)
- 📝 **Clean syntax** - Simple decorator, nothing more

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
1. As each line executes, it checks if that line has a comment
1. If a comment exists, it logs the comment text before executing the line
1. If the comment specifies a log level, use that loglevel  
   Eg: `# warning: [message]` will log `message` as a warning. This will work only if `setLevel` allows for warnings to be emitted.  
   Shorthand also works: `# w: [message]` or `# warn: [message]` or `# wa: [message]` will behave identically.  
   Caveat: if two loglevels share a shorthand/prefix, the lexicographically first level will be used.
1. Execution continues normally

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

When you're ready to move to production, you have the following options:

1. **Remove the decorator** - Simplest approach
1. **Convert to explicit logging** - Replace comments with `logger.info()` statements

## Philosophy

This tool embodies a simple idea: **during development, your comments already describe what your code does**. Why write them twice - once as comments and again as log statements?

commentlogger lets you:
- Write cleaner development code
- Maintain readability
- Debug with detailed execution traces
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

**Note**: Remember that commentlogger is a development tool. For production logging, use explicit `logger` calls or generate them programmatically from your development code.
