package com.jarvis.assistant

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.os.Bundle
import android.os.Environment
import android.widget.Button
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    private val client = OkHttpClient()
    private val backendBaseUrl = "http://10.0.2.2:8000/v1"

    private lateinit var statusText: TextView
    private lateinit var logText: TextView
    private lateinit var listenButton: Button

    private var mediaPlayer: MediaPlayer? = null

    private val audioPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        statusText.text = if (granted) "Permission granted" else "Microphone permission required"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        logText = findViewById(R.id.logText)
        listenButton = findViewById(R.id.listenButton)

        listenButton.setOnClickListener {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
                audioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            } else {
                startListening()
            }
        }
    }

    private fun startListening() {
        statusText.text = "Listening..."
        listenButton.isEnabled = false
        CoroutineScope(Dispatchers.IO).launch {
            val wavFile = recordWav(4_000)
            val transcription = uploadAudio(wavFile)
            log("STT: $transcription")

            if (!transcription.contains("hey jarvis", ignoreCase = true)) {
                status("Wake word not detected")
                listenButtonEnabled(true)
                return@launch
            }

            val nluResult = postJson("$backendBaseUrl/nlu", jsonPayload("text", transcription))
            log("NLU: $nluResult")

            val agentResult = postJson(
                "$backendBaseUrl/agent",
                JSONObject()
                    .put("text", transcription)
                    .put("provider", "opencode")
                    .toString()
            )
            log("Agent: $agentResult")

            val responseText = extractAssistantText(agentResult)
            if (responseText.isNotBlank()) {
                playTts(responseText)
            }

            status("Ready")
            listenButtonEnabled(true)
        }
    }

    private fun recordWav(durationMs: Int): File {
        val sampleRate = 16000
        val channelConfig = AudioFormat.CHANNEL_IN_MONO
        val audioFormat = AudioFormat.ENCODING_PCM_16BIT
        val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat)
        val audioRecord = AudioRecord(MediaRecorder.AudioSource.MIC, sampleRate, channelConfig, audioFormat, bufferSize)

        val outputDir = getExternalFilesDir(Environment.DIRECTORY_MUSIC) ?: cacheDir
        val wavFile = File(outputDir, "jarvis_input.wav")

        val pcmData = ByteArray(bufferSize)
        val pcmStream = ByteArrayOutputStream()

        audioRecord.startRecording()
        val startTime = System.currentTimeMillis()
        while (System.currentTimeMillis() - startTime < durationMs) {
            val read = audioRecord.read(pcmData, 0, pcmData.size)
            if (read > 0) {
                pcmStream.write(pcmData, 0, read)
            }
        }
        audioRecord.stop()
        audioRecord.release()

        val pcmBytes = pcmStream.toByteArray()
        writeWavFile(wavFile, pcmBytes, sampleRate, 1)
        return wavFile
    }

    private fun writeWavFile(file: File, pcmData: ByteArray, sampleRate: Int, channels: Int) {
        val byteRate = sampleRate * channels * 2
        val header = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
        header.put("RIFF".toByteArray())
        header.putInt(36 + pcmData.size)
        header.put("WAVE".toByteArray())
        header.put("fmt ".toByteArray())
        header.putInt(16)
        header.putShort(1)
        header.putShort(channels.toShort())
        header.putInt(sampleRate)
        header.putInt(byteRate)
        header.putShort((channels * 2).toShort())
        header.putShort(16)
        header.put("data".toByteArray())
        header.putInt(pcmData.size)

        FileOutputStream(file).use { output ->
            output.write(header.array())
            output.write(pcmData)
        }
    }

    private fun uploadAudio(file: File): String {
        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("audio", file.name, file.asRequestBody("audio/wav".toMediaType()))
            .build()

        val request = Request.Builder()
            .url("$backendBaseUrl/stt")
            .post(requestBody)
            .build()

        client.newCall(request).execute().use { response ->
            return response.body?.string().orEmpty()
        }
    }

    private fun postJson(url: String, payload: String): String {
        val body = payload.toRequestBody("application/json".toMediaType())
        val request = Request.Builder().url(url).post(body).build()
        client.newCall(request).execute().use { response ->
            return response.body?.string().orEmpty()
        }
    }

    private fun jsonPayload(key: String, value: String): String {
        return JSONObject().put(key, value).toString()
    }

    private fun extractAssistantText(response: String): String {
        val marker = "\"content\":\""
        val start = response.indexOf(marker)
        if (start < 0) return ""
        val end = response.indexOf("\"", start + marker.length)
        if (end < 0) return ""
        return response.substring(start + marker.length, end)
    }

    private fun playTts(text: String) {
        val payload = JSONObject()
            .put("text", text)
            .put("emotion", "neutral")
            .toString()
        val body = payload.toRequestBody("application/json".toMediaType())
        val request = Request.Builder().url("$backendBaseUrl/tts").post(body).build()

        client.newCall(request).execute().use { response ->
            val audioBytes = response.body?.bytes() ?: return
            val file = File(cacheDir, "jarvis_tts.wav")
            file.writeBytes(audioBytes)
            runOnUiThread {
                mediaPlayer?.release()
                mediaPlayer = MediaPlayer().apply {
                    setDataSource(file.absolutePath)
                    prepare()
                    start()
                }
            }
        }
    }

    private fun status(text: String) = runOnUiThread { statusText.text = text }

    private fun log(text: String) = runOnUiThread { logText.text = text }

    private fun listenButtonEnabled(enabled: Boolean) = runOnUiThread { listenButton.isEnabled = enabled }
}
