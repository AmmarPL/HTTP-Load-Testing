import pytest
import asyncio
from load_tester import HTTPLoadTester  # Import the custom load tester class.

def test_initialization():
    """
    Test the initialization of HTTPLoadTester with basic configuration.
    This test verifies that the HTTPLoadTester class correctly initializes with given configuration settings.
    """
    config = {
        'url': 'https://test.k6.io/contacts.php',  # URL to be tested.
        'qps': 10,  # Queries per second.
        'concurrency': 5,  # Number of concurrent requests.
        'duration': 60,  # Duration of the test in seconds.
        'timeout': 30  # Timeout for each request in seconds.
    }
    tester = HTTPLoadTester(config)  # Creating an instance of HTTPLoadTester with the specified config.
    # Assertions to check if the instance variables are initialized correctly.
    assert tester.url == 'https://test.k6.io/contacts.php'
    assert tester.qps == 10
    assert tester.concurrency == 5
    assert tester.duration == 60
    assert tester.timeout == 30

def test_get_request_handling():
    """
    Test how HTTPLoadTester handles a basic GET request.
    This function tests the ability of the load tester to handle a GET request and collect the necessary data.
    """
    config = {
        'url': 'http://httpbin.org/get',  # Public API that echoes the GET request.
        'qps': 1,
        'concurrency': 1,
        'duration': 1
    }
    tester = HTTPLoadTester(config)  # Initialize the tester with a simple GET request config.
    asyncio.run(tester.run_test())  # Execute the load test asynchronously.
    # Assertions to verify the correct execution and data collection.
    assert len(tester.latencies) > 0, "Should record at least one latency"
    assert tester.total_requests == 1, "Should have made exactly one request"
    assert tester.errors == 0, "Should have no errors"

@pytest.mark.asyncio
async def test_post_request_handling():
    """
    Test how HTTPLoadTester handles a basic POST request.
    This function tests the load tester's capability to handle POST requests and check the integrity of echoed data.
    """
    config = {
        'url': 'https://httpbin.org/post',  # Public API that echoes the POST request data.
        'qps': 1,
        'concurrency': 1,
        'duration': 1,
        'headers': {'Content-Type': 'application/json'},  # Headers specifying JSON content type.
        'payload': {"key": "value"},  # JSON payload to be sent.
        'timeout': 10
    }
    tester = HTTPLoadTester(config)  # Setup the load tester for a POST request.
    await tester.run_test()  # Run the test asynchronously.
    # Assertions to ensure the request was handled correctly and data was recorded.
    assert len(tester.latencies) == 1, "Should record exactly one latency"
    assert tester.total_requests == 1, "Should have made exactly one request"
    assert tester.errors == 0, "Should have no errors"
