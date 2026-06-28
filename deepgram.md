---
title: Getting Started with Flux
subtitle: >-
  Flux is the first conversational speech recognition model built specifically
  for voice agents. Unlike traditional STT that just transcribes words, Flux
  understands conversational flow and automatically handles turn-taking.
slug: docs/flux/quickstart
---

<Card
    href="https://playground.deepgram.com/?endpoint=listen-turn-taking&model=flux-general-en"
>
  <div class="t-default text-base font-semibold">Deepgram API Playground</div>
  Try this feature out in our API Playground.
</Card>

Flux tackles the most critical challenges for voice agents today: knowing when to listen, when to think, and when to speak. The model features first-of-its-kind model-integrated end-of-turn detection, configurable turn-taking dynamics, and ultra-low latency optimized for voice agent pipelines, all with Nova-3 level accuracy.

**Flux is Perfect for:** turn-based voice agents, customer service bots, phone assistants, and real-time conversation tools.

<Info>
**Multilingual support:** Flux Multilingual (`flux-general-multi`) extends Flux to 10 languages with optional `language_hint` biasing. See the [Language Prompting guide](/docs/flux/language-prompting) for details.
</Info>

**Key Benefits:**

- **Smart turn detection** — Knows when speakers finish talking
- **Ultra-low latency** — ~260ms end-of-turn detection
- **Early LLM responses** — `EagerEndOfTurn` events for faster replies
- **Turn-based transcripts** — Clean conversation structure
- **Natural interruptions** — Built-in barge-in handling
- **Nova-3 accuracy** — Best-in-class transcription quality

<Info>
For more information on how Flux manages turns, see the [Flux State Machine Guide](/docs/flux/state) guide.
</Info>

## Important: Flux Connection Requirements

<Warning>
**Flux requires the `/v2/listen` endpoint** — Using `/v1/listen` will not work with Flux.
</Warning>

