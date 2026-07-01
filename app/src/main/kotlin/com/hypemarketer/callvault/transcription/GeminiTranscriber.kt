package com.hypemarketer.callvault.transcription

import com.google.ai.client.generativeai.GenerativeModel
import com.google.ai.client.generativeai.type.content
import com.google.ai.client.generativeai.type.generationConfig
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Wraps Gemini 2.5 Flash for audio-in transcription.
 *
 * Uses inline blob transport (audio embedded in the request body). Fine up to ~20 MB —
 * at 64 kbps mono AAC, that's ~40 minutes of audio. For longer calls, switch to the
 * Files API upload flow.
 */
class GeminiTranscriber(private val apiKey: String) {

    private val model by lazy {
        GenerativeModel(
            modelName = "gemini-2.5-flash",
            apiKey = apiKey,
            generationConfig = generationConfig {
                temperature = 0.2f
                responseMimeType = "text/plain"
            },
        )
    }

    suspend fun transcribe(audio: File): String = withContext(Dispatchers.IO) {
        require(apiKey.isNotBlank()) { "GEMINI_API_KEY is empty. Set it in app/secrets.properties." }
        require(audio.exists()) { "Audio file missing: ${audio.absolutePath}" }

        val bytes = audio.readBytes()
        val mime = mimeFor(audio)

        val prompt = content("user") {
            text(PROMPT)
            blob(mime, bytes)
        }

        val response = model.generateContent(prompt)
        response.text?.trim().orEmpty()
    }

    private fun mimeFor(file: File): String = when (file.extension.lowercase()) {
        "m4a", "mp4" -> "audio/mp4"
        "aac" -> "audio/aac"
        "wav" -> "audio/wav"
        "ogg" -> "audio/ogg"
        "mp3" -> "audio/mpeg"
        else -> "audio/mp4"
    }

    companion object {
        private const val PROMPT = """
            You are transcribing a business phone call. The audio may be in Hindi, English,
            Arabic, or a code-switched mix. Produce a clean, readable transcript.
            Format: "Speaker A:" and "Speaker B:" on separate lines when you can distinguish
            speakers; otherwise write it as plain prose. Include timestamps every 30 seconds
            in the form (mm:ss). Do not summarise — transcribe verbatim.
        """
    }
}
