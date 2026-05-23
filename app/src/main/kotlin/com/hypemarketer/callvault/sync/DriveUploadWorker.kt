package com.hypemarketer.callvault.sync

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.hypemarketer.callvault.CallVaultApp
import com.hypemarketer.callvault.data.db.UploadStatus
import com.hypemarketer.callvault.transcription.TranscriptionQueue

/**
 * Phase 2 stub.
 *
 * TODO(Atharva):
 *   1. Acquire a Drive credential via GoogleAccountCredential + GoogleSignIn (scope: drive.file).
 *   2. Build a com.google.api.services.drive.Drive client using NetHttpTransport + GsonFactory.
 *   3. Look up / create the CallVault/YYYY-MM folder per PRD §4.2.
 *   4. Upload the local file as a resumable media upload; capture the returned fileId.
 *   5. Mark UploadStatus.UPLOADED with driveFileId, then enqueue transcription.
 *   6. On failure, return Result.retry() — WorkManager handles exponential backoff.
 */
class DriveUploadWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val recordingId = inputData.getLong(DriveSync.KEY_RECORDING_ID, -1L)
        if (recordingId < 0) return Result.failure()

        val app = applicationContext as CallVaultApp
        val rec = app.recordings.get(recordingId) ?: return Result.failure()

        return try {
            app.recordings.markUploadStatus(recordingId, UploadStatus.UPLOADING)

            // TODO: real upload. For now: pretend it succeeded so the rest of the pipeline
            // (transcription scheduling, library UI) can be wired end-to-end.
            val fakeFileId = "stub-${System.currentTimeMillis()}"
            Log.w(TAG, "DriveUploadWorker is a Phase 2 stub. Pretending upload for $recordingId.")

            app.recordings.markUploadStatus(recordingId, UploadStatus.UPLOADED, driveFileId = fakeFileId)
            TranscriptionQueue.enqueue(applicationContext, recordingId)
            Result.success()
        } catch (t: Throwable) {
            Log.e(TAG, "upload failed for $recordingId", t)
            app.recordings.markUploadStatus(recordingId, UploadStatus.FAILED)
            if (runAttemptCount < MAX_ATTEMPTS) Result.retry() else Result.failure()
        }
    }

    companion object {
        private const val TAG = "DriveUploadWorker"
        private const val MAX_ATTEMPTS = 5
    }
}
