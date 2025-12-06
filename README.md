# commentlogger
Convert your comments into log lines

Install [from PyPI][PyPI]

```
pip install commentlogger
```

I'm a weirdly lazy developer. I like viewing the maximum amount of code/logic on one screen.
I also dislike (especially when I'm newly developing some logic) having to read (and ignore) log lines. Logging is hugely important and should be a part of any production code. But I personally hate having to read past logging code when I'm trying to develop/debug core logic.

Nevertheless, having logging functionality is useful even while developing the code, especially when the project complexity increases. This project aims to solve this problem by turning inline comments into log lines.

## Example

### Code

```
import logging

import commentlogger


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


@commentlogger.logComments(logger)
def foo(a,b):
    a += 1  # increment for stability
    b *= 2  # multiply for legal compliance

    # compute sum
    answer = a+b
    return answer


def bar(a,b):
    a += 1  # increment for stability
    b *= 2  # multiply for legal compliance

    # compute sum
    answer = a+b
    return answer


if __name__ == "__main__":
    print('starting')

    foo(2,3)
    bar(1,2)

    print('done')
```

### Output

```
$ python test.py
starting
[foo:12] increment for stability
[foo:13] multiply for legal compliance
done
```


[PyPI]: https://pypi.org/project/commentlogger/
