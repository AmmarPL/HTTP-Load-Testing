import asyncio
import time

# Function to make constant rate requests
async def constant_rate_requests(tester, session):
    semaphore = asyncio.Semaphore(tester.concurrency)  # Control concurrency with a semaphore
    while time.time() < tester.end_time:
        loop_start = time.time()
        tasks = []
        for _ in range(tester.qps):
                # Acquire semaphore before creating a new task
                await semaphore.acquire()
                task = asyncio.create_task(tester.make_request(session))
                task.add_done_callback(lambda t: semaphore.release())  # Release when done
                tasks.append(task)
        
        # Wait for all tasks of this second to be scheduled
        await asyncio.gather(*tasks)
        
        # Calculate sleep to maintain constant rate
        elapsed = time.time() - loop_start
        sleep_time = max(0, 1 - elapsed)
        await asyncio.sleep(sleep_time)

#Function to make spike requests
async def spike_requests(tester, session):
    semaphore = asyncio.Semaphore(tester.concurrency)  # Control concurrency
    spike_duration = 10  # Duration of each spike in seconds
    rest_duration = 10  # Duration of rest between spikes
    qps_interval = 1.0 / tester.qps if tester.qps else float('inf')  # Calculate the interval between requests based on QPS
    
    while time.time() < tester.end_time:
        spike_end = time.time() + spike_duration
        while time.time() < spike_end and time.time() < tester.end_time:
            tasks = []
            start_time = time.time()

            while len(tasks) < tester.concurrency and time.time() - start_time < spike_duration:
                if time.time() - start_time >= qps_interval * len(tasks):
                    await semaphore.acquire()  # Manage concurrency
                    task = asyncio.create_task(tester.make_request(session))
                    task.add_done_callback(lambda t: semaphore.release())  # Ensure to release the semaphore
                    tasks.append(task)

            await asyncio.gather(*tasks)
        
        # Rest period
        await asyncio.sleep(rest_duration)

#Function to make ramping requests
async def ramp_requests(tester, session):
    semaphore = asyncio.Semaphore(tester.concurrency)  # Semaphore to control concurrency
    start_qps = 1
    end_qps = tester.qps
    current_qps = start_qps
    ramp_rate = (end_qps - start_qps) / tester.duration
    while time.time() < tester.end_time:
        loop_start = time.time()
        tasks = []
        for _ in range(int(current_qps)):
            await semaphore.acquire()  # Acquire semaphore before creating a task
            task = asyncio.create_task(tester.make_request(session))
            task.add_done_callback(lambda t: semaphore.release())  # Release semaphore when done
            tasks.append(task)
        await asyncio.gather(*tasks)
        current_qps += ramp_rate
        elapsed = time.time() - loop_start
        sleep_time = max(0, 1 - elapsed)
        await asyncio.sleep(sleep_time)