When connecting to Flux, you must use:
- **Endpoint:** `/v2/listen` (not `/v1/listen`)
- **Model:** `flux-general-en` for English or `flux-general-multi` for multilingual workloads
- **Audio Format:** See [Audio Format Requirements](#audio-format-requirements) table below
- **Chunk Size:** **80ms audio chunks strongly recommended** for optimal model performance and latency

### Audio Format Requirements

| Audio Type | Encoding | Container | `encoding` param | `sample_rate` param | Supported Sample Rates |
|------------|----------|-----------|------------------|---------------------|------------------------|
| Raw | `linear16`, `linear32`, `mulaw`, `alaw`, `opus`, `ogg-opus` | None | **Required** | **Required** (`16000` recommended) | `8000`, `16000`, `24000`, `44100`, `48000` |
| Containerized | `linear16` | WAV | **Omit** | **Omit** | Auto-detected from container |
| Containerized | `opus` | Ogg | **Omit** | **Omit** | Auto-detected from container |
| Containerized | `opus` | WebM | **Omit** | **Omit** | Auto-detected from container |

**WebSocket URL Format:**
```
wss://api.deepgram.com/v2/listen?model=flux-general-en

wss://api.deepgram.com/v2/listen?model=flux-general-multi&language_hint=en&language_hint=es
```

When using the Deepgram SDK, use `client.listen.v2.connect()` to access the v2 endpoint. For direct WebSocket connections, ensure you're using `/v2/listen` in your URL.

## Configurable Parameters

Flux provides three key parameters to control end-of-turn detection behavior and optimize your voice agent's conversational flow:

### End-of-Turn Detection Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `eot_threshold` | `0.5` - `0.9` | `0.7` | Confidence required to trigger an `EndOfTurn` event. Higher values = more reliable turn detection but slightly increased latency. |
| `eager_eot_threshold` | `0.3` - `0.9` | *None* | Confidence required to trigger an `EagerEndOfTurn` event. **Required** to enable early response generation. Lower values = earlier triggers but more false starts. |
| `eot_timeout_ms` | `500` - `10000` | `5000` | Maximum milliseconds of silence before forcing an `EndOfTurn`, regardless of confidence. |

### When to Configure These Parameters

**For most use cases**, the default `eot_threshold=0.7` works well. You only need to configure these parameters if:

- **You want faster responses**: Set `eager_eot_threshold` to enable `EagerEndOfTurn` events and start LLM processing before the user fully finishes speaking
- **Your users speak with long pauses**: Increase `eot_timeout_ms` to avoid cutting off turns prematurely
- **You need more reliable turn detection**: Increase `eot_threshold` to reduce false positives (at the cost of slightly higher latency)
- **You want more aggressive turn detection**: Lower `eot_threshold` to trigger turns earlier

<Info>
**Important**: Setting `eager_eot_threshold` enables `EagerEndOfTurn` and `TurnResumed` events. These events allow you to start preparing LLM responses early, reducing end-to-end latency by hundreds of milliseconds. See the [Eager End-of-Turn Optimization Guide](/docs/flux/voice-agent-eager-eot) for implementation strategies.
</Info>

<Warning>
**Cost Consideration**: Using `EagerEndOfTurn` can increase LLM API calls by 50-70% due to speculative response generation. The `TurnResumed` event signals when to cancel a draft response because the user continued speaking.
</Warning>

For comprehensive parameter documentation and tuning guidance, see the [End-of-Turn Configuration](/docs/flux/configuration).

<Info>
**Dynamic Configuration**: You can update these parameters mid-stream using the [Configure control message](/docs/flux/configure) without disconnecting and reconnecting. This is useful for adapting to changing conversation context or user behavior.
</Info>

## Using Flux: SDK vs Direct WebSocket

<CodeGroup>
```python SDK (Recommended)
from deepgram import AsyncDeepgramClient

client = AsyncDeepgramClient()

# SDK automatically uses /v2/listen endpoint
async with client.listen.v2.connect(
    model="flux-general-multi",
    encoding="linear16",
    sample_rate=16000,
    request_options={
        "additional_query_parameters": {
            "language_hint": ["en", "es"],
        }
    },
) as connection:
    # Your code here
    pass
```

```bash Direct WebSocket
# Example using wscat for testing
wscat -H "Authorization: Token YOUR_DEEPGRAM_API_KEY" \
  -c "wss://api.deepgram.com/v2/listen?model=flux-general-en&encoding=linear16&sample_rate=16000"

# Then send binary audio data
```

```javascript JavaScript SDK

const client = new DeepgramClient();

const connection = await client.listen.v2.connect({
  model: "flux-general-multi",
  encoding: "linear16",
  sample_rate: 16000,
  Authorization: `Token ${process.env.DEEPGRAM_API_KEY}`,
  queryParams: { language_hint: ["en", "es"] },
});

connection.on("message", (message) => {
  if (message.type === "TurnInfo") {
    console.log(message.transcript);
    console.log(message.languages);
  }
});

connection.connect();
await connection.waitForOpen();
```

```java Java SDK

DeepgramClient deepgram = DeepgramClient.builder().build();

// SDK automatically uses /v2/listen endpoint
V2ConnectOptions options = V2ConnectOptions.builder()
    .model(ListenV2Model.FLUX_GENERAL_MULTI)
    .encoding(ListenV2Encoding.LINEAR16)
    .sampleRate(ListenV2SampleRate.of(16000))
    .build();

V2WebSocketClient wsClient = deepgram.listen().v2().v2WebSocket();
wsClient.connect(options).get(10, java.util.concurrent.TimeUnit.SECONDS);

// Set language hints for the session.
wsClient.sendConfigure(
    ListenV2Configure.builder()
        .languageHints(List.of("en", "es"))
        .build()
).get(5, java.util.concurrent.TimeUnit.SECONDS);

// Send audio data here
```
</CodeGroup>

**Common Mistakes to Avoid:**
- ❌ Using `/v1/listen` instead of `/v2/listen`
- ❌ Using `model=flux` instead of `model=flux-general-en` or `model=flux-general-multi`
- ❌ Using `language=en` parameter (use the model name to select language support; use `language_hint` with `flux-general-multi` for language biasing)
- ❌ Sending `language_hint` to `flux-general-en` (only `flux-general-multi` supports it)
- ❌ Specifying `encoding` or `sample_rate` when sending containerized audio (omit these for containerized formats)

## Let's Build!

This guide walks you through building a basic streaming transcription application powered by Deepgram Flux and the Deepgram SDK.

By the end of this guide, you’ll have:
- A real-time streaming transcription application with sub-second response times using the [BBC Real Time Live Stream](http://stream.live.vc.bbcmedia.co.uk/bbc_world_service) as your audio.
- Natural conversation flow with Flux’s advanced turn detection model
- Voice Activity Detection based interruption handling for responsive interactions
- A working demo you can build on!

**Audio Stream**

To handle the audio stream will be using the following conversion approach:

```mermaid
graph LR
    A[BBC World Service<br/>MP3/AAC] --> B[FFmpeg]
    B --> C[Linear16 PCM]
    C --> D[Deepgram Flux]
    D --> E[Transcripts]
```

### 1. Install the Deepgram SDK

<CodeGroup>
 ```Python
  # Install the Deepgram Python SDK
  # https://github.com/deepgram/deepgram-python-sdk
  pip install deepgram-sdk
  ```
  ```JavaScript
  npm install @deepgram/sdk
  ```
  ```csharp C#
  COMING SOON!
  // Install the Deepgram .NET SDK
  // https://github.com/deepgram/deepgram-dotnet-sdk

  // $ dotnet add package Deepgram
  ```

  ```Go
  COMING SOON!
  // Install the Deepgram Go SDK
  // https://github.com/deepgram/deepgram-go-sdk

  // $ go get github.com/deepgram/deepgram-go-sdk
  ```

  ```java Java
  <!-- Add to pom.xml -->
  <dependency>
    <groupId>com.deepgram</groupId>
    <artifactId>deepgram-java-sdk</artifactId>
    <version>0.3.0</version>
  </dependency>

  // Gradle: implementation 'com.deepgram:deepgram-java-sdk:0.3.0'
  // https://github.com/deepgram/deepgram-java-sdk
  ```
</CodeGroup>

### 2. Add Dependencies

Install the additional dependencies:

<CodeGroup>
```Python
# Install python-dotenv to protect your API key
pip install python-dotenv
```
```javascript JavaScript
npm install fluent-ffmpeg
```
``` csharp C#
COMING SOON!
```
``` Go
COMING SOON!
```
```java Java
// No additional dependencies required.
// FFmpeg must be installed on your machine (see step 3).
// Set DEEPGRAM_API_KEY as an environment variable.
```

</CodeGroup>

### 3. Install `FFMPEG` on your machine

You will need the actual FFmpeg binary installed to run this demo:

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: `Download from https://ffmpeg.org/`

### 4. Create a `.env` file

Create a `.env` file in your project root with your Deepgram API key:

```bash
touch .env
```
```bash
DEEPGRAM_API_KEY="your_deepgram_api_key"
```
<Info>
Replace `your_deepgram_api_key` with your actual Deepgram API key.
</Info>

### 4. Set Imports and Set Audio Stream Colors

**Core Dependencies**:
- `asyncio` - Handles concurrent audio streaming and Deepgram connection
- `subprocess` - Manages FFmpeg process for audio conversion
- `dotenv` - Loads Deepgram API key from `.env` file

**Deepgram SDK**:
- `AsyncDeepgramClient` - Main client for Flux API connection
- `EventType` - WebSocket event constants (OPEN, MESSAGE, CLOSE, ERROR)
- `ListenV2TurnInfo` - Type hints for incoming transcription messages

**Configuration**:
- `STREAM_URL` - BBC World Service streaming audio endpoint

**Visual Feedback System**:
- `Colors` class - ANSI terminal color codes for confidence visualization
- `get_confidence_color()` - Maps confidence scores to colors:
  - **Green** (0.90-1.00): High confidence
  - **Yellow** (0.80-0.90): Good confidence
  - **Orange** (0.70-0.80): Lower confidence
  - **Red** (≤0.69): Low confidence

**Purpose**: Sets up the foundation for real-time streaming transcription with visual quality indicators, making it easy to spot transcription accuracy at a glance.

<CodeGroup>
```python Python

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.listen.v2.types import ListenV2TurnInfo

# URL for the realtime streaming audio to transcribe
STREAM_URL = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service"

# Terminal color codes
class Colors:
    GREEN = '\033[92m'    # 0.90-1.00
    YELLOW = '\033[93m'   # 0.80-0.90
    ORANGE = '\033[91m'   # 0.70-0.80 (using red as orange isn't standard)
    RED = '\033[31m'      # <=0.69
    RESET = '\033[0m'     # Reset to default

def get_confidence_color(confidence: float) -> str:
    """Return the appropriate color code based on confidence score"""
    if confidence >= 0.90:
        return Colors.GREEN
    elif confidence >= 0.80:
        return Colors.YELLOW
    elif confidence >= 0.70:
        return Colors.ORANGE
    else:
        return Colors.RED

```

```javascript JavaScript

const client = new DeepgramClient();

const STREAM_URL = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service";

const colors = {
  green: "\u001b[92m",
  yellow: "\u001b[93m",
  orange: "\u001b[91m",
  red: "\u001b[31m",
  reset: "\u001b[0m",
};

function getConfidenceColor(confidence) {
  if (confidence >= 0.9) return colors.green;
  if (confidence >= 0.8) return colors.yellow;
  if (confidence >= 0.7) return colors.orange;
  return colors.red;
}
```
``` csharp C#
COMING SOON!
```
``` Go
COMING SOON!
```
```java Java

// Audio stream URL
static final String STREAM_URL = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service";

// ANSI color codes for confidence visualization
static final String GREEN  = "\033[92m"; // 0.90-1.00
static final String YELLOW = "\033[93m"; // 0.80-0.90
static final String ORANGE = "\033[91m"; // 0.70-0.80
static final String RED    = "\033[31m"; // <=0.69
static final String RESET  = "\033[0m";

static String getConfidenceColor(double confidence) {
    if (confidence >= 0.90) return GREEN;
    if (confidence >= 0.80) return YELLOW;
    if (confidence >= 0.70) return ORANGE;
    return RED;
}
```
</CodeGroup>

### 5. Connect to Flux and Process Audio

The main function orchestrates real-time transcription of streaming audio URLs:
- **Initialize:** Creates `AsyncDeepgramClient` and connects to Flux with required linear16 format
- **Event Handling:** Sets up message handler that displays transcriptions with color-coded confidence scores
- **Audio Pipeline:** Launches FFmpeg subprocess to convert compressed stream URL to `linear16` PCM format
- **Streaming Loop:** Reads converted audio chunks and pipes them to Deepgram Flux connection
- **Concurrent Tasks:** Runs Deepgram listener and audio conversion simultaneously using asyncio
- **Error Handling:** Manages FFmpeg errors and connection timeouts (60s default)

The function handles both the audio conversion requirement (Flux only accepts `linear16`) and real-time streaming coordination between multiple async processes.

<CodeGroup>
```python Python
async def main():
    """Main async function to handle URL streaming to Deepgram Flux"""

    # Create the Deepgram async client
    client = AsyncDeepgramClient() # The API key retrieval happens automatically in the constructor

    try:
        # Connect to Flux with auto-detection for streaming audio
        # SDK automatically connects to: wss://api.deepgram.com/v2/listen?model=flux-general-en&encoding=linear16&sample_rate=16000
        async with client.listen.v2.connect(
            model="flux-general-en",
            encoding="linear16",
            sample_rate="16000"
        ) as connection:

            # Define message handler function
            def on_message(message) -> None:
                msg_type = getattr(message, "type", "Unknown")

                # Show transcription results
                if hasattr(message, 'transcript') and message.transcript:
                    print(f"🎤 {message.transcript}")

                    # Show word-level confidence with color coding
                    if hasattr(message, 'words') and message.words:
                        colored_words = []
                        for word in message.words:
                            color = get_confidence_color(word.confidence)
                            colored_words.append(f"{color}{word.word}({word.confidence:.2f}){Colors.RESET}")
                        words_info = " | ".join(colored_words)
                        print(f"   📝 {words_info}")
                elif msg_type == "Connected":
                    print(f"✅ Connected to Deepgram Flux - Ready for audio!")

            # Set up event handlers
            connection.on(EventType.OPEN, lambda _: print("Connection opened"))
            connection.on(EventType.MESSAGE, on_message)
            connection.on(EventType.CLOSE, lambda _: print("Connection closed"))
            connection.on(EventType.ERROR, lambda error: print(f"Caught: {error}"))

            # Start the connection listening in background (it's already async)
            deepgram_task = asyncio.create_task(connection.start_listening())

            # Convert BBC stream to linear16 PCM using ffmpeg
            print(f"Starting to stream and convert audio from: {STREAM_URL}")

            # Use ffmpeg to convert the compressed BBC stream to linear16 PCM at 16kHz
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', STREAM_URL,           # Input: BBC World Service stream
                '-f', 's16le',              # Output format: 16-bit little-endian PCM (linear16)
                '-ar', '16000',             # Sample rate: 16kHz
                '-ac', '1',                 # Channels: mono
                '-'                         # Output to stdout
            ]

            try:
                # Start ffmpeg process
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                print(f"✅ Audio conversion started (BBC → linear16 PCM)")

                # Read converted PCM data and send to Deepgram
                # Note: 1024 bytes = ~32ms of audio at 16kHz linear16
                # For optimal performance, consider using ~2560 bytes (~80ms at 16kHz)
                while True:
                    chunk = await process.stdout.read(1024)
                    if not chunk:
                        break

                    # Send converted linear16 PCM data to Flux
                    await connection._send(chunk)

                await process.wait()

            except Exception as e:
                print(f"Error during audio conversion: {e}")
                if 'process' in locals():
                    stderr = await process.stderr.read()
                    print(f"FFmpeg error: {stderr.decode()}")

            # Wait for Deepgram task to complete (or cancel after timeout)
            try:
                await asyncio.wait_for(deepgram_task, timeout=60)
            except asyncio.TimeoutError:
                print("Stream timeout after 60 seconds")
                deepgram_task.cancel()

    except Exception as e:
        print(f"Caught: {e}")

if __name__ == "__main__":
    asyncio.run(main())

```

```javascript JavaScript

async function main() {
  const client = new DeepgramClient();

  const connection = await client.listen.v2.connect({
    model: "flux-general-multi",
    encoding: "linear16",
    sample_rate: 16000,
    Authorization: `Token ${process.env.DEEPGRAM_API_KEY}`,
    queryParams: { language_hint: ["en", "es"] },
  });

  connection.on("message", (message) => {
    if (message.type !== "TurnInfo" || !message.transcript) {
      return;
    }

    console.log(`Transcript: ${message.transcript}`);

    if (message.words?.length) {
      const words = message.words.map((word) => {
        const color = getConfidenceColor(word.confidence);
        return `${color}${word.word}(${word.confidence.toFixed(2)})${colors.reset}`;
      });

      console.log(words.join(" | "));
    }
  });

  connection.connect();
  await connection.waitForOpen();

  ffmpeg(STREAM_URL)
    .format("s16le")
    .audioFrequency(16000)
    .audioChannels(1)
    .on("error", console.error)
    .pipe()
    .on("data", (chunk) => connection.sendMedia(chunk));
}

main().catch(console.error);
```
``` csharp C#
COMING SOON!
```
``` Go
COMING SOON!
```
```java Java
public static void main(String[] args) throws Exception {
    DeepgramClient deepgram = DeepgramClient.builder().build();

    V2ConnectOptions options = V2ConnectOptions.builder()
        .model("flux-general-en")
        .encoding("linear16")
        .sampleRate(16000)
        .build();

    V2WebSocketClient wsClient = deepgram.listen().v2().v2WebSocket();
    wsClient.connect(options).get(10, java.util.concurrent.TimeUnit.SECONDS);

    wsClient.onConnected(() -> System.out.println("Connected to Deepgram Flux - Ready for audio!"));
    wsClient.onTurnInfo(message -> {
        if (message.getTranscript() != null && !message.getTranscript().isEmpty()) {
            System.out.println("Transcript: " + message.getTranscript());

            // Show word-level confidence with color coding
            if (message.getWords() != null) {
                StringBuilder sb = new StringBuilder();
                for (var word : message.getWords()) {
                    String color = getConfidenceColor(word.getConfidence());
                    sb.append(color).append(word.getWord())
                      .append("(").append(String.format("%.2f", word.getConfidence())).append(")")
                      .append(RESET).append(" | ");
                }
                System.out.println("  " + sb);
            }
        }
    });
    wsClient.onDisconnected(() -> System.out.println("Connection closed"));
    wsClient.onError(err -> System.err.println("Error: " + err));

    // Use FFmpeg to convert BBC stream to linear16 PCM
    System.out.println("Starting audio stream from: " + STREAM_URL);
    ProcessBuilder pb = new ProcessBuilder(
        "ffmpeg", "-i", STREAM_URL,
        "-f", "s16le", "-ar", "16000", "-ac", "1", "-"
    );
    Process ffmpeg = pb.start();

    // Read FFmpeg output and send to Deepgram (~80ms chunks at 16kHz)
    byte[] buffer = new byte[2560];
    int bytesRead;
    try (InputStream pcm = ffmpeg.getInputStream()) {
        while ((bytesRead = pcm.read(buffer)) != -1) {
            wsClient.sendMedia(okio.ByteString.of(buffer, 0, bytesRead));
        }
    }

    ffmpeg.waitFor();
}
```
</CodeGroup>

### 6. Complete Code Example

Here's the complete working example that combines all the steps. You can also find this code on [GitHub](https://github.com/deepgram-devs/deepgram-demos-flux-streaming-transcription).

<CodeGroup>
```java Java

public class FluxStreaming {
    static final String STREAM_URL = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service";
    static final String GREEN  = "\033[92m";
    static final String YELLOW = "\033[93m";
    static final String ORANGE = "\033[91m";
    static final String RED    = "\033[31m";
    static final String RESET  = "\033[0m";

    static String getConfidenceColor(double confidence) {
        if (confidence >= 0.90) return GREEN;
        if (confidence >= 0.80) return YELLOW;
        if (confidence >= 0.70) return ORANGE;
        return RED;
    }

    public static void main(String[] args) throws Exception {
        DeepgramClient deepgram = DeepgramClient.builder().build();

        V2ConnectOptions options = V2ConnectOptions.builder()
            .model("flux-general-en")
            .encoding("linear16")
            .sampleRate(16000)
            .build();

        V2WebSocketClient wsClient = deepgram.listen().v2().v2WebSocket();
        wsClient.connect(options).get(10, java.util.concurrent.TimeUnit.SECONDS);

        wsClient.onConnected(() -> System.out.println("Connected to Deepgram Flux - Ready for audio!"));
        wsClient.onTurnInfo(message -> {
            if (message.getTranscript() != null && !message.getTranscript().isEmpty()) {
                System.out.println("Transcript: " + message.getTranscript());

                if (message.getWords() != null) {
                    StringBuilder sb = new StringBuilder();
                    for (var word : message.getWords()) {
                        String color = getConfidenceColor(word.getConfidence());
                        sb.append(color).append(word.getWord())
                          .append("(").append(String.format("%.2f", word.getConfidence())).append(")")
                          .append(RESET).append(" | ");
                    }
                    System.out.println("  " + sb);
                }
            }
        });
        wsClient.onDisconnected(() -> System.out.println("Connection closed"));
        wsClient.onError(err -> System.err.println("Error: " + err));

        System.out.println("Starting audio stream from: " + STREAM_URL);
        ProcessBuilder pb = new ProcessBuilder(
            "ffmpeg", "-i", STREAM_URL,
            "-f", "s16le", "-ar", "16000", "-ac", "1", "-"
        );
        Process ffmpeg = pb.start();

        // Read FFmpeg output and send to Deepgram (~80ms chunks at 16kHz)
        byte[] buffer = new byte[2560];
        int bytesRead;
        try (InputStream pcm = ffmpeg.getInputStream()) {
            while ((bytesRead = pcm.read(buffer)) != -1) {
                wsClient.sendMedia(okio.ByteString.of(buffer, 0, bytesRead));
            }
        }

        ffmpeg.waitFor();
    }
}
```

```Python

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.listen.v2.types import ListenV2TurnInfo

# URL for the realtime streaming audio to transcribe
STREAM_URL = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service"

# Terminal color codes
class Colors:
    GREEN = '\033[92m'    # 0.90-1.00
    YELLOW = '\033[93m'   # 0.80-0.90
    ORANGE = '\033[91m'   # 0.70-0.80 (using red as orange isn't standard)
    RED = '\033[31m'      # <=0.69
    RESET = '\033[0m'     # Reset to default

def get_confidence_color(confidence: float) -> str:
    """Return the appropriate color code based on confidence score"""
    if confidence >= 0.90:
        return Colors.GREEN
    elif confidence >= 0.80:
        return Colors.YELLOW
    elif confidence >= 0.70:
        return Colors.ORANGE
    else:
        return Colors.RED

async def main():
    """Main async function to handle URL streaming to Deepgram Flux"""

    # Create the Deepgram async client
    client = AsyncDeepgramClient()

    try:
        # Connect to Flux with auto-detection for streaming audio
        # SDK automatically connects to: wss://api.deepgram.com/v2/listen?model=flux-general-en&encoding=linear16&sample_rate=16000
        async with client.listen.v2.connect(
            model="flux-general-en",
            encoding="linear16",
            sample_rate="16000"
        ) as connection:

            # Define message handler function
            def on_message(message) -> None:
                msg_type = getattr(message, "type", "Unknown")

                # Show transcription results
                if hasattr(message, 'transcript') and message.transcript:
                    print(f"🎤 {message.transcript}")

                    # Show word-level confidence with color coding
                    if hasattr(message, 'words') and message.words:
                        colored_words = []
                        for word in message.words:
                            color = get_confidence_color(word.confidence)
                            colored_words.append(f"{color}{word.word}({word.confidence:.2f}){Colors.RESET}")
                        words_info = " | ".join(colored_words)
                        print(f"   📝 {words_info}")
                elif msg_type == "Connected":
                    print(f"✅ Connected to Deepgram Flux - Ready for audio!")

            # Set up event handlers
            connection.on(EventType.OPEN, lambda _: print("Connection opened"))
            connection.on(EventType.MESSAGE, on_message)
            connection.on(EventType.CLOSE, lambda _: print("Connection closed"))
            connection.on(EventType.ERROR, lambda error: print(f"Caught: {error}"))

            # Start the connection listening in background (it's already async)
            deepgram_task = asyncio.create_task(connection.start_listening())

            # Convert BBC stream to linear16 PCM using ffmpeg
            print(f"Starting to stream and convert audio from: {STREAM_URL}")

            # Use ffmpeg to convert the compressed BBC stream to linear16 PCM at 16kHz
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', STREAM_URL,           # Input: BBC World Service stream
                '-f', 's16le',              # Output format: 16-bit little-endian PCM (linear16)
                '-ar', '16000',             # Sample rate: 16kHz
                '-ac', '1',                 # Channels: mono
                '-'                         # Output to stdout
            ]

            try:
                # Start ffmpeg process
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                print(f"✅ Audio conversion started (BBC → linear16 PCM)")

                # Read converted PCM data and send to Deepgram
                # Note: 1024 bytes = ~32ms of audio at 16kHz linear16
                # For optimal performance, consider using ~2560 bytes (~80ms at 16kHz)
                while True:
                    chunk = await process.stdout.read(1024)
                    if not chunk:
                        break

                    # Send converted linear16 PCM data to Flux
                    await connection._send(chunk)

                await process.wait()

            except Exception as e:
                print(f"Error during audio conversion: {e}")
                if 'process' in locals():
                    stderr = await process.stderr.read()
                    print(f"FFmpeg error: {stderr.decode()}")

            # Wait for Deepgram task to complete (or cancel after timeout)
            try:
                await asyncio.wait_for(deepgram_task, timeout=60)
            except asyncio.TimeoutError:
                print("Stream timeout after 60 seconds")
                deepgram_task.cancel()

    except Exception as e:
        print(f"Caught: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```
</CodeGroup>

## Additional Flux Demos

For additional demos showcasing Flux, check out the following repositories:

| Demo Link                    | Repository                   | Tech Stack                   | Use Case                     |
|------------------------------|------------------------------|------------------------------|------------------------------|
| [Demo Link](https://demos.dx.deepgram.com/flux-streaming) | [Repository](https://github.com/deepgram-devs/deepgram-demos-flux-streaming) | Node, JS, HTML, CSS             | Flux Streaming Transcription |
| N/A                             | [Repository](https://github.com/deepgram-devs/deepgram-demos-rust)                             | Rust                   | Flux Streaming Transcription                   |

## Building a Voice Agent with Flux

Are you ready to build a voice agent with Flux? See our [Build a Flux-enabled Voice Agent](/docs/flux/agent) Guide to get started.