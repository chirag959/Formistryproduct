package com.hypemarketer.callvault.transcription

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.hypemarketer.callvault.BuildConfig
import com.hypemarketer.callvault.CallVaultApp
import com.hypemarketer.callvault.data.db.TranscriptStatus
import java.io.File

class TranscriptionWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val id = inputData.getLong(TranscriptionQueue.KEY_RECORDING_ID, -1L)
        if (id < 0) return Result.failure()

        val app = applicationContext as CallVaultApp
        val rec = app.recordings.get(id) ?: return Result.failure()
        val localPath = rec.localPath
        if (localPath.isNullOrBlank()) {
            Log.w(TAG, "no local file for $id (already cleaned up?) — skipping transcription")
            return Result.failure()
        }
        val audio = File(localPath)
        if (!audio.exists()) {
            Log.w(TAG, "audio missing at $localPath")
            return Result.failure()
        }

        val apiKey = BuildConfig.GEMINI_API_KEY
        if (apiKey.isBlank()) {
            Log.w(TAG, "GEMINI_API_KEY is blank; add it to app/secrets.properties and rebuild.")
            app.recordings.markTranscriptStatus(id, TranscriptStatus.FAILED)
            return Result.failure()
        }

        return try {
            app.recordings.markTranscriptStatus(id, TranscriptStatus.PROCESSING)
            val transcript = GeminiTranscriber(apiKey).transcribe(audio)
            app.recordings.saveTranscript(id, transcript.ifBlank { "[empty response]" })
            Result.success()
        } catch (t: Throwable) {
            Log.e(TAG, "transcription failed for $id", t)
            app.recordings.markTranscriptStatus(id, TranscriptStatus.FAILED)
            if (runAttemptCount < MAX_ATTEMPTS) Result.retry() else Result.failure()
        }
    }

    companion object {
        private const val TAG = "TranscriptionWorker"
        private const val MAX_ATTEMPTS = 3
    }
}
