package com.hypemarketer.callvault.sync

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import java.util.concurrent.TimeUnit

/**
 * Phase 2 entry point: enqueue a recording for Google Drive upload.
 *
 * Implementation lives in [DriveUploadWorker]; WorkManager handles retries with
 * exponential backoff per PRD §7 Flow 2.
 */
object DriveSync {

    const val KEY_RECORDING_ID = "recordingId"

    fun enqueueUpload(context: Context, recordingId: Long) {
        val request = OneTimeWorkRequestBuilder<DriveUploadWorker>()
            .setInputData(workDataOf(KEY_RECORDING_ID to recordingId))
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build(),
            )
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
            .addTag(TAG_UPLOAD)
            .build()
        WorkManager.getInstance(context).enqueue(request)
    }

    const val TAG_UPLOAD = "callvault.drive.upload"
}
