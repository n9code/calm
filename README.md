# Calm

<a href="http://calm.n9co.de/">
    <img src="https://raw.githubusercontent.com/n9code/calm/master/docs/logo/calm-logo.png"
         alt="Calm Logo"
         align="right"
         width=70
         height=70 />
</a>
[![PyPI](https://img.shields.io/pypi/v/calm.svg)](https://pypi.python.org/pypi/calm)
[![Build Status](https://travis-ci.org/n9code/calm.svg?branch=master)](https://travis-ci.org/n9code/calm)
[![Coverage Status](https://coveralls.io/repos/github/n9code/calm/badge.svg?branch=master)](https://coveralls.io/github/n9code/calm?branch=master)
[![Code Health](https://landscape.io/github/n9code/calm/master/landscape.svg?style=flat)](https://landscape.io/github/n9code/calm/master)
[![Gitter](https://badges.gitter.im/n9code/calm.svg)](https://gitter.im/n9code/calm?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/n9code/calm/master/LICENSE)

## Introduction

Calm is an extension to Tornado Framework that provides decorators and other
tools to easily implement RESTful APIs. The purpose of Calm is to ease the
process of defining your API, parsing argument values in the request handlers,
etc.

### Installation

Calm installation process is dead simple with `pip`:

```
$ pip install calm
```

*Note: Calm works only with Python 3.5*

## Let's code!

Here is a basic usage example of Calm:

```python
import tornado.ioloop
from calm import Application


app = Application()


@app.get('/hello/:your_name')
async def hello_world(request, your_name):
    return {'hello': your_name}


tornado_app = app.make_app()
tornado_app.listen(8888)
tornado.ioloop.IOLoop.current().start()
```

Now go ahead and try your new application! Navigate to
`http://localhost:8888/hello/YOUR_NAME_HERE` and see what you get.

Now that you built your first Calm RESTful API, let us dive deeper and see more
features of Calm. Go ahead and add the following code to your first application.

```python
# Calm has the notion of a Service. A Service is nothing more than a URL prefix for
# a group of endpoints.
my_service = app.service('/my_service')


# So when usually you would define your handler with `@app.get`
# (or `post`, `put`, `delete`), with Service you use the same named methods of
# the Service instance
@my_service.post('/body_demo')
async def body_demo(request):
    """
    The request body is automatically parsed to a dict.

    If the request body is not a valid JSON, `400` HTTP error is returned.

    When the handler returns not a `dict` object, the return value is nested
    into a JSON, e.g.:

        {"result": YOUR_RETURN_VALUE}

    """
    return request.body['key']


@my_service.get('/args_demo/:number')
async def args_demo(request, number: int, arg1: int, arg2='arg2_default'):
    """
    You can specify types for your request arguments.

    When specified, Calm will parse the arguments to the appropriate type. When
    there is an error parsing the value, `400` HTTP error is returned.

    Any function parameters that do not appear as path arguments, are
    considered query arguments. If a default value is assigned for a query
    argument it is considered optional. And finally if not all required query
    arguments are passed, `400` HTTP error is returned.
    """
    return {
        'type(number)': str(type(number)),
        'type(arg1)': str(type(arg1)),
        'arg2': arg2
    }
```

If you followed the comments in the example, then we are ready to play with it!

First let us see how Calm treats request and response bodies:

```
$ curl -X POST --data '{"key": "value"}' 'localhost:8888/my_service/body_demo'
{"result": "value"}

$ curl -X POST --data '{"another_key": "value"}' 'localhost:8888/my_service/body_demo'
{"error": "Oops our bad. We are working to fix this!"}

$ curl -X POST --data 'This is not JSON' 'localhost:8888/my_service/body_demo'
{"error": "Malformed request body. JSON is expected."}
```

Now it's time to observe some request argument magic!

```
$ curl 'localhost:8888/my_service/args_demo/0'
{"error": "Missing required query param 'arg1'"}

$ curl 'localhost:8888/my_service/args_demo/0?arg1=12'
{"type(arg1)": "<class 'int'>", "type(number)": "<class 'int'>", "arg2": "arg2_default"}

$ curl 'localhost:8888/my_service/args_demo/0?arg1=not_a_number'
{"error": "Bad value for integer: not_a_number"}

$ curl 'localhost:8888/my_service/args_demo/0?arg1=12&arg2=hello'
{"type(arg1)": "<class 'int'>", "type(number)": "<class 'int'>", "arg2": "hello"}
```

## Contributions

Calm loves Pull Requests and welcomes any contribution be it an issue,
documentation or code. A good start for a contribution can be reviewing existing
open issues and trying to fix one of them.

If you find nothing to work on but cannot kill the urge, jump into the [gitter
channel](https://gitter.im/n9code/calm) and ask "what can I do?".
