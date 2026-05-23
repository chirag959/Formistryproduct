package com.hypemarketer.callvault.transcription

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.hypemarketer.callvault.CallVaultApp
import com.hypemarketer.callvault.data.db.TranscriptStatus

/**
 * Phase 4 stub.
 *
 * TODO(Atharva):
 *   1. Load the local file (or download from Drive if local was cleaned up).
 *   2. Build a com.google.ai.client.generativeai.GenerativeModel with model
 *      "gemini-2.5-flash" and the user's API key (from EncryptedSharedPreferences
 *      or a per-team key shipped via secrets.properties / BuildConfig).
 *   3. Send the audio as an inline-data Part (audio/mp4 for .m4a).
 *   4. Ask Gemini for a structured JSON: { transcript, summary, speakers, action_items, sentiment }
 *      per PRD §4.3.
 *   5. Save the transcript via RecordingRepository.saveTranscript().
 *
 * Audio I/O note: Gemini accepts inline audio up to ~20MB. For long calls, either trim or
 * use the Files API (uploadFile / generateContent referencing the file URI).
 */
class TranscriptionWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val id = inputData.getLong(TranscriptionQueue.KEY_RECORDING_ID, -1L)
        if (id < 0) return Result.failure()

        val app = applicationContext as CallVaultApp
        val rec = app.recordings.get(id) ?: return Result.failure()

        return try {
            app.recordings.markTranscriptStatus(id, TranscriptStatus.PROCESSING)

            // TODO: real Gemini call. Stub: write a placeholder so search/UI work end-to-end.
            Log.w(TAG, "TranscriptionWorker is a Phase 4 stub. Writing placeholder for $id.")
            val placeholder = "[Transcription pending — wire up GeminiTranscriber in Phase 4]"
            app.recordings.saveTranscript(id, placeholder)
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
