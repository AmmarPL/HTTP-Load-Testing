import argparse
import asyncio
import aiohttp
import time
import json
from collections import defaultdict
from statistics import mean, median, stdev
import matplotlib.pyplot as plt
import io
import os
import glob
import numpy as np
from scipy.stats import gaussian_kde
from request_patterns import constant_rate_requests, spike_requests, ramp_requests


class HTTPLoadTestError(Exception):
    """
    Custom exception class for handling specific HTTP load test errors.
    """
    pass

class HTTPLoadTester:
    """
    Class to perform HTTP load testing. Simulates multiple HTTP requests to a given URL to measure
    the performance and reliability of the target server under various conditions.

    Attributes:
        url (str): URL to test.
        qps (int): Queries per second.
        concurrency (int): Number of concurrent requests.
        duration (int): Duration of the test in seconds.
        headers (dict): HTTP headers for requests.
        payload (dict): Payload for POST requests, if any.
        timeout (int): Timeout for each request.
        results (defaultdict): Stores response times categorized by HTTP status codes.
        errors (int): Number of request errors encountered during the test.
        total_requests (int): Total number of requests made during the test.
        latencies (list): List of latency times for each request.
        start_time (float): Start time of the test.
    """
    def __init__(self, config):
        self.url = config.get('url')  # URL to test.
        self.qps = config.get('qps', 10)  # Queries per second.
        self.concurrency = config.get('concurrency', 5)  # Number of concurrent requests.
        self.duration = config.get('duration', 60)  # Duration of the test in seconds.
        self.headers = config.get('headers', {})  # HTTP headers for requests.
        self.payload = config.get('payload', None)  # Payload for POST requests.
        self.timeout = config.get('timeout', 30)  # Timeout for each request.
        self.results = defaultdict(list)  # Store results by status code.
        self.errors = 0  # Count of errors during test.
        self.total_requests = 0  # Total number of requests made.
        self.latencies = []  # List of latency times.
        self.start_time = None  # Start time of the test.
        self.pattern_functions = {
            'constant': constant_rate_requests,
            'spike': spike_requests,
            'ramp': ramp_requests
        }
        self.pattern = config.get('pattern', 'constant')
        self.end_time = None
        self.request_times = []

    async def generate_requests(self, session):
        await self.pattern_functions[self.pattern](self, session)

    async def make_request(self, session):
        """
        Sends a single HTTP request using the given session and records its latency and outcome.
        
        Args:
            session (aiohttp.ClientSession): The session used to send the request.
            
        Raises:
            HTTPLoadTestError: If a timeout occurs during the request.
        """
        start_time = time.time()
        self.request_times.append(start_time - self.start_time)  # Record the time of the request
        try:
            if self.payload:
                # Send a POST request if a payload is present.
                async with session.post(self.url, json=self.payload, headers=self.headers, timeout=self.timeout) as response:
                    data = await response.json()  # Awaiting response data.
                    latency = time.time() - start_time
                    self.results[response.status].append(latency)
                    self.latencies.append((time.time() - self.start_time, latency))
                    # print("Received Data from Server: ", data)
            else:
                # Send a GET request if no payload is specified.
                async with session.get(self.url, headers=self.headers, timeout=self.timeout) as response:
                    await response.text()  # Awaiting response text.
                    latency = time.time() - start_time
                    self.results[response.status].append(latency)
                    self.latencies.append((time.time() - self.start_time, latency))
        except asyncio.TimeoutError:
            self.errors += 1
            raise HTTPLoadTestError(f"Request to {self.url} timed out.")
        except Exception as e:
            self.errors += 1
            print(f"Error: {str(e)}")
        finally:
            self.total_requests += 1

    async def run_test(self):
        """
        Manages the entire load test by orchestrating the sending of HTTP requests according
        to the specified configuration (QPS, concurrency, etc.), and timing their execution.
        """
        async with aiohttp.ClientSession() as session:
            self.start_time = time.time()
            self.end_time = self.start_time + self.duration
            await self.generate_requests(session)
        await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})

    def print_results(self):
        """
        Outputs the results of the load test, including the distribution of response statuses,
        error rate, and detailed latency statistics.
        """
        print("\nTest Results:")
        print(f"Total Requests: {self.total_requests}")
        print(f"Errors: {self.errors}")
        print(f"Error Rate: {self.errors / self.total_requests:.2%}")
        print(f"Actual QPS: {self.total_requests / self.duration:.2f}")

        all_latencies = [latency for latencies in self.results.values() for latency in latencies]
        if all_latencies:
            print(f"\nLatency Statistics (seconds):")
            print(f"  Min: {min(all_latencies):.4f}")
            print(f"  Max: {max(all_latencies):.4f}")
            print(f"  Mean: {mean(all_latencies):.4f}")
            print(f"  Median: {median(all_latencies):.4f}")
            print(f"  P90: {sorted(all_latencies)[int(len(all_latencies)*0.9)]:.4f}")
            print(f"  P95: {sorted(all_latencies)[int(len(all_latencies)*0.95)]:.4f}")
            print(f"  P99: {sorted(all_latencies)[int(len(all_latencies)*0.99)]:.4f}")
            print(f"  Std Dev: {stdev(all_latencies):.4f}")

        print("\nStatus Code Distribution:")
        for status, latencies in self.results.items():
            print(f"  {status}: {len(latencies)}")

        self.plot_latencies()
        self.plot_request_pattern()

    def plot_latencies(self):
        """
        Generates and saves a plot of latencies over time to a PNG file. Each plot file is
        uniquely named based on the number of existing files in the 'Latency_Plots' directory.
        """
        times, latencies = zip(*self.latencies)
        plt.figure(figsize=(10, 5))
        plt.plot(times, latencies)
        plt.title('Latency over time')
        plt.xlabel('Time (s)')
        plt.ylabel('Latency (s)')
        plt.grid(True)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        file_number = len(glob.glob('/app/Latency_Plots/*'))
        print("\nLatency plot saved as '/app/Latency_Plots/latency_plot" + str(file_number) + ".png'")
        with open('/app/Latency_Plots/latency_plot' + str(file_number) + '.png', 'wb') as f:
            f.write(buf.getvalue())

    def plot_request_pattern(self):
        """
        Generates and saves a plot of the request pattern over time to a PNG file.
        Each plot file is uniquely named based on the number of existing files in the 'Pattern_Plots' directory.
        """
        plt.figure(figsize=(10, 5))
        
        # Calculate the density using a Gaussian Kernel Density Estimation
        density = gaussian_kde(self.request_times)
        xs = np.linspace(0, self.duration, 200)  # 200 points for smoothness
        density.covariance_factor = lambda : .25  # Smaller bandwidth for more detail
        density._compute_covariance()
        
        plt.plot(xs, density(xs), label='Request Density')
        plt.title(f'Request Pattern over Time ({self.pattern})')
        plt.xlabel('Time (s)')
        plt.ylabel('Density')
        plt.grid(True)
        plt.legend()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        file_number = len(glob.glob('/app/Pattern_Plots/*'))
        print(f"\nRequest pattern plot saved as '/app/Pattern_Plots/pattern_plot{file_number}.png'")
        with open(f'/app/Pattern_Plots/pattern_plot{file_number}.png', 'wb') as f:
            f.write(buf.getvalue())
def main():
    """Parses command-line arguments and runs the load test."""
    parser = argparse.ArgumentParser(description="HTTP Load Tester")
    parser.add_argument("url", help="URL to load test")
    parser.add_argument("--qps", type=int, default=10, help="Queries per second")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--headers", type=json.loads, default="{}", help="Headers as JSON string")
    parser.add_argument("--payload", type=json.loads, help="POST request payload as JSON string")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--pattern", type=str, default="constant", choices=["constant", "spike", "ramp"],
                    help="Request pattern: constant, spike, or ramp")
    args = parser.parse_args()
    os.makedirs("/app/Latency_Plots", exist_ok=True)
    os.makedirs("/app/Pattern_Plots", exist_ok=True)

    config = {
        'url': args.url,
        'qps': args.qps,
        'concurrency': args.concurrency,
        'duration': args.duration,
        'headers': args.headers,
        'payload': args.payload,
        'timeout': args.timeout,
        'pattern': args.pattern
    }

    load_tester = HTTPLoadTester(config)
    asyncio.run(load_tester.run_test())
    load_tester.print_results()

if __name__ == "__main__":
    main()
