import requests
import concurrent.futures

# Make sure backend is running on port 5555

API_BASE_URL = "http://localhost:5555/api"
START_SESSION_URL = f"{API_BASE_URL}/start_session"
QUERY_URL = f"{API_BASE_URL}/query"

# Example payload for start_session (should be customized to your backend's requirements)
START_SESSION_PAYLOAD = {
    "accessCode": "demo"  # Adjust this to match your backend's access codes
}

# Base payload for query (session_id will be updated for each client)
BASE_QUERY_PAYLOAD = {
    "logs": [],
    "suggestions": [],
    "example": "na",
    "n": 1,
    "max_tokens": 10,
    "temperature": 0.7,
    "top_p": 1.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "engine": "gpt-3.5-turbo-instruct",
    "stop": ["."],
    "doc": "This is a test document. We are requesting autocompletion suggestions for ",
}

BATCH_SIZES = [1, 5, 20, 50, 100]
# BATCH_SIZES = [1]


def get_session_id():
    """Get a unique session_id by calling start_session"""
    try:
        response = requests.post(START_SESSION_URL, json=START_SESSION_PAYLOAD)
        data = response.json()
        if data.get("status"):  # Assuming SUCCESS is True
            return data.get("session_id")
        else:
            print(f"Failed to start session: {data.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Exception starting session: {e}")
        return None


def send_query(session_id):
    """Send a query with the given session_id"""
    payload = BASE_QUERY_PAYLOAD.copy()
    payload["session_id"] = session_id

    try:
        response = requests.post(QUERY_URL, json=payload)
        data = response.json()
        openai_time = data.get("openai_time", None)
        return openai_time
    except Exception as e:
        print(f"Exception in query: {e}")
        return None


def run_batch(batch_size):
    print(f"\n--- Running batch of {batch_size} simultaneous calls ---")

    # First, get session_ids for all clients (sequentially)
    print(f"Getting {batch_size} session_ids...")
    session_ids = []
    for i in range(batch_size):
        session_id = get_session_id()
        if session_id:
            session_ids.append(session_id)
        else:
            print(f"Failed to get session_id {i + 1}")

    if not session_ids:
        print("No valid session_ids obtained. Cannot proceed with batch.")
        return

    # Now send queries simultaneously using the obtained session_ids
    print(f"Sending {len(session_ids)} simultaneous queries...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [executor.submit(send_query, session_id) for session_id in session_ids]
        openai_times = [future.result() for future in concurrent.futures.as_completed(futures)]
        openai_times = [t for t in openai_times if t is not None]
        if openai_times:
            avg_time = sum(openai_times) / len(openai_times)
            print(f"Average openai_time for batch size {batch_size}: {avg_time:.3f}s")
        else:
            print(f"WARNING: All calls failed or did not return openai_time for batch size {batch_size}.")


def main():
    for batch_size in BATCH_SIZES:
        run_batch(batch_size)


if __name__ == "__main__":
    main()
